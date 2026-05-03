from functools import lru_cache

from jose import jwt
from jose.exceptions import JOSEError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import requests

from config.settings import get_settings

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache
def get_jwks() -> dict:
    settings = get_settings()

    if not settings.COGNITO_REGION or not settings.COGNITO_USER_POOL_ID:
        raise RuntimeError("Cognito settings are not configured")

    jwks_url = (
        f"https://cognito-idp.{settings.COGNITO_REGION}.amazonaws.com/"
        f"{settings.COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    )

    response = requests.get(jwks_url, timeout=10)
    response.raise_for_status()
    return response.json()


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
        headers = jwt.get_unverified_header(token)
        key = next(
            key
            for key in get_jwks()["keys"]
            if key["kid"] == headers["kid"]
        )

        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=settings.COGNITO_APP_CLIENT_ID,
            issuer=get_cognito_issuer(),
        )
    except (JOSEError, KeyError, StopIteration, requests.RequestException) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Cognito token: {type(exc).__name__}",
        ) from exc

    if claims.get("token_use") != "id":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Expected Cognito ID token, got {claims.get('token_use', 'unknown')}",
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
