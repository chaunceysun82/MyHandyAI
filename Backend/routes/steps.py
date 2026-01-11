from datetime import datetime
from typing import List, Optional, Annotated

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pymongo.collection import Collection
from pymongo.database import Database

from database.mongodb import mongodb

router = APIRouter()
database: Database = mongodb.get_database()
steps_collection: Collection = database.get_collection("ProjectSteps")


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
    progress: int = 0  # percentage
    tools_needed: List[str] = []
    safety_warnings: List[str] = []
    tips: List[str] = []
    completed: bool = False
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class ProgressUpdate(BaseModel):
    progress: Annotated[int, Field(ge=0, le=100)]  # 0–100
    status: Optional[str] = None


@router.post("/steps")
def create_step(step: Step):
    step_dict = step.dict()
    step_dict["projectId"] = ObjectId(step.projectId)

    p = max(0, min(100, int(step_dict.get("progress", 0))))
    step_dict["progress"] = p
    if p >= 100:
        step_dict["completed"] = True
        step_dict["status"] = "completed"
    elif p > 0 and step_dict.get("status", "pending") == "pending":
        step_dict["status"] = "in-progress"

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


@router.put("/steps/{step_id}/progress")
def update_step_progress(step_id: str, body: ProgressUpdate):
    # compute new flags
    new_progress = int(body.progress)
    update = {
        "progress": new_progress,
        "updatedAt": datetime.utcnow()
    }
    # derive completed/status if not overridden
    if body.status is not None:
        update["status"] = body.status.lower()
    else:
        if new_progress >= 100:
            update["status"] = "completed"
        elif new_progress > 0:
            update["status"] = "in-progress"
        else:
            update["status"] = "pending"

    update["completed"] = (update["status"] == "completed")

    result = steps_collection.update_one(
        {"_id": ObjectId(step_id)},
        {"$set": update}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Step not found")
    return {"message": "Progress updated", "modified": bool(result.modified_count)}


@router.get("/projects/{project_id}/progress")
def get_project_progress(project_id: str):
    cur = steps_collection.find(
        {"projectId": ObjectId(project_id)},
        {"order": 1, "title": 1, "status": 1, "progress": 1}
    ).sort("order", 1)

    steps = []
    total = 0
    count = 0
    completed = 0

    for s in cur:
        prog = int(s.get("progress", 0) or 0)
        st = (s.get("status") or "pending").lower()
        steps.append({
            "id": str(s["_id"]),
            "order": s.get("order"),
            "title": s.get("title", ""),
            "status": st,
            "progress": prog
        })
        total += prog
        count += 1
        if st == "completed" or prog >= 100:
            completed += 1

    if count == 0:
        return {
            "project_id": project_id,
            "total_steps": 0,
            "completed_steps": 0,
            "average_progress": 0,
            "steps": []
        }

    avg = round(total / count)
    return {
        "project_id": project_id,
        "total_steps": count,
        "completed_steps": completed,
        "average_progress": avg,  # 0–100 for the homepage bar
        "steps": steps
    }


@router.put("/projects/{project_id}/complete-all")
def complete_all_steps(project_id: str):
    result = steps_collection.update_many(
        {"projectId": ObjectId(project_id)},
        {
            "$set": {
                "progress": 100,
                "status": "completed",
                "completed": True,
                "updatedAt": datetime.utcnow()
            }
        }
    )
    return {
        "message": "All steps marked as completed",
        "modified_count": result.modified_count
    }
