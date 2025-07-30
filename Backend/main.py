# Main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
#from routes.profile_creation import router as profile_router
from routes import user, project, steps
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
app.include_router(user.router)
app.include_router(project.router)
app.include_router(steps.router)

#handler for aws
handler = Mangum(app)