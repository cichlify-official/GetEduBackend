from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.models import User, Essay, EssayGrading
from app.api.auth.auth import get_current_active_user

# Try to import AI service, fall back to free service if not available
try:
    from app.services.ai_service import OpenAIService
    AI_SERVICE_AVAILABLE = True
except ImportError:
    AI_SERVICE_AVAILABLE = False

try:
    from app.services.free_ai_service import FreeAIService
    FREE_AI_AVAILABLE = True
except ImportError:
    FREE_AI_AVAILABLE = False

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
    
    # Try to grade with available AI service
    grading_result = None
    ai_model_used = "demo"
    
    if FREE_AI_AVAILABLE:
        # Use free AI service
        ai_service = FreeAIService()
        grading_result = ai_service.grade_essay(
            content=essay.content,
            task_type=essay.task_type,
            word_count=essay.word_count
        )
        ai_model_used = "free_ai_v1"
    elif AI_SERVICE_AVAILABLE:
        # Use OpenAI service if available
        ai_service = OpenAIService()
        grading_result = ai_service.grade_essay(
            content=essay.content,
            task_type=essay.task_type,
            word_count=essay.word_count
        )
        ai_model_used = "gpt-4"
    else:
        # Fallback demo grading
        grading_result = {
            "scores": {
                "task_achievement": 6.0,
                "coherence_cohesion": 6.0,
                "lexical_resource": 6.0,
                "grammar_accuracy": 6.0,
                "overall_band": 6.0
            },
            "feedback": {
                "strengths": ["Essay submitted successfully"],
                "improvements": ["Demo grading - install AI services for real analysis"],
                "suggestions": ["Add OpenAI API key or install AI services"]
            }
        }
        ai_model_used = "demo"
    
    # Save grading results
    essay_grading = EssayGrading(
        essay_id=essay.id,
        task_achievement=grading_result["scores"]["task_achievement"],
        coherence_cohesion=grading_result["scores"]["coherence_cohesion"],
        lexical_resource=grading_result["scores"]["lexical_resource"],
        grammar_accuracy=grading_result["scores"]["grammar_accuracy"],
        overall_band=grading_result["scores"]["overall_band"],
        feedback=grading_result["feedback"],
        ai_model_used=ai_model_used
    )
    
    db.add(essay_grading)
    
    # Update essay
    essay.is_graded = True
    essay.overall_score = grading_result["scores"]["overall_band"]
    
    await db.commit()
    
    return {
        "message": "Essay graded successfully",
        "essay_id": essay.id,
        "overall_band": grading_result["scores"]["overall_band"],
        "cost": grading_result.get("cost", 0.0),
        "analysis_type": grading_result.get("analysis_type", "demo"),
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
        "cost_saved": len(graded_essays) * 0.10
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
    
    # Use available AI service or fallback
    if FREE_AI_AVAILABLE:
        ai_service = FreeAIService()
        grading_result = ai_service.grade_essay(
            content=content,
            task_type=task_type,
            word_count=len(content.split())
        )
    else:
        # Simple fallback grading
        word_count = len(content.split())
        score = min(9.0, max(4.0, 5.0 + (word_count / 50)))  # Simple scoring
        
        grading_result = {
            "scores": {
                "task_achievement": score,
                "coherence_cohesion": score,
                "lexical_resource": score - 0.5,
                "grammar_accuracy": score,
                "overall_band": round(score, 1)
            },
            "feedback": {
                "strengths": ["Text submitted for analysis"],
                "improvements": ["Install AI services for detailed feedback"],
                "suggestions": ["Add more content for better analysis"]
            },
            "analysis_type": "demo",
            "cost": 0.0
        }
    
    return {
        "message": "Demo grading completed",
        "analysis_type": grading_result.get("analysis_type", "demo"),
        "cost": grading_result.get("cost", 0.0),
        "grading": grading_result
    }