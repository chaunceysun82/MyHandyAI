from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Any
from bson import ObjectId
from db import project_collection, conversations_collection
from datetime import datetime

router = APIRouter()

class Project(BaseModel):
    projectTitle: str
    userId: str

def _maybe_iso(dt):
    return dt.isoformat() if isinstance(dt, datetime) else None

def _serialize_project(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB doc to JSON-serializable dict."""
    return {
        "_id": str(doc.get("_id")) if doc.get("_id") is not None else None,
        "userId": str(doc.get("userId")) if doc.get("userId") is not None else "",
        "projectTitle": doc.get("projectTitle", ""),
        "createdAt": _maybe_iso(doc.get("createdAt")),
        "description": doc.get("description", ""),
        "detailDescription": doc.get("detailDescription", ""),
        "projectImages": doc.get("projectImages", []),
        "imagesDescription": doc.get("imagesDescription", ""),
        "userPrevExperience": doc.get("userPrevExperience", ""),
        "currentTools": doc.get("currentTools", []),
        "currentToolsImages": doc.get("currentToolsImages", []),
        "lastActivity": _maybe_iso(doc.get("lastActivity")),
        "percentComplete": doc.get("percentComplete", 0),
    }

def _ensure_object_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id format")

@router.post("/projects")
def create_project(project: ProjectCreate):
    now = datetime.utcnow()
    project_doc = {
        "projectTitle": project.projectTitle,
        "userId": project.userId,  # kept as string to match current data
        "createdAt": now,
        "description": "",
        "detailDescription": "",
        "projectImages": [],
        "imagesDescription": "",
        "userPrevExperience": "",
        "currentTools": [],
        "currentToolsImages": [],
        "lastActivity": now,
        "percentComplete": 0,
    }

    result = project_collection.insert_one(project_doc)
    project_id = result.inserted_id

    # conversations_collection.insert_one({
    #     "projectId": project_id,
    #     "type": "agent1"
    # })

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