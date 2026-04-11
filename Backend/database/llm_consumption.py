from datetime import datetime
from typing import Any, Dict, Optional

from pymongo import DESCENDING
from pymongo.collection import Collection
from pymongo.database import Database

from database.mongodb import mongodb

database: Database = mongodb.get_database()
llm_consumption_collection: Collection = database.get_collection("LLMConsumption")

OPENAI_PRICING_PER_1M_TOKENS = {
    "gpt-5": {"input": 1.25, "output": 10.0},
    "gpt-5-mini": {"input": 0.25, "output": 2.0},
    "gpt-5-nano": {"input": 0.05, "output": 0.4},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
}

GOOGLE_IMAGEN_PRICING_PER_IMAGE = {
    "imagen 4 ultra": 0.06,
    "imagen 4 fast": 0.02,
    "imagen 4": 0.04,
    "imagen 3 fast": 0.02,
    "imagen 3": 0.04,
    "imagen 2": 0.02,
    "imagen 1": 0.02,
}


def ensure_indexes() -> None:
    llm_consumption_collection.create_index([("createdAt", DESCENDING)])
    llm_consumption_collection.create_index([("projectId", DESCENDING), ("createdAt", DESCENDING)])
    llm_consumption_collection.create_index([("userId", DESCENDING), ("createdAt", DESCENDING)])
    llm_consumption_collection.create_index([("model", DESCENDING), ("createdAt", DESCENDING)])


ensure_indexes()


def normalize_usage(usage: Optional[Dict[str, Any]]) -> Dict[str, int]:
    usage = usage or {}
    input_tokens = usage.get("input_tokens")
    if input_tokens is None:
        input_tokens = usage.get("prompt_tokens")

    output_tokens = usage.get("output_tokens")
    if output_tokens is None:
        output_tokens = usage.get("completion_tokens")

    total_tokens = usage.get("total_tokens")
    if total_tokens is None:
        total_tokens = (input_tokens or 0) + (output_tokens or 0)

    return {
        "input_tokens": int(input_tokens or 0),
        "output_tokens": int(output_tokens or 0),
        "total_tokens": int(total_tokens or 0),
    }


def estimate_openai_cost_usd(model: str, input_tokens: int, output_tokens: int) -> Optional[float]:
    pricing = OPENAI_PRICING_PER_1M_TOKENS.get(model)
    if not pricing:
        return None

    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 8)


def estimate_google_image_cost_usd(model: str, image_count: int = 1) -> Optional[float]:
    normalized = (model or "").lower().replace("-", " ").replace("_", " ").strip()
    for model_key, price_per_image in GOOGLE_IMAGEN_PRICING_PER_IMAGE.items():
        if model_key in normalized:
            return round(price_per_image * image_count, 8)
    return None


def insert_llm_consumption(
    *,
    provider: str,
    model: str,
    operation: str,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    usage: Optional[Dict[str, Any]] = None,
    endpoint: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    estimated_cost_usd: Optional[float] = None,
) -> Optional[str]:
    normalized_usage = normalize_usage(usage)
    if normalized_usage["total_tokens"] == 0 and estimated_cost_usd is None:
        return None

    if estimated_cost_usd is None and provider == "openai":
        estimated_cost_usd = estimate_openai_cost_usd(
            model,
            normalized_usage["input_tokens"],
            normalized_usage["output_tokens"],
        )

    result = llm_consumption_collection.insert_one(
        {
            "provider": provider,
            "model": model,
            "operation": operation,
            "projectId": project_id,
            "userId": user_id,
            "endpoint": endpoint,
            "usage": normalized_usage,
            "estimatedCostUsd": estimated_cost_usd,
            "metadata": metadata or {},
            "createdAt": datetime.utcnow(),
        }
    )
    return str(result.inserted_id)


def record_openai_response_usage(
    response_json: Dict[str, Any],
    *,
    model: str,
    operation: str,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    endpoint: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    return insert_llm_consumption(
        provider="openai",
        model=model,
        operation=operation,
        project_id=project_id,
        user_id=user_id,
        usage=response_json.get("usage"),
        endpoint=endpoint,
        metadata=metadata,
    )


def record_langchain_usage(
    usage_metadata: Optional[Dict[str, Any]],
    *,
    model: str,
    operation: str,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    return insert_llm_consumption(
        provider="openai",
        model=model,
        operation=operation,
        project_id=project_id,
        user_id=user_id,
        usage=usage_metadata,
        endpoint="langchain",
        metadata=metadata,
    )


def record_google_image_generation(
    *,
    model: str,
    operation: str,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    image_count: int = 1,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    estimated_cost_usd = estimate_google_image_cost_usd(model, image_count=image_count)
    return insert_llm_consumption(
        provider="google",
        model=model,
        operation=operation,
        project_id=project_id,
        user_id=user_id,
        usage={"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
        endpoint="vertex_imagen",
        metadata={**(metadata or {}), "imageCount": image_count},
        estimated_cost_usd=estimated_cost_usd,
    )
