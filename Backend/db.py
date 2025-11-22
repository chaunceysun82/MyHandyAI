from pymongo import MongoClient
from dotenv import load_dotenv
from fastapi import HTTPException
import os

load_dotenv()

MONGO_URI = os.getenv("MongoUri")
DB_NAME = os.getenv("DB")

# Connect to Mongo Atlas
try:
    client = MongoClient(MONGO_URI)
    print( "Connection Succeded")
except Exception as e:
    print("❌ ERROR:", str(e))
    raise HTTPException(status_code=500, detail="Internal Server Error")

db = client[DB_NAME]
users_collection = db["Users"]
project_collection = db["Project"]
steps_collection = db["ProjectSteps"]
conversations_collection = db["Conversations"]
conversations_step_collection = db["StepConversations"]
questions_collection = db["Questions"]
tools_collection = db["Tools"] 


