# feedback.py
import os
from datetime import datetime
from typing import Optional, List

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from pymongo.collection import Collection
from pymongo.database import Database

from database.mongodb import mongodb

router = APIRouter()

database: Database = mongodb.get_database()
project_collection: Collection = database.get_collection("Project")


# ---- helpers ----

def to_obj_id(id_str: str) -> ObjectId:
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid project id")


def find_project_or_404(project_id: str):
    doc = project_collection.find_one({"_id": to_obj_id(project_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    return doc


# ---- models ----
class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comments: Optional[str] = ""


class FeedbackOut(BaseModel):
    ok: bool
    averageRating: Optional[float] = None
    totalFeedback: Optional[int] = None


class CompletionMsg(BaseModel):
    message: str


# Generate completion message (LLM w/ fallback) ----
@router.get("/projects/{project_id}/completion-message", response_model=CompletionMsg)
def completion_message(project_id: str):
    doc = find_project_or_404(project_id)

    title = doc.get("projectTitle", "your project")
    finished = doc.get("completedAt")
    nice_date = (
        datetime.fromisoformat(finished) if isinstance(finished, str)
        else (finished or datetime.utcnow())
    ).strftime("%b %d, %Y")

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:

            import openai
            openai.api_key = api_key
            prompt = (
                f"Write a one-sentence cheerful completion note for a home project titled "
                f"'{title}'. Avoid emojis. Keep it under 20 words."
            )
            resp = openai.Completion.create(
                engine="text-davinci-003",
                prompt=prompt,
                max_tokens=40,
                temperature=0.6,
            )
            text = resp.choices[0].text.strip()
            return {"message": text or f"All done! '{title}' looks great."}
        except Exception:

            pass

    # Fallback message
    return {
        "message": f"All done! '{title}' is completed and looking great as of {nice_date}."
    }


# Store feedback & mark project complete ----
@router.post("/projects/{project_id}/feedback", response_model=FeedbackOut)
def add_feedback(project_id: str, fb: FeedbackIn):
    doc = find_project_or_404(project_id)

    entry = {
        "rating": fb.rating,
        "comments": fb.comments or "",
        "createdAt": datetime.utcnow(),
    }

    # Push feedback, mark completed status/timestamp/lastActivity
    project_collection.update_one(
        {"_id": to_obj_id(project_id)},
        {
            "$push": {"feedback": entry},
            "$set": {
                "status": "completed",
                "completedAt": datetime.utcnow(),
                "lastActivity": datetime.utcnow(),
            },
        },
    )

    # Compute average and count for convenience

    fresh = project_collection.find_one({"_id": to_obj_id(project_id)}, {"feedback": 1})
    fb_list: List[dict] = fresh.get("feedback", []) if fresh else []
    total = len(fb_list)
    avg = sum((f.get("rating", 0) for f in fb_list)) / total if total else None

    project_collection.update_one(
        {"_id": to_obj_id(project_id)},
        {"$set": {"feedbackAverage": avg, "feedbackCount": total}}
    )

    return {"ok": True, "averageRating": avg, "totalFeedback": total}
