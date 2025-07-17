from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime

from app.database import get_db
from app.models.models import User, Essay, EssayGrading
from app.api.auth.auth import get_current_active_user
from app.services.enhanced_ai_service import EnhancedAIService
from app.services.free_ai_service import FreeAIService

router = APIRouter(prefix="/api/ai", tags=["AI Grading"])

class GradingRequest(BaseModel):
    essay_id: int

@router.post("/grade-essay")
async def grade_essay_endpoint(
    grading_request: GradingRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Grade an essay using AI analysis"""
    
    # Get the essay
    result = await db.execute(
        select(Essay).where(
            Essay.id == grading_request.essay_id, 
            Essay.author_id == current_user.id
        )
    )
    essay = result.scalar_one_or_none()
    
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")
    
    if essay.is_graded:
        raise HTTPException(status_code=400, detail="Essay already graded")
    
    # Try enhanced AI service first, fallback to free service
    try:
        ai_service = EnhancedAIService()
        grading_result = await ai_service.grade_essay(
            content=essay.content,
            task_type=essay.task_type,
            word_count=essay.word_count
        )
        ai_model_used = "gpt-4"
    except Exception as e:
        print(f"Enhanced AI service failed: {e}")
        # Fallback to free service
        ai_service = FreeAIService()
        grading_result = ai_service.grade_essay(
            content=essay.content,
            task_type=essay.task_type,
            word_count=essay.word_count
        )
        ai_model_used = "free_ai_v1"
    
    # Save grading results
    essay_grading = EssayGrading(
        essay_id=essay.id,
        task_achievement=grading_result["scores"]["task_achievement"],
        coherence_cohesion=grading_result["scores"]["coherence_cohesion"],
        lexical_resource=grading_result["scores"]["lexical_resource"],
        grammar_accuracy=grading_result["scores"]["grammar_accuracy"],
        overall_band=grading_result["scores"]["overall_band"],
        feedback=grading_result["feedback"],
        lesson_recommendations=grading_result.get("lesson_recommendations", []),
        ai_model_used=ai_model_used
    )
    
    db.add(essay_grading)
    
    # Update essay
    essay.is_graded = True
    essay.overall_score = grading_result["scores"]["overall_band"]
    essay.graded_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "message": "Essay graded successfully",
        "essay_id": essay.id,
        "overall_band": grading_result["scores"]["overall_band"],
        "cost": grading_result.get("cost", 0.0),
        "analysis_type": grading_result.get("analysis_type", "ai_powered"),
        "grading": grading_result
    }

@router.post("/demo-grade")
async def demo_grade_text(
    text_data: dict,
    current_user: User = Depends(get_current_active_user)
):
    """Demo endpoint to grade any text without saving to database"""
    
    content = text_data.get("content", "")
    task_type = text_data.get("task_type", "general")
    
    if not content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    # Try enhanced AI service first, fallback to free service
    try:
        ai_service = EnhancedAIService()
        grading_result = await ai_service.grade_essay(
            content=content,
            task_type=task_type,
            word_count=len(content.split())
        )
    except Exception as e:
        print(f"Enhanced AI service failed: {e}")
        # Fallback to free service
        ai_service = FreeAIService()
        grading_result = ai_service.grade_essay(
            content=content,
            task_type=task_type,
            word_count=len(content.split())
        )
    
    return {
        "message": "Demo grading completed",
        "analysis_type": grading_result.get("analysis_type", "ai_powered"),
        "cost": grading_result.get("cost", 0.0),
        "grading": grading_result
    }