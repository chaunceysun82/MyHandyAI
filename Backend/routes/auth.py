from fastapi import APIRouter, Depends

from security.cognito import get_current_cognito_user
from security.current_user import sync_cognito_user

router = APIRouter(prefix="/auth")


@router.post("/me")
def sync_current_user(claims: dict = Depends(get_current_cognito_user)):
    return sync_cognito_user(claims)
