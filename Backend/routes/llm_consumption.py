from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pymongo import DESCENDING

from database.llm_consumption import llm_consumption_collection
from security.current_user import get_current_app_user

router = APIRouter()


@router.get("/llm-consumption")
def list_llm_consumption(
    project_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    model: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: dict = Depends(get_current_app_user),
):
    query: Dict[str, Any] = {}
    if project_id:
        query["projectId"] = project_id
    if user_id:
        query["userId"] = user_id
    if model:
        query["model"] = model

    rows: List[Dict[str, Any]] = list(
        llm_consumption_collection.find(query).sort("createdAt", DESCENDING).limit(limit)
    )
    for row in rows:
        row["_id"] = str(row["_id"])
    return rows


@router.get("/llm-consumption/summary")
def llm_consumption_summary(
    project_id: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
    current_user: dict = Depends(get_current_app_user),
):
    match: Dict[str, Any] = {}
    if project_id:
        match["projectId"] = project_id
    if user_id:
        match["userId"] = user_id

    pipeline: List[Dict[str, Any]] = []
    if match:
        pipeline.append({"$match": match})
    pipeline.append(
        {
            "$group": {
                "_id": {
                    "projectId": "$projectId",
                    "userId": "$userId",
                    "model": "$model",
                },
                "requests": {"$sum": 1},
                "inputTokens": {"$sum": "$usage.input_tokens"},
                "outputTokens": {"$sum": "$usage.output_tokens"},
                "totalTokens": {"$sum": "$usage.total_tokens"},
                "estimatedCostUsd": {"$sum": {"$ifNull": ["$estimatedCostUsd", 0]}},
            }
        }
    )

    return list(llm_consumption_collection.aggregate(pipeline))
