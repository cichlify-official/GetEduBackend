# routes/recording.py

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from uuid import uuid4
import os

router = APIRouter(prefix="/recording", tags=["Recording"])

@router.post("/audio")
async def upload_audio(file: UploadFile = File(...)):
    temp_path = f"/tmp/{uuid4()}_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await file.read())
    
    # Add transcription or feedback logic here
    return JSONResponse(content={"status": "success", "filename": temp_path})
