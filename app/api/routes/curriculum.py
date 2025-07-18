from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, validator
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json

from app.database import get_db
from app.models.models import User, StudentProfile, Curriculum, Essay, EssayGrading, SpeakingAnalysis, Language, UserRole
from app.api.auth.auth import get_current_active_user
from app.services.enhanced_ai_services import ai_service_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/curriculum", tags=["Curriculum Generation"])

class CurriculumRequest(BaseModel):
    target_language: str = "english"
    target_level: str  # A1, A2, B1, B2, C1, C2
    target_band: Optional[float] = None  # IELTS target
    duration_weeks: int = 12
    weekly_hours: int = 10
    focus_areas: List[str] = ["grammar", "vocabulary", "speaking", "writing"]
    learning_style: Optional[str] = "balanced"  # visual, auditory, kinesthetic, balanced
    specific_goals: Optional[List[str]] = []

class CurriculumUpdateRequest(BaseModel):
    curriculum_id: int
    progress_percentage: float
    completed_modules: List[str]
    difficulty_feedback: Optional[str] = None  # "too_easy", "appropriate", "too_hard"

class CurriculumService:
    """Service for generating and managing personalized curriculums"""
    
    @staticmethod
    async def analyze_student_profile(db: AsyncSession, student_id: int) -> Dict[str, Any]:
        """Analyze student's current performance and identify weak areas"""
        
        # Get student profile
        profile_result = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == student_id)
        )
        profile = profile_result.scalar_one_or_none()
        
        if not profile:
            # Create basic profile if none exists
            return {
                "current_level": "A1",
                "overall_band": 4.0,
                "weak_areas": ["grammar", "vocabulary", "speaking", "writing"],
                "strong_areas": [],
                "total_assessments": 0,
                "improvement_rate": 0.0
            }
        
        # Analyze recent performance
        recent_essays = await db.execute(
            select(Essay, EssayGrading).join(EssayGrading).where(
                and_(
                    Essay.author_id == student_id,
                    Essay.submitted_at >= datetime.utcnow() - timedelta(days=30)
                )
            ).order_by(Essay.submitted_at.desc()).limit(10)
        )
        
        recent_speaking = await db.execute(
            select(SpeakingAnalysis).join(
                Essay, SpeakingAnalysis.speaking_task_id == Essay.id
            ).where(
                Essay.author_id == student_id
            ).order_by(Essay.submitted_at.desc()).limit(5)
        )
        
        essays_data = recent_essays.fetchall()
        speaking_data = recent_speaking.scalars().all()
        
        # Calculate skill averages
        skill_scores = {
            "grammar": [],
            "vocabulary": [],
            "speaking": [],
            "writing": [],
            "coherence": []
        }
        
        for essay, grading in essays_data:
            skill_scores["grammar"].append(grading.grammar_accuracy)
            skill_scores["vocabulary"].append(grading.lexical_resource)
            skill_scores["writing"].append(grading.task_achievement)
            skill_scores["coherence"].append(grading.coherence_cohesion)
        
        for speaking in speaking_data:
            skill_scores["speaking"].append(speaking.overall_band)
            skill_scores["grammar"].append(speaking.grammatical_range)
            skill_scores["vocabulary"].append(speaking.lexical_resource)
        
        # Identify weak and strong areas
        avg_scores = {
            skill: sum(scores) / len(scores) if scores else 0.0
            for skill, scores in skill_scores.items()
        }
        
        overall_avg = sum(avg_scores.values()) / len(avg_scores) if avg_scores else 0.0
        weak_areas = [skill for skill, score in avg_scores.items() if score < overall_avg - 0.5]
        strong_areas = [skill for skill, score in avg_scores.items() if score > overall_avg + 0.5]
        
        # Calculate improvement rate
        if len(essays_data) >= 3:
            first_scores = [essays_data[-1][1].overall_band]
            recent_scores = [grading.overall_band for _, grading in essays_data[:3]]
            improvement_rate = (sum(recent_scores) / len(recent_scores)) - (sum(first_scores) / len(first_scores))
        else:
            improvement_rate = 0.0
        
        return {
            "current_level": profile.user.current_level or "A2",
            "overall_band": profile.overall_band,
            "weak_areas": weak_areas or ["grammar", "vocabulary"],
            "strong_areas": strong_areas,
            "total_assessments": len(essays_data) + len(speaking_data),
            "improvement_rate": round(improvement_rate, 2),
            "skill_breakdown": {k: round(v, 2) for k, v in avg_scores.items()},
            "recent_performance": {
                "essays_completed": len(essays_data),
                "speaking_sessions": len(speaking_data),
                "avg_essay_score": round(sum(grading.overall_band for _, grading in essays_data) / len(essays_data), 2) if essays_data else 0.0,
                "avg_speaking_score": round(sum(s.overall_band for s in speaking_data) / len(speaking_data), 2) if speaking_data else 0.0
            }
        }
    
    @staticmethod
    async def generate_personalized_curriculum(
        db: AsyncSession,
        student_id: int,
        request: CurriculumRequest
    ) -> Curriculum:
        """Generate AI-powered personalized curriculum"""
        
        # Analyze student profile
        student_analysis = await CurriculumService.analyze_student_profile(db, student_id)
        
        # Prepare AI prompt data
        ai_input = {
            "student_profile": student_analysis,
            "target_language": request.target_language,
            "target_level": request.target_level,
            "target_band": request.target_band,
            "duration_weeks": request.duration_weeks,
            "weekly_hours": request.weekly_hours,
            "focus_areas": request.focus_areas,
            "learning_style": request.learning_style,
            "specific_goals": request.specific_goals
        }
        
        try:
            # Generate curriculum using AI
            ai_response = await ai_service_manager.generate_curriculum(ai_input)
            
            # Create curriculum record
            curriculum = Curriculum(
                name=ai_response["curriculum_overview"]["title"],
                description=f"Personalized curriculum for {request.target_language} - {request.target_level}",
                target_language=Language(request.target_language.upper()),
                target_level=request.target_level,
                target_band=request.target_band,
                duration_weeks=request.duration_weeks,
                curriculum_data=ai_response,
                focus_areas=request.focus_areas,
                difficulty_progression=CurriculumService._generate_difficulty_progression(
                    request.duration_weeks, student_analysis["overall_band"], request.target_band
                ),
                created_by_ai=True,
                ai_model_used=ai_response.get("model", "ai_service"),
                generation_prompt=json.dumps(ai_input)
            )
            
            db.add(curriculum)
            await db.commit()
            await db.refresh(curriculum)
            
            # Update student profile to use this curriculum
            profile_result = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == student_id)
            )
            profile = profile_result.scalar_one_or_none()
            
            if profile:
                profile.current_curriculum_id = curriculum.id
                profile.curriculum_progress = 0.0
                profile.focus_areas = request.focus_areas
                if request.target_band:
                    profile.target_band = request.target_band
                await db.commit()
            
            return curriculum
            
        except Exception as e:
            logger.error(f"Curriculum generation failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate curriculum: {str(e)}"
            )
    
    @staticmethod
    def _generate_difficulty_progression(weeks: int, current_band: float, target_band: Optional[float]) -> List[Dict[str, Any]]:
        """Generate week-by-week difficulty progression"""
        
        if not target_band:
            target_band = current_band + 1.0
        
        improvement_per_week = (target_band - current_band) / weeks
        progression = []
        
        for week in range(1, weeks + 1):
            week_target = current_band + (improvement_per_week * week)
            
            # Determine difficulty level
            if week <= weeks * 0.3:  # First 30% - Foundation
                difficulty = "beginner"
                focus = "foundation_building"
            elif week <= weeks * 0.7:  # Next 40% - Development
                difficulty = "intermediate"
                focus = "skill_development"
            else:  # Last 30% - Advanced
                difficulty = "advanced"
                focus = "test_preparation"
            
            progression.append({
                "week": week,
                "target_band": round(week_target, 1),
                "difficulty_level": difficulty,
                "focus_area": focus,
                "expected_improvement": round(improvement_per_week, 2)
            })
        
        return progression
    
    @staticmethod
    async def update_curriculum_progress(
        db: AsyncSession,
        student_id: int,
        update_request: CurriculumUpdateRequest
    ) -> Dict[str, Any]:
        """Update student's curriculum progress"""
        
        # Get curriculum
        curriculum_result = await db.execute(
            select(Curriculum).where(Curriculum.id == update_request.curriculum_id)
        )
        curriculum = curriculum_result.scalar_one_or_none()
        
        if not curriculum:
            raise HTTPException(status_code=404, detail="Curriculum not found")
        
        # Get student profile
        profile_result = await db.execute(
            select(StudentProfile).where(StudentProfile.user_id == student_id)
        )
        profile = profile_result.scalar_one_or_none()
        
        if not profile or profile.current_curriculum_id != curriculum.id:
            raise HTTPException(
                status_code=403,
                detail="This curriculum is not assigned to the current student"
            )
        
        # Update progress
        profile.curriculum_progress = min(update_request.progress_percentage, 100.0)
        profile.updated_at = datetime.utcnow()
        
        # Check if curriculum needs adjustment based on feedback
        needs_adjustment = False
        adjustment_reason = ""
        
        if update_request.difficulty_feedback == "too_easy":
            needs_adjustment = True
            adjustment_reason = "Student finds curriculum too easy - suggesting acceleration"
        elif update_request.difficulty_feedback == "too_hard":
            needs_adjustment = True
            adjustment_reason = "Student finds curriculum too difficult - suggesting more support"
        
        await db.commit()
        
        # Calculate estimated completion date
        weeks_completed = (update_request.progress_percentage / 100) * curriculum.duration_weeks
        weeks_remaining = curriculum.duration_weeks - weeks_completed
        estimated_completion = datetime.utcnow() + timedelta(weeks=weeks_remaining)
        
        return {
            "progress_updated": True,
            "current_progress": update_request.progress_percentage,
            "weeks_completed": round(weeks_completed, 1),
            "weeks_remaining": round(weeks_remaining, 1),
            "estimated_completion": estimated_completion.isoformat(),
            "needs_adjustment": needs_adjustment,
            "adjustment_reason": adjustment_reason,
            "completed_modules": update_request.completed_modules
        }

