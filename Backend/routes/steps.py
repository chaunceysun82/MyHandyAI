from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, conint
from typing import List, Optional, Annotated, Dict, Any
from bson import ObjectId
from db import steps_collection, tools_collection
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
    progress: int = 0  #percentage
    tools_needed: List[str] = []
    safety_warnings: List[str] = []
    tips: List[str] = []
    completed: bool = False
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

class ProgressUpdate(BaseModel):
    progress: Annotated[int, Field(ge=0, le=100)]  # 0–100
    status: Optional[str] = None

class ToolCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    price: float = 0.0
    risk_factors: str = ""
    safety_measures: str = ""
    image_link: Optional[str] = None
    amazon_link: Optional[str] = None
    category: str = "general"
    tags: List[str] = []
    usage_count: int = 0
    last_used: Optional[datetime] = None

class ToolUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    risk_factors: Optional[str] = None
    safety_measures: Optional[str] = None
    image_link: Optional[str] = None
    amazon_link: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    usage_count: Optional[int] = None
    last_used: Optional[datetime] = None

def _serialize_tool(doc: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "_id": str(doc.get("_id")),
        "name": doc.get("name", ""),
        "description": doc.get("description", ""),
        "price": float(doc.get("price", 0.0) or 0.0),
        "risk_factors": doc.get("risk_factors", ""),
        "safety_measures": doc.get("safety_measures", ""),
        "image_link": doc.get("image_link"),
        "amazon_link": doc.get("amazon_link"),
        "category": doc.get("category", "general"),
        "tags": doc.get("tags", []),
        "usage_count": int(doc.get("usage_count") or 0),
        "last_used": doc.get("last_used"),
        # accept both created_at and createdAt from DB
        "created_at": doc.get("created_at") or doc.get("createdAt"),
        "updated_at": doc.get("updated_at") or doc.get("updatedAt"),
    }

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
        "average_progress": avg,         # 0–100 for the homepage bar
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

#Tools
@router.get("/tools")
def list_tools(
    q: Optional[str] = Query(default=None, description="Search by name (regex)"),
    category: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None, description="Filter tools that contain this tag"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    criteria: Dict[str, Any] = {}
    if q:
        criteria["name"] = {"$regex": q, "$options": "i"}
    if category:
        criteria["category"] = category
    if tag:
        criteria["tags"] = {"$in": [tag]}

    cur = tools_collection.find(criteria).skip(skip).limit(limit).sort("name", 1)
    docs = [_serialize_tool(d) for d in cur]
    total = tools_collection.count_documents(criteria)
    return {"total": total, "count": len(docs), "items": docs}

@router.get("/tools/{tool_id}")
def get_tool(tool_id: str):
    try:
        _id = ObjectId(tool_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid tool id")
    doc = tools_collection.find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Tool not found")
    return _serialize_tool(doc)

@router.post("/tools", status_code=201)
def create_tool(body: ToolCreate):
    now = datetime.utcnow()
    doc = body.dict()
    doc["created_at"] = now
    doc["updated_at"] = now
    doc["usage_count"] = int(doc.get("usage_count") or 0)
    res = tools_collection.insert_one(doc)
    return {"id": str(res.inserted_id)}

@router.put("/tools/{tool_id}")
def update_tool(tool_id: str, body: ToolUpdate):
    try:
        _id = ObjectId(tool_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid tool id")

    update = {k: v for k, v in body.dict(exclude_unset=True).items() if v is not None}
    if not update:
        return {"message": "Nothing to update", "modified": False}

    update["updated_at"] = datetime.utcnow()
    result = tools_collection.update_one({"_id": _id}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {"message": "Tool updated", "modified": bool(result.modified_count)}

@router.delete("/tools/{tool_id}", status_code=204)
def delete_tool(tool_id: str):
    try:
        _id = ObjectId(tool_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid tool id")
    result = tools_collection.delete_one({"_id": _id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tool not found")
    return