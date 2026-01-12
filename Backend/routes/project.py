from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from pymongo.collection import Collection
from pymongo.database import Database

from database.mongodb import mongodb

# from qdrant_client import QdrantClient
# from qdrant_client.http.models import Filter, FieldCondition, MatchValue
# from qdrant_client.http import models

router = APIRouter()
database: Database = mongodb.get_database()
project_collection: Collection = database.get_collection("Project")
conversations_collection: Collection = database.get_collection("Conversations")
steps_collection: Collection = database.get_collection("ProjectSteps")


class Project(BaseModel):
    projectTitle: str
    userId: str


# def fetch_all_points_client(url, api_key, collection_name, limit=500):
#     client = QdrantClient(url=url, api_key=api_key)
#     all_points = []
#     offset = None

#     while True:
#         response = client.scroll(
#             collection_name=collection_name,
#             limit=limit,
#             offset=offset,
#             with_payload=True,
#             with_vectors=False, 
#         )

#         if isinstance(response, tuple) and len(response) == 2:
#             pts, next_offset = response
#         else:
#             pts = response
#             next_offset = None

#         all_points.extend(pts)
#         if not next_offset:
#             break
#         offset = next_offset

#     return all_points

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
        docs = project_collection.find({"userId": user_id})

        print(docs)

        results = list(docs)

        if not results:
            return {"message": "No Projects found", "projects": []}

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

    # client_points = fetch_all_points_client(
    #     os.getenv("QDRANT_URL"), 
    #     os.getenv("QDRANT_API_KEY"), 
    #     "projects"
    # )

    # # Find points with the matching project ID
    # points_to_delete = []
    # for point in client_points:
    #     if point.payload and 'project' in point.payload and point.payload['project'] == project_id:
    #         points_to_delete.append(point.id)

    # # Delete the points if found
    # if points_to_delete:
    #     client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
    #     response = client.delete(
    #         collection_name="projects",
    #         points_selector=models.PointIdsList(points=points_to_delete),
    #         wait=True
    #     )
    return {
        "message": "Project, associated conversations, and Qdrant embeddings deleted successfully",
        "project_id": project_id
    }
    # else:
    #     print(f"Warning: failed to delete Qdrant points for project {project_id}")
    #     return {
    #         "message": "Project and conversations deleted from MongoDB. Failed to delete Qdrant embeddings (see server logs).",
    #         "project_id": project_id
    #     }


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

    cursor = project_collection.find({
        "_id": ObjectId(project_id)
    })
    if "step_generation" in cursor and "steps" in cursor["step_generation"]:
        steps = list(cursor["step_generation"]["steps"])

        completed = True
        for s in steps:
            if not ("completed" in s and s["completed"] == True):
                completed = False
                break

        if completed == True:
            project_collection.update_one(
                {"_id": ObjectId(project_id)},
                {"$set": {"completed": True}}
            )

    return {"message": "Step updated", "modified": bool(result.modified_count)}


@router.put("/reset-step/{project_id}/{step}")
def reset_step(project_id: str, step: int):
    result = project_collection.update_one(
        {"_id": ObjectId(project_id), "step_generation.steps.order": step},
        {"$set": {"step_generation.steps.$.completed": False}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Step not found")

    project_collection.update_one(
        {"_id": ObjectId(project_id)},
        {"$set": {"completed": False}}
    )

    return {"message": "Step reset", "modified": bool(result.modified_count)}


@router.put("/step-feedback/{project_id}/{step}/{feedback}")
def step_feedback(project_id: str, step: int, feedback: int):
    result = project_collection.update_one(
        {"_id": ObjectId(project_id), "step_generation.steps.order": step},
        {"$set": {"step_generation.steps.$.feedback": feedback}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Step not found")
    return {"message": "Step feedback updated", "modified": bool(result.modified_count)}


@router.put("/project/{project_id}/complete")
def complete_all_steps(project_id):
    cursor = project_collection.find_one({
        "_id": ObjectId(project_id)
    })
    if "step_generation" in cursor and "steps" in cursor["step_generation"]:
        print("there is steps")
        print(cursor)
        project_collection.update_one(
            {"_id": ObjectId(project_id)},
            {"$set": {"step_generation.steps.$[].completed": True, "completed": True}}
        )

        return {"message": "Project/Steps updated"}

    return {"message": "No steps found"}


@router.get("/project/{project_id}/progress")
def steps_progress(project_id):
    cursor = project_collection.find_one({
        "_id": ObjectId(project_id)
    })

    if "step_generation" in cursor and "steps" in cursor["step_generation"]:
        steps = list(cursor["step_generation"]["steps"])

        print("there is steps")
        print(steps)

        count = 0
        for s in steps:
            if "completed" in s and s["completed"] == True:
                count += 1

        return count / len(steps)

    return 0
