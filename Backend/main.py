# Backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

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
)

app = FastAPI()

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

# handler for AWS
handler = Mangum(app)
