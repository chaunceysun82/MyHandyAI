from datetime import datetime

from fastapi import Depends, HTTPException, status
from database.mongodb import mongodb
from security.cognito import get_current_cognito_user


def get_users_collection():
    return mongodb.get_collection("Users")


def serialize_user(user: dict) -> dict:
    user_id = str(user["_id"])

    return {
        "id": user_id,
        "_id": user_id,
        "cognito_sub": user.get("cognito_sub"),
        "email": user.get("email", ""),
        "firstname": user.get("firstname", ""),
        "lastname": user.get("lastname", ""),
        "describe": user.get("describe"),
        "experienceLevel": user.get("experienceLevel"),
        "confidence": user.get("confidence"),
        "tools": user.get("tools"),
        "interestedProjects": user.get("interestedProjects"),
        "country": user.get("country"),
        "state": user.get("state"),
    }


def sync_cognito_user(claims: dict) -> dict:
    users_collection = get_users_collection()
    cognito_sub = claims["sub"]
    email = claims.get("email", "")
    firstname = claims.get("given_name") or email.split("@")[0] or "User"
    lastname = claims.get("family_name") or ""
    now = datetime.utcnow()

    update = {
        "$set": {
            "cognito_sub": cognito_sub,
            "email": email,
            "firstname": firstname,
            "lastname": lastname,
            "updatedAt": now,
        },
        "$setOnInsert": {
            "createdAt": now,
        },
    }

    existing_user = users_collection.find_one(
        {"$or": [{"cognito_sub": cognito_sub}, {"email": email}]}
    )
    user_filter = (
        {"_id": existing_user["_id"]}
        if existing_user
        else {"cognito_sub": cognito_sub}
    )

    users_collection.update_one(user_filter, update, upsert=True)
    user = users_collection.find_one({"cognito_sub": cognito_sub})

    return serialize_user(user)


def get_current_app_user(claims: dict = Depends(get_current_cognito_user)) -> dict:
    return sync_cognito_user(claims)


def require_user_match(requested_user_id: str, current_user: dict) -> None:
    if requested_user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this user resource",
        )
