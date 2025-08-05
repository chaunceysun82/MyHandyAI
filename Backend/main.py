# Main.py
from routes.chat import router as chat_router
from routes.tool_detection_demo import router as demo_router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
#from routes.profile_creation import router as profile_router
from routes import user, project, steps, chat
from mangum import Mangum

from fastapi import FastAPI

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
#app.include_router(auth_router)
# app.include_router(profile_router)
app.include_router(demo_router)
app.include_router(user.router)
app.include_router(project.router)
app.include_router(steps.router)
app.include_router(chat_router)


#handler for aws
handler = Mangum(app)
