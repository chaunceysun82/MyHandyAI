from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId
from db import steps_collection
from datetime import datetime

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
    order: int
    title: str
    est_time_min: int = 0
    time_text: str = ""
    instructions: List[str] = []
    status: str = "pending"
    tools_needed: List[str] = []
    safety_warnings: List[str] = []
    tips: List[str] = []
    completed: bool = False
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

@router.post("/steps")
def create_step(step: Step):
    step_dict = step.dict()
    step_dict["projectId"] = ObjectId(step.projectId)
    step_dict["createdAt"] = datetime.utcnow()
    step_dict["updatedAt"] = datetime.utcnow()
    result = steps_collection.insert_one(step_dict)
    return {"id": str(result.inserted_id)}

@router.get("/projects/{project_id}/steps")
def get_steps_by_project(project_id: str):
    steps = list(
        steps_collection.find({"projectId": ObjectId(project_id)})
                        .sort("order", 1)
    )
    for step in steps:
        step["_id"] = str(step["_id"])
        step["projectId"] = str(step["projectId"])
    return steps

@router.put("/steps/{step_id}")
def update_step(step_id: str, update_data: dict):
    update_data["updatedAt"] = datetime.utcnow()
    result = steps_collection.update_one(
        {"_id": ObjectId(step_id)},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Step not found")
    return {"message": "Step updated"}