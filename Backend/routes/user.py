from fastapi import APIRouter, HTTPException
from db import users_collection, conversations_collection
from pydantic import BaseModel, EmailStr
from bson import ObjectId

router = APIRouter()

class User(BaseModel):
    firstname: str
    lastname: str
    password: str
    email: EmailStr

@router.post("/users")
def create_user(user: User):
    if users_collection.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already exists")
    
    new_user = user.dict()
    result = users_collection.insert_one(new_user)

    conversations_collection.insert_one({ "userId": result.inserted_id })

    return {"id": str(result.inserted_id)}

@router.get("/user-login")
def login_user(email: str, password: str):
    user = users_collection.find_one({"_id": ObjectId(email)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.get("password")!= password:
        raise HTTPException(status_code=404, detail="Incorrect Password")

    user["_id"] = str(user["_id"])

    return user

@router.get("/users/{user_id}")
def get_user(user_id: str):
    user = users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user["_id"] = str(user["_id"])
    return user

@router.delete("/users/{user_id}")
def delete_user(user_id: str):
    result = users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}
