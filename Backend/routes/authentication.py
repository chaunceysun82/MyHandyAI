from fastapi import APIRouter, HTTPException, Header, Request, Query, Query
from db import users_collection
from pydantic import BaseModel, EmailStr

router = APIRouter()


class AccountData(BaseModel):
    name: str
    age: int
    email: EmailStr

@router.post("/create-profile")
def create_user_profile(data: AccountData):

    if users_collection.find_one({"email": data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user= {
        "name": data.name,
        "age":data.age,
        "email":data.email
    }
    
    result = users_collection.insert_one(user)
    return {"success": True, "message": "Account created", "id": str(result.inserted_id)}