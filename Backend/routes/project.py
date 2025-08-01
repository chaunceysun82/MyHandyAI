from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
from bson import ObjectId
from db import project_collection

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
    result = project_collection.insert_one(project_dict)
    return {"id": str(result.inserted_id)}

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
    result = project_collection.delete_one({"_id": ObjectId(project_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"message": "Project deleted"}