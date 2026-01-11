from datetime import datetime
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from pymongo.collection import Collection
from pymongo.database import Database

from database.mongodb import mongodb

router = APIRouter()
database: Database = mongodb.get_database()
users_collection: Collection = database.get_collection("Users")
conversations_collection: Collection = database.get_collection("Conversations")
questions_collection: Collection = database.get_collection("Questions")


class User(BaseModel):
    firstname: str
    lastname: str
    password: Optional[str] = None
    email: EmailStr
    google_flag: Optional[bool] = None
    describe: Optional[str] = None
    experienceLevel: Optional[str] = None
    confidence: Optional[int] = None
    tools: Optional[str] = None
    interestedProjects: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None


class LoginData(BaseModel):
    email: EmailStr
    password: Optional[str] = None
    google_flag: Optional[bool] = None


@router.get("/user")
def get_current_user(email: str):
    user = users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["_id"] = str(user["_id"])
    return user


@router.post("/users")
def create_user(user: User):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already exists")

    # For Google users, password is not required
    if user.google_flag is True:
        # Google user - password can be empty or None
        pass
    else:
        # Email user - password is required
        if not user.password:
            raise HTTPException(status_code=400, detail="Password required for email users")

    new_user = user.dict()
    new_user["createdAt"] = datetime.utcnow()
    result = users_collection.insert_one(new_user)

    return {"id": str(result.inserted_id)}


@router.get("/users/{user_id}")
def get_user(user_id: str):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["_id"] = str(user["_id"])
    return user


@router.get("/onboarding")
def get_onbording():
    questions = list(questions_collection.find())
    if not questions:
        raise HTTPException(status_code=404, detail="No questions")
    for q in questions:
        q["_id"] = str(q["_id"])
    return questions


@router.delete("/users/{user_id}")
def delete_user(user_id: str):
    result = users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}


@router.post("/login")
def login(data: LoginData):
    user = users_collection.find_one({"email": data.email})
    if data.google_flag:
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": "Login successful", "id": str(user["_id"])}
    if not user or user.get("password") != data.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful", "id": str(user["_id"])}


@router.put("/users/{user_id}")
def update_user(user_id: str, update_data: dict):
    result = users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found or no changes")
    return {"message": "User updated"}
