from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
from bson import ObjectId
from db import project_collection, conversations_collection
from datetime import datetime

router = APIRouter()

class Project(BaseModel):
    projectTitle: str
    description: str
    detailDescription: str
    projectImages: List[str]
    imagesDescription: str
    userPrevExperience: str
    currentTools: List[str]
    currentToolsImages: List[str]
    userId: str  # store as ObjectId

@router.post("/projects")
def create_project(project: Project):
    project_dict = project.dict()
    project_dict["userId"] = ObjectId(project.userId)
    project_dict["createdAt"] = datetime.utcnow()

    # Insert project
    result = project_collection.insert_one(project_dict)
    project_id = result.inserted_id

    # Create conversation tied to this project
    conversations_collection.insert_one({
    "projectId": project_id,
    "type": "agent1"
})

    return {"id": str(project_id)}

@router.get("/projects/{project_id}")
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
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Project not found or no changes made")
    return {"message": "Project updated"}

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