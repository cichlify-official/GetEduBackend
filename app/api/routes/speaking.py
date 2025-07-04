from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import os
import uuid
from typing import Optional

from app.database import get_db
from app.models.models import User
from app.api.auth.auth import get_current_active_user

router = APIRouter(prefix="/api/speaking", tags=["Speaking Tasks"])

@router.post("/submit")
async def submit_speaking_task(
    audio_file: UploadFile = File(...),
    task_type: str = Form("part1"),
    question: str = Form(""),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit an audio file for speaking analysis"""
    
    # Validate file type
    if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be audio format")
    
    # Generate unique filename
    file_extension = audio_file.filename.split('.')[-1] if '.' in audio_file.filename else 'wav'
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join("uploads", unique_filename)
    
    # Save file
    os.makedirs("uploads", exist_ok=True)
    with open(file_path, "wb") as f:
        content = await audio_file.read()
        f.write(content)
    
    # For now, return success - we'll add actual analysis later
    return {
        "message": "Audio file uploaded successfully",
        "filename": unique_filename,
        "task_type": task_type,
        "question": question,
        "file_size": len(content),
        "status": "uploaded",
        "note": "Speaking analysis coming soon!"
    }

@router.get("/demo/analyze-text")
async def demo_speaking_analysis(
    text: str,
    current_user: User = Depends(get_current_active_user)
):
    """Demo endpoint: analyze speaking from text (simulating transcription)"""
    
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    # Simple speaking analysis based on text
    word_count = len(text.split())
    sentence_count = len([s for s in text.split('.') if s.strip()])
    
    # Basic fluency metrics
    words_per_sentence = word_count / max(sentence_count, 1)
    
    # Calculate scores (simplified)
    fluency_score = min(6.0 + (words_per_sentence - 10) * 0.2, 9.0) if words_per_sentence > 5 else 5.0
    lexical_score = min(5.0 + (len(set(text.lower().split())) / max(word_count, 1)) * 6, 9.0)
    grammar_score = 6.0 if ',' in text and len(text.split()) > 10 else 5.5
    pronunciation_score = 6.5  # Demo score
    
    overall_band = round((fluency_score + lexical_score + grammar_score + pronunciation_score) / 4, 1)
    
    return {
        "message": "Speaking analysis completed (demo)",
        "scores": {
            "fluency_coherence": fluency_score,
            "lexical_resource": lexical_score,
            "grammatical_range": grammar_score,
            "pronunciation": pronunciation_score,
            "overall_band": overall_band
        },
        "analysis": {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "words_per_sentence": round(words_per_sentence, 1),
            "vocabulary_diversity": round(len(set(text.lower().split())) / max(word_count, 1), 2)
        },
        "feedback": {
            "strengths": ["Good attempt at speaking task"],
            "improvements": ["Continue practicing for better fluency"],
            "suggestions": ["Speak for longer periods", "Use more varied vocabulary"]
        }
    }
