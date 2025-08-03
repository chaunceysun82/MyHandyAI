from fastapi import APIRouter, HTTPException
from db import users_collection, conversations_collection, questions_collection
from pydantic import BaseModel, EmailStr
from bson import ObjectId

router = APIRouter()

class User(BaseModel):
    firstname: str
    lastname: str
    password: str
    email: EmailStr

class LoginData(BaseModel):
    email: EmailStr
    password: str

@router.post("/users")
def create_user(user: User):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already exists")
    if not user.password:
        raise HTTPException(status_code=400, detail="invalid password")
    new_user = user.dict()
    result = users_collection.insert_one(new_user)

    conversations_collection.insert_one({ "userId": result.inserted_id })

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
