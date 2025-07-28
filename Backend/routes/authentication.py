from fastapi import APIRouter, HTTPException, Header, Request, Query, Query
from db import users_collection
from pydantic import BaseModel, EmailStr

router = APIRouter()


class AccountData(BaseModel):
    firstName: str
    lastName: str
    email: EmailStr
    password: str

@router.post("/create-profile")
def create_user_profile(data: AccountData):

    if users_collection.find_one({"email": data.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = {
        "firstName": data.firstName,
        "lastName": data.lastName,
        "email": data.email,
        "password": data.password
    }
    
    result = users_collection.insert_one(user)
    return {"success": True, "message": "Account created", "id": str(result.inserted_id)}