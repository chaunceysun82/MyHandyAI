# Backend/main.py
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from config.logger import setup_logging
from config.settings import get_settings
from database.mongodb import mongodb

load_dotenv()
settings = get_settings()

# Routers
from routes import (
    user,
    project,
    steps,
    generation,
    feedback,
    information_gathering_agent,
    project_assistant_agent
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    mongodb.initialize()

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
app.include_router(user.router, tags=["User"])
app.include_router(project.router, tags=["Project"])
app.include_router(steps.router, tags=["Steps"])
app.include_router(generation.router, tags=["Generation"])
app.include_router(feedback.router, tags=["Feedback"])
app.include_router(information_gathering_agent.router, prefix="/api/v1", tags=["Information Gathering Agent"])
app.include_router(project_assistant_agent.router, prefix="/api/v1", tags=["Project Assistant Agent"])

# handler for AWS
handler = Mangum(app)
