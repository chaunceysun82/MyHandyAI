from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId
from db import steps_collection

router = APIRouter()

class Tool(BaseModel):
    name: str
    description: str
    link: Optional[str] = None

class Material(BaseModel):
    name: str
    description: str
    quantity: int
    size: float
    link: Optional[str] = None

class Step(BaseModel):
    projectId: str
    stepNumber: int
    title: str
    description: str
    tools: List[Tool]
    materials: List[Material]
    images: List[str]
    videoTutorialLink: Optional[str] = None
    referenceLinks: Optional[List[str]] = []
    completed: bool = False

# Routes
@router.post("/steps")
def create_step(step: Step):
    step_dict = step.dict()
    step_dict["projectId"] = ObjectId(step.projectId)
    result = steps_collection.insert_one(step_dict)
    return {"id": str(result.inserted_id)}

@router.get("/steps/{step_id}")
def get_step(step_id: str):
    step = steps_collection.find_one({"_id": ObjectId(step_id)})
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    step["_id"] = str(step["_id"])
    step["projectId"] = str(step["projectId"])
    return step

@router.get("/projects/{project_id}/steps")
def get_steps_by_project(project_id: str):
    steps = list(steps_collection.find({"projectId": ObjectId(project_id)}))
    for step in steps:
        step["_id"] = str(step["_id"])
        step["projectId"] = str(step["projectId"])
    return steps

@router.put("/steps/{step_id}")
def update_step(step_id: str, update_data: dict):
    result = steps_collection.update_one(
        {"_id": ObjectId(step_id)},
        {"$set": update_data}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Step not found or no changes made")
    return {"message": "Step updated"}

@router.delete("/steps/{step_id}")
def delete_step(step_id: str):
    result = steps_collection.delete_one({"_id": ObjectId(step_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Step not found")
    return {"message": "Step deleted"}