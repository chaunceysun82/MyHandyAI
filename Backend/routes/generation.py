import json
import os
# Import tools reuse functions from chatbot
import sys

import boto3
from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pymongo.collection import Collection
from pymongo.database import Database

from config.settings import get_settings
from database.mongodb import mongodb
from routes.project import update_project

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

router = APIRouter(prefix="/generation")
settings = get_settings()

sqs = boto3.client("sqs", region_name=settings.AWS_REGION)
database: Database = mongodb.get_database()
project_collection: Collection = database.get_collection("Project")
steps_collection: Collection = database.get_collection("ProjectSteps")


# Pydantic models for request/response

@router.get("/tools/{project_id}")
async def get_generated_tools(project_id: str):
    doc = project_collection.find_one({"_id": ObjectId(project_id)}, {"tool_generation": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    if "tool_generation" not in doc or doc["tool_generation"] is None:
        raise HTTPException(status_code=404, detail="Tools not generated yet")
    return {"project_id": project_id, "tools_data": doc["tool_generation"]}


@router.get("/steps/{project_id}")
async def get_generated_steps(project_id: str):
    doc = project_collection.find_one({"_id": ObjectId(project_id)}, {"step_generation": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    steps_payload = doc.get("step_generation")
    if not steps_payload:
        raise HTTPException(status_code=404, detail="Steps not generated yet")
    return {"project_id": project_id, "steps_data": steps_payload}


@router.get("/estimation/{project_id}")
async def get_generated_estimation(project_id: str):
    doc = project_collection.find_one({"_id": ObjectId(project_id)}, {"estimation_generation": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Project not found")
    if "estimation_generation" not in doc or doc["estimation_generation"] is None:
        raise HTTPException(status_code=404, detail="Estimation not generated yet")
    return {"project_id": project_id, "estimation_data": doc["estimation_generation"]}


@router.post("/all/{project}")
async def generate(project):
    try:
        cursor = project_collection.find_one({"_id": ObjectId(project)})
        if not cursor:
            print("Project not found")
            return {"message": "Project not found"}
        message = {
            "project": project
        }

        update_project(str(cursor["_id"]), {"generation_status": "in-progress"})

        # LOCAL TESTING: Comment out SQS and call lambda_handler directly
        # Uncomment the block below for local testing
        # from worker.worker_lambda import lambda_handler
        # mock_event = {"Records": [{"body": json.dumps(message)}]}
        # mock_context = None
        # lambda_handler(mock_event, mock_context)
        # return {"message": "Generation completed (local test)"}

        # PRODUCTION: Use SQS
        sqs.send_message(
            QueueUrl=settings.AWS_SQS_URL,
            MessageBody=json.dumps(message)
        )
        return {"message": "Request In progress"}
    except Exception as e:
        print(f"Error triggering generation: {e}")
        return {"message": "Request could not be processed"}


@router.get("/status/{project}")
async def status(project):
    cursor = project_collection.find_one({"_id": ObjectId(project)})
    if not cursor:
        print("Project not found")
        return {"message": "Project not found"}

    if not "generation_status" in cursor:
        return {"message": "Generation not started"}

    if "tool_generation" in cursor and "status" in cursor["tool_generation"]:
        tools = cursor["tool_generation"]["status"]
    else:
        tools = "Not started"

    if "step_generation" in cursor and "status" in cursor["step_generation"]:
        steps = cursor["step_generation"]["status"]
    else:
        steps = "Not started"

    if "estimation_generation" in cursor and "status" in cursor["estimation_generation"]:
        estimation = cursor["estimation_generation"]["status"]
    else:
        estimation = "Not started"

    if cursor["generation_status"] == "complete":
        return {"message": "generation completed",
                "tools": tools,
                "steps": steps,
                "estimation": estimation}

    if cursor["generation_status"] == "in-progress":
        return {"message": "generation in progress",
                "tools": tools,
                "steps": steps,
                "estimation": estimation}

    return {"message": "Something went wrong"}
