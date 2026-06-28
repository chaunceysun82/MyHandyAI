# Backend/main.py
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from config.logger import setup_logging
from config.settings import get_settings
from database.mongodb import mongodb

load_dotenv()
settings = get_settings()
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://my-handy-ai-amc9.vercel.app",
    "https://my-handy-ai.vercel.app"
]

# Routers
from routes import (
    auth,
    user,
    project,
    steps,
    generation,
    feedback,
    llm_consumption,
    logs,
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
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"message": "Hello, FastAPI!"}


@app.options("/{full_path:path}")
def preflight_handler(full_path: str, request: Request):
    origin = request.headers.get("origin")
    allow_origin = origin if origin in CORS_ALLOWED_ORIGINS else CORS_ALLOWED_ORIGINS[0]

    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": allow_origin,
            "Access-Control-Allow-Methods": "DELETE,GET,HEAD,OPTIONS,PATCH,POST,PUT",
            "Access-Control-Allow-Headers": "*",
            "Vary": "Origin",
        },
    )


# Register routes
app.include_router(user.router, tags=["User"])
app.include_router(auth.router, tags=["Auth"])
app.include_router(project.router, tags=["Project"])
app.include_router(steps.router, tags=["Steps"])
app.include_router(generation.router, tags=["Generation"])
app.include_router(feedback.router, tags=["Feedback"])
app.include_router(llm_consumption.router, tags=["LLM Consumption"])
app.include_router(logs.router, tags=["Logs"])
app.include_router(information_gathering_agent.router, prefix="/api/v1", tags=["Information Gathering Agent"])
app.include_router(project_assistant_agent.router, prefix="/api/v1", tags=["Project Assistant Agent"])

# handler for AWS
handler = Mangum(app)
