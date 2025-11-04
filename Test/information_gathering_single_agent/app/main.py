from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config.logger import setup_logging
from config.settings import get_settings
from presentation.routers import health
from presentation.routers.v1 import information_gathering_agent

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory="../static", html=True), name="static")

# V1 APIs
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(information_gathering_agent.router, prefix="/api/v1", tags=["Information Gathering Agent"])

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=settings.APP_PORT)
