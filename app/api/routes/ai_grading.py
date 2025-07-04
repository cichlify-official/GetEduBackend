from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.models import User, Essay, EssayGrading
from app.api.auth.auth import get_current_active_user
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
    """Grade an essay using free AI analysis"""
    
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
    
    # Grade with free AI service
    ai_service = FreeAIService()
    grading_result = ai_service.grade_essay(
        content=essay.content,
        task_type=essay.task_type,
        word_count=essay.word_count
    )
    
    # Save grading results
    essay_grading = EssayGrading(
        essay_id=essay.id,
        task_achievement=grading_result["scores"]["task_achievement"],
        coherence_cohesion=grading_result["scores"]["coherence_cohesion"],
        lexical_resource=grading_result["scores"]["lexical_resource"],
        grammar_accuracy=grading_result["scores"]["grammar_accuracy"],
        overall_band=grading_result["scores"]["overall_band"],
        feedback=grading_result["feedback"],
        ai_model_used="free_ai_v1"
    )
    
    db.add(essay_grading)
    
    # Update essay
    essay.is_graded = True
    essay.overall_score = grading_result["scores"]["overall_band"]
    
    await db.commit()
    
    return {
        "message": "Essay graded successfully with Free AI",
        "essay_id": essay.id,
        "overall_band": grading_result["scores"]["overall_band"],
        "cost": 0.0,  # Completely free!
        "analysis_type": "rule_based",
        "grading": grading_result
    }

@router.get("/grading-history")
async def get_grading_history(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's AI grading history"""
    
    result = await db.execute(
        select(Essay, EssayGrading)
        .join(EssayGrading, Essay.id == EssayGrading.essay_id)
        .where(Essay.author_id == current_user.id)
        .order_by(Essay.submitted_at.desc())
    )
    
    graded_essays = result.all()
    
    return {
        "graded_essays": [
            {
                "essay_id": essay.id,
                "title": essay.title,
                "task_type": essay.task_type,
                "overall_band": grading.overall_band,
                "submitted_at": essay.submitted_at.isoformat(),
                "ai_model": grading.ai_model_used
            }
            for essay, grading in graded_essays
        ],
        "total_graded": len(graded_essays),
        "cost_saved": len(graded_essays) * 0.10  # Show how much money saved vs paid services
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
    
    ai_service = FreeAIService()
    grading_result = ai_service.grade_essay(
        content=content,
        task_type=task_type,
        word_count=len(content.split())
    )
    
    return {
        "message": "Demo grading completed",
        "analysis_type": "free_ai",
        "cost": 0.0,
        "grading": grading_result
    }
