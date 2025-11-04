from fastapi import APIRouter

from config.settings import get_settings

router = APIRouter(prefix="")

settings = get_settings()


@router.get("/healthy")
def health_check():
    return {'status': 'Healthy'}
