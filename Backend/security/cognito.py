from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from config.settings import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_jwks_client() -> PyJWKClient:
    settings = get_settings()

    if not settings.COGNITO_REGION or not settings.COGNITO_USER_POOL_ID:
        raise RuntimeError("Cognito settings are not configured")

    jwks_url = (
        f"https://cognito-idp.{settings.COGNITO_REGION}.amazonaws.com/"
        f"{settings.COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    )

    return PyJWKClient(jwks_url)


def get_cognito_issuer() -> str:
    settings = get_settings()

    if not settings.COGNITO_REGION or not settings.COGNITO_USER_POOL_ID:
        raise RuntimeError("Cognito settings are not configured")

    return (
        f"https://cognito-idp.{settings.COGNITO_REGION}.amazonaws.com/"
        f"{settings.COGNITO_USER_POOL_ID}"
    )


def verify_cognito_token(token: str) -> dict:
    settings = get_settings()

    if not settings.COGNITO_APP_CLIENT_ID:
        raise RuntimeError("COGNITO_APP_CLIENT_ID is not configured")

    try:
        signing_key = get_jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.COGNITO_APP_CLIENT_ID,
            issuer=get_cognito_issuer(),
            options={"require": ["exp", "iat", "iss", "sub"]},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Cognito token",
        ) from exc

    if claims.get("token_use") != "id":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Expected Cognito ID token",
        )

    return claims


def get_current_cognito_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization token",
        )

    return verify_cognito_token(credentials.credentials)
