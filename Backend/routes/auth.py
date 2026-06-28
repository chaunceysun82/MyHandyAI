from fastapi import APIRouter, Depends, Response

from security.cognito import get_current_cognito_user
from security.current_user import sync_cognito_user

router = APIRouter(prefix="/auth")


@router.options("/me")
def sync_current_user_preflight():
    return Response(status_code=204)


@router.post("/me")
def sync_current_user(claims: dict = Depends(get_current_cognito_user)):
    return sync_cognito_user(claims)
