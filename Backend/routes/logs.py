from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from pymongo import DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database

from database.mongodb import mongodb

router = APIRouter()
database: Database = mongodb.get_database()
logs_collection: Collection = database.get_collection("Logs")

LOG_EVENT_TYPES = {
    "app_entered",
    "user_logged_in",
    "project_started",
    "solution_generation_started",
    "step_viewed",
    "project_finished",
}


def ensure_indexes() -> None:
    logs_collection.create_index([("eventType", DESCENDING), ("createdAt", DESCENDING)])
    logs_collection.create_index([("userId", DESCENDING), ("createdAt", DESCENDING)])
    logs_collection.create_index([("projectId", DESCENDING), ("createdAt", DESCENDING)])


ensure_indexes()


class LogEventRequest(BaseModel):
    eventType: Literal[
        "app_entered",
        "user_logged_in",
        "project_started",
        "solution_generation_started",
        "step_viewed",
        "project_finished",
    ]
    userId: Optional[str] = None
    projectId: Optional[str] = None
    stepNumber: Optional[int] = Field(default=None, ge=0)
    path: Optional[str] = None
    sessionId: Optional[str] = None
    visitorId: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LogEventResponse(BaseModel):
    id: str
    message: str


def insert_log_event(
    event_type: str,
    *,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    step_number: Optional[int] = None,
    path: Optional[str] = None,
    session_id: Optional[str] = None,
    visitor_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    if event_type not in LOG_EVENT_TYPES:
        raise ValueError(f"Unsupported log event type: {event_type}")

    document = {
        "eventType": event_type,
        "userId": user_id,
        "projectId": project_id,
        "stepNumber": step_number,
        "path": path,
        "sessionId": session_id,
        "visitorId": visitor_id,
        "metadata": metadata or {},
        "createdAt": datetime.utcnow(),
    }
    result = logs_collection.insert_one(document)
    return str(result.inserted_id)


@router.post("/logs", response_model=LogEventResponse)
def create_log_event(payload: LogEventRequest):
    log_id = insert_log_event(
        payload.eventType,
        user_id=payload.userId,
        project_id=payload.projectId,
        step_number=payload.stepNumber,
        path=payload.path,
        session_id=payload.sessionId,
        visitor_id=payload.visitorId,
        metadata=payload.metadata,
    )
    return {"id": log_id, "message": "Log event created"}


@router.get("/logs")
def list_log_events(
    event_type: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    if event_type and event_type not in LOG_EVENT_TYPES:
        raise HTTPException(status_code=400, detail="Invalid event_type")

    query: Dict[str, Any] = {}
    if event_type:
        query["eventType"] = event_type
    if user_id:
        query["userId"] = user_id
    if project_id:
        query["projectId"] = project_id

    events: List[Dict[str, Any]] = list(
        logs_collection.find(query).sort("createdAt", DESCENDING).limit(limit)
    )

    for event in events:
        event["_id"] = str(event["_id"])

    return events


@router.get("/logs/summary")
def get_logs_summary():
    pipeline = [
        {
            "$group": {
                "_id": "$eventType",
                "count": {"$sum": 1},
            }
        }
    ]

    summary = {event_type: 0 for event_type in LOG_EVENT_TYPES}
    for row in logs_collection.aggregate(pipeline):
        summary[row["_id"]] = row["count"]

    return summary
