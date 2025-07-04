from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List

from app.database import get_db
from app.models.models import User, Essay, EssayGrading
from app.api.auth.auth import get_current_active_user

router = APIRouter(prefix="/api/essays", tags=["essays"])

class EssayCreate(BaseModel):
    title: str
    content: str
    task_type: str = "general"

class EssayResponse(BaseModel):
    id: int
    title: str
    content: str
    task_type: str
    word_count: int
    is_graded: bool
    overall_score: float = None
    submitted_at: str

    class Config:
        from_attributes = True

@router.post("/submit")
async def submit_essay(
    essay_data: EssayCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit an essay for grading"""
    word_count = len(essay_data.content.split())
    
    new_essay = Essay(
        title=essay_data.title,
        content=essay_data.content,
        task_type=essay_data.task_type,
        word_count=word_count,
        author_id=current_user.id
    )
    
    db.add(new_essay)
    await db.commit()
    await db.refresh(new_essay)
    
    return {
        "message": "Essay submitted successfully",
        "essay_id": new_essay.id,
        "word_count": word_count,
        "status": "submitted"
    }

@router.get("/my-essays")
async def get_my_essays(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all essays by the current user"""
    result = await db.execute(
        select(Essay).where(Essay.author_id == current_user.id).order_by(Essay.submitted_at.desc())
    )
    essays = result.scalars().all()
    
    return {
        "essays": [
            {
                "id": essay.id,
                "title": essay.title,
                "task_type": essay.task_type,
                "word_count": essay.word_count,
                "is_graded": essay.is_graded,
                "overall_score": essay.overall_score,
                "submitted_at": essay.submitted_at.isoformat()
            }
            for essay in essays
        ]
    }

@router.get("/{essay_id}")
async def get_essay_details(
    essay_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed essay information"""
    result = await db.execute(
        select(Essay).where(Essay.id == essay_id, Essay.author_id == current_user.id)
    )
    essay = result.scalar_one_or_none()
    
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")
    
    # Get grading if available
    grading_result = None
    if essay.is_graded:
        grading_query = await db.execute(
            select(EssayGrading).where(EssayGrading.essay_id == essay_id)
        )
        grading = grading_query.scalar_one_or_none()
        if grading:
            grading_result = {
                "overall_band": grading.overall_band,
                "task_achievement": grading.task_achievement,
                "coherence_cohesion": grading.coherence_cohesion,
                "lexical_resource": grading.lexical_resource,
                "grammar_accuracy": grading.grammar_accuracy,
                "feedback": grading.feedback,
                "ai_model_used": grading.ai_model_used
            }
    
    return {
        "essay": {
            "id": essay.id,
            "title": essay.title,
            "content": essay.content,
            "task_type": essay.task_type,
            "word_count": essay.word_count,
            "submitted_at": essay.submitted_at.isoformat()
        },
        "grading": grading_result
    }
