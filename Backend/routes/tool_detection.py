from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import List

router = APIRouter(prefix="/api/tools", tags=["tools"])

# for now it's a stub
async def detect_tools(image_bytes: bytes) -> List[dict]:
    
    return [{"name": "cordless drill", "confidence": 0.92}]

@router.post("/detect")
async def detect_endpoint(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")
    image_bytes = await file.read()
    results = await detect_tools(image_bytes)
    return {"tools": results}
