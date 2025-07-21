# Main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.authentication import router as auth_router
#from routes.profile_creation import router as profile_router
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
async def root():
    return {"message": "Hello, FastAPI!"}

# Register routes
app.include_router(auth_router)
# app.include_router(profile_router)

#handler for aws
handler = Mangum(app)