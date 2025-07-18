from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Dict, Any

from app.database import get_db
from app.models.models import User, Essay, EssayGrading
from app.api.auth.auth import get_current_active_user
from app.services.ai_service import EnhancedFreeAIService

router = APIRouter(prefix="/api/ai", tags=["AI Grading"])

class GradingRequest(BaseModel):
    essay_id: int

class SpeakingEvaluationRequest(BaseModel):
    transcription: str
    speaking_duration: float = 0.0

class QuickEvaluationRequest(BaseModel):
    content: str
    work_type: str = "essay"  # essay or speaking
    task_type: str = "general"

@router.post("/evaluate-essay")
async def evaluate_essay_comprehensive(
    grading_request: GradingRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Comprehensive essay evaluation with strengths, weaknesses, and improvement course"""
    
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
    
    # Evaluate with enhanced AI service
    ai_service = EnhancedFreeAIService()
    evaluation_result = ai_service.evaluate_work(
        content=essay.content,
        work_type="essay",
        task_type=essay.task_type,
        word_count=essay.word_count
    )
    
    # Save grading results
    essay_grading = EssayGrading(
        essay_id=essay.id,
        task_achievement=evaluation_result["scores"]["task_achievement"],
        coherence_cohesion=evaluation_result["scores"]["coherence_cohesion"],
        lexical_resource=evaluation_result["scores"]["lexical_resource"],
        grammar_accuracy=evaluation_result["scores"]["grammar_accuracy"],
        overall_band=evaluation_result["scores"]["overall_band"],
        feedback=evaluation_result["evaluation"],
        ai_model_used="enhanced_free_ai_v2"
    )
    
    db.add(essay_grading)
    
    # Update essay
    essay.is_graded = True
    essay.overall_score = evaluation_result["scores"]["overall_band"]
    
    await db.commit()
    
    return {
        "message": "Essay evaluated successfully",
        "essay_id": essay.id,
        "overall_band": evaluation_result["scores"]["overall_band"],
        "cost": 0.0,
        "evaluation": evaluation_result["evaluation"],
        "improvement_course": evaluation_result["improvement_course"],
        "scores": evaluation_result["scores"]
    }

@router.post("/evaluate-speaking")
async def evaluate_speaking_comprehensive(
    speaking_request: SpeakingEvaluationRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Comprehensive speaking evaluation with improvement course"""
    
    if not speaking_request.transcription.strip():
        raise HTTPException(status_code=400, detail="Transcription cannot be empty")
    
    # Evaluate with enhanced AI service
    ai_service = EnhancedFreeAIService()
    evaluation_result = ai_service.evaluate_work(
        content=speaking_request.transcription,
        work_type="speaking"
    )
    
    return {
        "message": "Speaking evaluated successfully",
        "user_id": current_user.id,
        "overall_band": evaluation_result["scores"]["overall_band"],
        "cost": 0.0,
        "evaluation": evaluation_result["evaluation"],
        "improvement_course": evaluation_result["improvement_course"],
        "scores": evaluation_result["scores"],
        "analysis_type": "speaking_comprehensive"
    }

@router.post("/quick-evaluate")
async def quick_evaluate(
    evaluation_request: QuickEvaluationRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Quick evaluation without saving to database - for instant feedback"""
    
    if not evaluation_request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    # Evaluate with enhanced AI service
    ai_service = EnhancedFreeAIService()
    evaluation_result = ai_service.evaluate_work(
        content=evaluation_request.content,
        work_type=evaluation_request.work_type,
        task_type=evaluation_request.task_type,
        word_count=len(evaluation_request.content.split())
    )
    
    return {
        "message": f"{evaluation_request.work_type.title()} evaluation completed",
        "user_id": current_user.id,
        "overall_band": evaluation_result["scores"]["overall_band"],
        "cost": 0.0,
        "evaluation": evaluation_result["evaluation"],
        "improvement_course": evaluation_result["improvement_course"],
        "scores": evaluation_result["scores"],
        "analysis_type": "quick_evaluation"
    }

@router.get("/my-progress")
async def get_my_learning_progress(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get user's learning progress and improvement over time"""
    
    # Get user's graded essays
    result = await db.execute(
        select(Essay, EssayGrading)
        .join(EssayGrading, Essay.id == EssayGrading.essay_id)
        .where(Essay.author_id == current_user.id)
        .order_by(Essay.submitted_at.asc())
    )
    
    graded_essays = result.all()
    
    if not graded_essays:
        return {
            "message": "No graded essays found",
            "progress": {
                "total_essays": 0,
                "improvement_trend": "No data yet",
                "recommendation": "Submit your first essay to start tracking progress!"
            }
        }
    
    # Calculate progress metrics
    scores = [grading.overall_band for essay, grading in graded_essays]
    skill_scores = {
        'task_achievement': [grading.task_achievement for essay, grading in graded_essays],
        'coherence_cohesion': [grading.coherence_cohesion for essay, grading in graded_essays],
        'lexical_resource': [grading.lexical_resource for essay, grading in graded_essays],
        'grammar_accuracy': [grading.grammar_accuracy for essay, grading in graded_essays]
    }
    
    # Calculate trends
    first_score = scores[0]
    latest_score = scores[-1]
    improvement = latest_score - first_score
    
    # Identify weakest area
    latest_skills = {
        'task_achievement': skill_scores['task_achievement'][-1],
        'coherence_cohesion': skill_scores['coherence_cohesion'][-1],
        'lexical_resource': skill_scores['lexical_resource'][-1],
        'grammar_accuracy': skill_scores['grammar_accuracy'][-1]
    }
    
    weakest_skill = min(latest_skills.items(), key=lambda x: x[1])
    
    # Generate personalized recommendations
    ai_service = EnhancedFreeAIService()
    recommendations = ai_service._get_daily_activities(weakest_skill[0])
    
    return {
        "progress": {
            "total_essays": len(graded_essays),
            "current_level": latest_score,
            "starting_level": first_score,
            "improvement": round(improvement, 1),
            "improvement_trend": "Improving" if improvement > 0 else "Stable" if improvement == 0 else "Needs attention",
            "skill_breakdown": {
                skill: {
                    "current": values[-1],
                    "trend": round(values[-1] - values[0], 1) if len(values) > 1 else 0
                }
                for skill, values in skill_scores.items()
            },
            "weakest_area": weakest_skill[0].replace('_', ' ').title(),
            "weakest_score": weakest_skill[1]
        },
        "recommendations": {
            "focus_area": weakest_skill[0].replace('_', ' ').title(),
            "daily_activities": recommendations,
            "next_goal": f"Improve {weakest_skill[0].replace('_', ' ')} to {weakest_skill[1] + 0.5}",
            "estimated_time": "2-4 weeks with consistent practice"
        },
        "recent_essays": [
            {
                "title": essay.title,
                "score": grading.overall_band,
                "date": essay.submitted_at.strftime("%Y-%m-%d"),
                "strengths": grading.feedback.get("strengths", [])[:2] if isinstance(grading.feedback, dict) else ["Good effort"]
            }
            for essay, grading in graded_essays[-3:]  # Last 3 essays
        ]
    }

@router.get("/improvement-course/{skill}")
async def get_skill_improvement_course(
    skill: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed improvement course for a specific skill"""
    
    valid_skills = ['task_achievement', 'coherence_cohesion', 'lexical_resource', 'grammar_accuracy']
    
    if skill not in valid_skills:
        raise HTTPException(status_code=400, detail=f"Invalid skill. Choose from: {valid_skills}")
    
    # Get user's latest performance in this skill
    result = await db.execute(
        select(EssayGrading)
        .join(Essay, EssayGrading.essay_id == Essay.id)
        .where(Essay.author_id == current_user.id)
        .order_by(Essay.submitted_at.desc())
        .limit(1)
    )
    
    latest_grading = result.scalar_one_or_none()
    
    if not latest_grading:
        # Generate generic course
        current_score = 5.0
    else:
        current_score = getattr(latest_grading, skill)
    
    # Generate detailed course
    ai_service = EnhancedFreeAIService()
    
    # Create mock scores for course generation
    mock_scores = {
        'task_achievement': current_score if skill == 'task_achievement' else 6.0,
        'coherence_cohesion': current_score if skill == 'coherence_cohesion' else 6.0,
        'lexical_resource': current_score if skill == 'lexical_resource' else 6.0,
        'grammar_accuracy': current_score if skill == 'grammar_accuracy' else 6.0,
        'overall_band': current_score
    }
    
    course = ai_service._generate_improvement_course(mock_scores, [f"Needs improvement in {skill}"])
    
    return {
        "skill": skill.replace('_', ' ').title(),
        "current_score": current_score,
        "course": course,
        "skill_specific_tips": ai_service.improvement_strategies.get(skill, {}).get('tips', []),
        "practice_exercises": ai_service.improvement_strategies.get(skill, {}).get('exercises', [])
    }

@router.post("/simulate-improvement")
async def simulate_improvement_timeline(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Simulate improvement timeline based on user's current performance"""
    
    # Get user's latest scores
    result = await db.execute(
        select(EssayGrading)
        .join(Essay, EssayGrading.essay_id == Essay.id)
        .where(Essay.author_id == current_user.id)
        .order_by(Essay.submitted_at.desc())
        .limit(1)
    )
    
    latest_grading = result.scalar_one_or_none()
    
    if not latest_grading:
        return {
            "message": "No grading history found",
            "recommendation": "Submit and grade your first essay to get personalized improvement timeline"
        }
    
    current_scores = {
        'task_achievement': latest_grading.task_achievement,
        'coherence_cohesion': latest_grading.coherence_cohesion,
        'lexical_resource': latest_grading.lexical_resource,
        'grammar_accuracy': latest_grading.grammar_accuracy,
        'overall_band': latest_grading.overall_band
    }
    
    # Simulate improvement over time
    improvement_timeline = []
    
    for month in range(1, 7):  # 6 months simulation
        projected_scores = {}
        
        for skill, score in current_scores.items():
            if skill == 'overall_band':
                continue
                
            # Simulate improvement (0.1-0.3 per month based on current level)
            improvement_rate = 0.3 if score < 6.0 else 0.2 if score < 7.0 else 0.1
            projected_score = min(score + (improvement_rate * month), 9.0)
            projected_scores[skill] = round(projected_score, 1)
        
        # Calculate overall band
        overall = sum(projected_scores.values()) / len(projected_scores)
        projected_scores['overall_band'] = round(overall, 1)
        
        improvement_timeline.append({
            "month": month,
            "projected_scores": projected_scores,
            "milestone": f"Month {month}: Focus on {'grammar' if month <= 2 else 'vocabulary' if month <= 4 else 'advanced skills'}"
        })
    
    return {
        "current_scores": current_scores,
        "improvement_timeline": improvement_timeline,
        "recommendations": {
            "study_hours_per_week": 10 if current_scores['overall_band'] < 6.0 else 8 if current_scores['overall_band'] < 7.0 else 6,
            "priority_skills": [
                skill for skill, score in current_scores.items() 
                if score < 6.0 and skill != 'overall_band'
            ],
            "realistic_timeline": "3-6 months to reach next band level with consistent practice"
        }
    }