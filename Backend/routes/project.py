from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
from fastapi.encoders import jsonable_encoder
from bson import ObjectId
from db import project_collection, conversations_collection
from datetime import datetime

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

        return {"message":"Projects found", "projects":results}
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

    # Delete the project
    result = project_collection.delete_one({"_id": project_obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete related conversations
    conversations_collection.delete_many({"projectId": project_obj_id})

    return {"message": "Project and associated conversations deleted"}