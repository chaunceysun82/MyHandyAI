# Backend/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
from starlette.staticfiles import StaticFiles

from config.logger import setup_logging
from config.settings import get_settings

settings = get_settings()

# Routers
from routes import (
    user,
    project,
    steps,
    chatbot,
    generation,
    feedback,
    step_guidance,
    tool_detection,
    information_gathering_agent
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Hello, FastAPI!"}


# Register routes
app.include_router(user.router)
app.include_router(project.router)
app.include_router(steps.router)
app.include_router(chatbot.router)
app.include_router(generation.router)
app.include_router(feedback.router)
app.include_router(step_guidance.router)
app.include_router(tool_detection.router, prefix="/chatbot/tools")
app.include_router(information_gathering_agent.router, prefix="/api/v1", tags=["Information Gathering Agent"])
app.mount("/static", StaticFiles(directory="./static", html=True), name="static")

# handler for AWS
handler = Mangum(app)