# API Endpoints

@router.post("/generate")
async def generate_curriculum(
    curriculum_request: CurriculumRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a personalized curriculum for the current student"""
    
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=403,
            detail="Only students can generate personal curriculums"
        )
    
    try:
        curriculum = await CurriculumService.generate_personalized_curriculum(
            db, current_user.id, curriculum_request
        )
        
        return {
            "message": "Curriculum generated successfully",
            "curriculum_id": curriculum.id,
            "curriculum_name": curriculum.name,
            "duration_weeks": curriculum.duration_weeks,
            "focus_areas": curriculum.focus_areas,
            "target_level": curriculum.target_level,
            "ai_generated": curriculum.created_by_ai,
            "curriculum_overview": curriculum.curriculum_data.get("curriculum_overview", {})
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Curriculum generation error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate curriculum. Please try again."
        )

@router.get("/my-curriculum")
async def get_my_curriculum(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current student's curriculum"""
    
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=403,
            detail="Only students can access personal curriculums"
        )
    
    # Get student profile with curriculum
    profile_result = await db.execute(
        select(StudentProfile).options(
            selectinload(StudentProfile.current_curriculum)
        ).where(StudentProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    if not profile or not profile.current_curriculum:
        return {
            "has_curriculum": False,
            "message": "No curriculum assigned. Generate one to get started!"
        }
    
    curriculum = profile.current_curriculum
    current_week = int((profile.curriculum_progress / 100) * curriculum.duration_weeks) + 1
    
    # Get current week's plan
    weekly_plan = curriculum.curriculum_data.get("weekly_plan", [])
    current_week_plan = None
    if current_week <= len(weekly_plan):
        current_week_plan = weekly_plan[current_week - 1]
    
    # Calculate progress metrics
    total_weeks = curriculum.duration_weeks
    completed_weeks = int((profile.curriculum_progress / 100) * total_weeks)
    remaining_weeks = total_weeks - completed_weeks
    
    return {
        "has_curriculum": True,
        "curriculum": {
            "id": curriculum.id,
            "name": curriculum.name,
            "description": curriculum.description,
            "target_level": curriculum.target_level,
            "target_band": curriculum.target_band,
            "duration_weeks": curriculum.duration_weeks,
            "focus_areas": curriculum.focus_areas,
            "created_at": curriculum.created_at.isoformat()
        },
        "progress": {
            "percentage": profile.curriculum_progress,
            "current_week": current_week,
            "completed_weeks": completed_weeks,
            "remaining_weeks": remaining_weeks,
            "estimated_completion": (
                datetime.utcnow() + timedelta(weeks=remaining_weeks)
            ).isoformat()
        },
        "current_week_plan": current_week_plan,
        "difficulty_progression": curriculum.difficulty_progression,
        "resources": curriculum.curriculum_data.get("resources", {}),
        "milestones": curriculum.curriculum_data.get("milestone_assessments", [])
    }

@router.post("/progress/update")
async def update_progress(
    update_request: CurriculumUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update curriculum progress"""
    
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=403,
            detail="Only students can update their curriculum progress"
        )
    
    try:
        result = await CurriculumService.update_curriculum_progress(
            db, current_user.id, update_request
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Progress update error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update progress"
        )

@router.get("/templates")
async def get_curriculum_templates(
    language: Optional[str] = None,
    level: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available curriculum templates"""
    
    query = select(Curriculum).where(
        and_(
            Curriculum.is_template == True,
            Curriculum.is_active == True
        )
    )
    
    if language:
        query = query.where(Curriculum.target_language == Language(language.upper()))
    
    if level:
        query = query.where(Curriculum.target_level == level)
    
    result = await db.execute(query)
    templates = result.scalars().all()
    
    return {
        "templates": [
            {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "target_language": template.target_language.value.lower(),
                "target_level": template.target_level,
                "duration_weeks": template.duration_weeks,
                "focus_areas": template.focus_areas,
                "preview": template.curriculum_data.get("curriculum_overview", {})
            }
            for template in templates
        ],
        "total_templates": len(templates),
        "filters": {
            "language": language,
            "level": level
        }
    }

@router.post("/templates/{template_id}/apply")
async def apply_curriculum_template(
    template_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Apply a curriculum template to current student"""
    
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=403,
            detail="Only students can apply curriculum templates"
        )
    
    # Get template
    template_result = await db.execute(
        select(Curriculum).where(
            and_(
                Curriculum.id == template_id,
                Curriculum.is_template == True,
                Curriculum.is_active == True
            )
        )
    )
    template = template_result.scalar_one_or_none()
    
    if not template:
        raise HTTPException(status_code=404, detail="Curriculum template not found")
    
    # Analyze student profile for customization
    student_analysis = await CurriculumService.analyze_student_profile(db, current_user.id)
    
    # Create personalized version of template
    personalized_curriculum = Curriculum(
        name=f"{template.name} - Personalized for {current_user.full_name}",
        description=f"Personalized version of {template.name}",
        target_language=template.target_language,
        target_level=template.target_level,
        target_band=template.target_band,
        duration_weeks=template.duration_weeks,
        curriculum_data=template.curriculum_data.copy(),
        focus_areas=student_analysis["weak_areas"] + template.focus_areas,
        difficulty_progression=CurriculumService._generate_difficulty_progression(
            template.duration_weeks,
            student_analysis["overall_band"],
            template.target_band
        ),
        created_by_ai=False,
        is_template=False
    )
    
    db.add(personalized_curriculum)
    await db.commit()
    await db.refresh(personalized_curriculum)
    
    # Update student profile
    profile_result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    
    if profile:
        profile.current_curriculum_id = personalized_curriculum.id
        profile.curriculum_progress = 0.0
        profile.focus_areas = personalized_curriculum.focus_areas
        await db.commit()
    
    return {
        "message": "Curriculum template applied successfully",
        "curriculum_id": personalized_curriculum.id,
        "curriculum_name": personalized_curriculum.name,
        "customizations_applied": {
            "focus_areas_added": student_analysis["weak_areas"],
            "difficulty_adjusted": True,
            "duration_weeks": personalized_curriculum.duration_weeks
        }
    }

@router.get("/analytics")
async def get_curriculum_analytics(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get curriculum effectiveness analytics (admin only)"""
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    # Curriculum usage statistics
    curriculum_stats = await db.execute(
        select(
            Curriculum.id,
            Curriculum.name,
            Curriculum.target_level,
            func.count(StudentProfile.id).label('students_enrolled'),
            func.avg(StudentProfile.curriculum_progress).label('avg_progress'),
            func.count(
                func.case(
                    (StudentProfile.curriculum_progress >= 80, 1),
                    else_=None
                )
            ).label('near_completion')
        ).outerjoin(StudentProfile).group_by(
            Curriculum.id, Curriculum.name, Curriculum.target_level
        ).order_by(func.count(StudentProfile.id).desc())
    )
    
    curriculum_data = [
        {
            "curriculum_id": row.id,
            "curriculum_name": row.name,
            "target_level": row.target_level,
            "students_enrolled": row.students_enrolled,
            "avg_progress": round(row.avg_progress or 0, 2),
            "completion_rate": round(
                (row.near_completion / max(row.students_enrolled, 1)) * 100, 2
            ),
            "effectiveness_score": round(
                ((row.avg_progress or 0) / 100) * 
                ((row.near_completion / max(row.students_enrolled, 1)) * 100) / 100 * 10, 2
            )
        }
        for row in curriculum_stats.fetchall()
    ]
    
    # Overall metrics
    total_curriculums = await db.execute(
        select(func.count(Curriculum.id)).where(Curriculum.is_active == True)
    )
    
    total_students_with_curriculum = await db.execute(
        select(func.count(StudentProfile.id)).where(
            StudentProfile.current_curriculum_id.isnot(None)
        )
    )
    
    avg_completion_time = await db.execute(
        select(
            func.avg(
                func.extract('epoch', 
                    func.now() - StudentProfile.updated_at
                ) / (7 * 24 * 3600)  # Convert to weeks
            )
        ).where(StudentProfile.curriculum_progress >= 100)
    )
    
    return {
        "curriculum_analytics": {
            "total_active_curriculums": total_curriculums.scalar() or 0,
            "students_with_curriculum": total_students_with_curriculum.scalar() or 0,
            "avg_completion_time_weeks": round(avg_completion_time.scalar() or 0, 1),
            "curriculum_performance": curriculum_data,
            "top_performing_curriculums": sorted(
                curriculum_data, 
                key=lambda x: x["effectiveness_score"], 
                reverse=True
            )[:5]
        },
        "generated_at": datetime.utcnow().isoformat()
    }

@router.delete("/{curriculum_id}")
async def delete_curriculum(
    curriculum_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a curriculum (admin only)"""
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    # Get curriculum
    curriculum_result = await db.execute(
        select(Curriculum).where(Curriculum.id == curriculum_id)
    )
    curriculum = curriculum_result.scalar_one_or_none()
    
    if not curriculum:
        raise HTTPException(status_code=404, detail="Curriculum not found")
    
    # Check if curriculum is in use
    students_using = await db.execute(
        select(func.count(StudentProfile.id)).where(
            StudentProfile.current_curriculum_id == curriculum_id
        )
    )
    
    students_count = students_using.scalar() or 0
    
    if students_count > 0:
        # Soft delete - deactivate instead of deleting
        curriculum.is_active = False
        curriculum.updated_at = datetime.utcnow()
        await db.commit()
        
        return {
            "message": f"Curriculum deactivated (was in use by {students_count} students)",
            "curriculum_id": curriculum_id,
            "action": "deactivated",
            "affected_students": students_count
        }
    else:
        # Hard delete if no students are using it
        await db.delete(curriculum)
        await db.commit()
        
        return {
            "message": "Curriculum deleted successfully",
            "curriculum_id": curriculum_id,
            "action": "deleted"
        }