from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
from fastapi.encoders import jsonable_encoder
from bson import ObjectId
from db import project_collection, conversations_collection, steps_collection
from datetime import datetime
import os
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

router = APIRouter()

class Project(BaseModel):
    projectTitle: str
    userId: str


@router.post("/projects")
def create_project(project: Project):
    project_dict = {
        "projectTitle": project.projectTitle,
        "userId": project.userId,
        "createdAt": datetime.utcnow(),
    }

    result = project_collection.insert_one(project_dict)
    project_id = result.inserted_id

    return {"id": str(project_id)}


@router.get("/projects")
def list_projects(user_id: str):
    """
    GET /projects?user_id=<mongo‐object‐id>
    returns all projects for that user.
    """
    try:
        docs = project_collection.find({ "userId": user_id })

        
        print (docs)

        results = list(docs)

        if not results:
            return {"message":"No Projects found", "projects":[]}

        payload = {"message": "Projects found", "projects": results}

        # Convert all ObjectIds (including nested ones) to strings
        return jsonable_encoder(payload, custom_encoder={ObjectId: str})

    except:
        print(f"❌ There was an error fetching projects for {user_id}")
        raise HTTPException(status_code=400, detail="Projects Error")
        


@router.get("/project/{project_id}")
def get_project(project_id: str):
    project = project_collection.find_one({"_id": ObjectId(project_id)})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project["_id"] = str(project["_id"])
    project["userId"] = str(project["userId"])
    return project


@router.put("/projects/{project_id}")
def update_project(project_id: str, update_data: dict):
    result = project_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project updated", "modified": bool(result.modified_count)}


@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    project_obj_id = ObjectId(project_id)

    result = project_collection.delete_one({"_id": project_obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")

    conversations_collection.delete_many({"projectId": project_obj_id})
    conversations_collection.delete_many({"project": str(project_obj_id)})

    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    collection_name = os.getenv("QDRANT_COLLECTION", "projects")

    if not qdrant_url or not qdrant_api_key:
        return {
            "message": "Project and associated conversations deleted from MongoDB. Qdrant not configured; no embeddings removed.",
            "project_id": project_id
        }

    try:
        qclient = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, prefer_grpc=False)

        from qdrant_client.http.models import Filter, FieldCondition, MatchValue

        combined_filter = Filter(
            should=[
                FieldCondition(key="project", match=MatchValue(value=str(project_obj_id))),
                FieldCondition(key="mongo_id", match=MatchValue(value=str(project_obj_id))),
            ]
        )

        # Optional: log the count to confirm what will be deleted
        try:
            count_before = qclient.count(collection_name=collection_name, filter=combined_filter).count
            print(f"Qdrant: {count_before} points match the delete filter for project {project_id}")
        except Exception:
            print("Qdrant: could not fetch count before delete (continuing to delete)")

        qclient.delete(collection_name=collection_name, filter=combined_filter, wait=True)

        # Optional: confirm deletion
        try:
            count_after = qclient.count(collection_name=collection_name, filter=combined_filter).count
            print(f"Qdrant: {count_after} points remain after deletion for project {project_id}")
        except Exception:
            pass

    except Exception as e:
        print(f"Warning: failed to delete Qdrant points for project {project_id}: {e}")
        return {
            "message": "Project and conversations deleted from MongoDB. Failed to delete Qdrant embeddings (see server logs).",
            "project_id": project_id,
            "qdrant_error": str(e)
        }

    return {
        "message": "Project, associated conversations, and Qdrant embeddings deleted successfully",
        "project_id": project_id
    }

# @router.put("/complete-step/{project_id}/{step_number}")
# def complete_step(project_id: str, step_number: int):
#     result = steps_collection.update_one(
#         {"projectId": ObjectId(project_id), "stepNumber": step_number},
#         {"$set": {"completed": True}}
#     )
#     if result.matched_count == 0:
#         raise HTTPException(status_code=404, detail="Step not found")
#     return {"message": "Step updated", "modified": bool(result.modified_count)}

@router.put("/complete-step/{project_id}/{step}")
def complete_step(project_id: str, step: int):
    result = project_collection.update_one(
        {"_id": ObjectId(project_id), "step_generation.steps.order": step},
        {"$set": {"step_generation.steps.$.completed": True}}
    )
    if result.matched_count == 0:
        print("Project not found")

    cursor= project_collection.find({
        "_id": ObjectId(project_id)
    })
    if "step_generation" in cursor and "steps" in cursor["step_generation"]:
        steps= list(cursor["step_generation"]["steps"])

        completed=True
        for s in steps:
            if not ("completed" in s and s["completed"]==True):
                completed=False
                break
        
        if completed==True:
            project_collection.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": {"completed": True}}
            )

    return {"message": "Step updated", "modified": bool(result.modified_count)}

@router.put("/project/{project_id}/complete")
def complete_all_steps(project_id):
    cursor= project_collection.find_one({
        "_id": ObjectId(project_id)
    })
    if "step_generation" in cursor and "steps" in cursor["step_generation"]:
        print("there is steps")
        print(cursor)
        project_collection.update_one(   
            {"_id": ObjectId(project_id)},
            {"$set": { "step_generation.steps.$[].completed": True, "completed": True } }
        )
    
        return {"message": "Project/Steps updated"}

    return {"message": "No steps found"}

@router.get("/project/{project_id}/progress")
def steps_progress(project_id):
    cursor= project_collection.find_one({
        "_id": ObjectId(project_id)
    })

    if "step_generation" in cursor and "steps" in cursor["step_generation"]:
        steps= list(cursor["step_generation"]["steps"])

        print("there is steps")
        print(steps)

        count=0
        for s in steps:
            if "completed" in s and s["completed"]==True:
                count+=1

        return count/len(steps)
    
    return 0
