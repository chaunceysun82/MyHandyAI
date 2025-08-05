# Main.py
from routes.tool_detection import router as tool_router
from routes.chat import router as chat_router
from routes.tool_detection_demo import router as demo_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.authentication import router as auth_router
#from routes.profile_creation import router as profile_router
from mangum import Mangum

from fastapi import FastAPI

app = FastAPI()
app.include_router(chat_router)
app.include_router(demo_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hello, FastAPI!"}

# Register routes
app.include_router(auth_router)
# app.include_router(profile_router)
app.include_router(tool_router)

#handler for aws
handler = Mangum(app)