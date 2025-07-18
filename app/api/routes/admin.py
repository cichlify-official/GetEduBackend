from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json

from app.database import get_db
from app.models.models import (
    User, Class, Essay, EssayGrading, SpeakingTask, SpeakingAnalysis,
    StudentProfile, AIRequest, Room, UserRole, ClassStatus, Language
)
from app.api.auth.auth import get_current_active_user

router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])

# Permission check
async def verify_admin_access(current_user: User = Depends(get_current_active_user)):
    """Verify user has admin access"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    return current_user

class PlatformStats(BaseModel):
    total_users: int
    total_students: int
    total_teachers: int
    total_classes: int
    completed_classes: int
    scheduled_classes: int
    total_essays: int
    graded_essays: int
    total_speaking_tasks: int
    analyzed_speaking_tasks: int
    ai_requests_today: int
    total_ai_cost: float
    avg_student_score: float

class UserAnalytics(BaseModel):
    user_id: int
    username: str
    full_name: str
    role: str
    total_classes: int
    completed_classes: int
    avg_score: Optional[float]
    last_activity: Optional[datetime]
    registration_date: datetime

class TeacherPerformance(BaseModel):
    teacher_id: int
    teacher_name: str
    total_classes: int
    completed_classes: int
    avg_student_rating: float
    specializations: List[str]
    student_improvement_rate: float
    revenue_generated: float

class AdminAnalyticsService:
    """Service for generating admin analytics and reports"""
    
    @staticmethod
    async def get_platform_statistics(db: AsyncSession) -> PlatformStats:
        """Get comprehensive platform statistics"""
        
        # User counts
        user_stats = await db.execute(
            select(
                func.count(User.id).label('total'),
                func.sum(func.case((User.role == UserRole.STUDENT, 1), else_=0)).label('students'),
                func.sum(func.case((User.role == UserRole.TEACHER, 1), else_=0)).label('teachers')
            ).where(User.is_active == True)
        )
        user_counts = user_stats.first()
        
        # Class statistics
        class_stats = await db.execute(
            select(
                func.count(Class.id).label('total'),
                func.sum(func.case((Class.status == ClassStatus.COMPLETED, 1), else_=0)).label('completed'),
                func.sum(func.case((Class.status == ClassStatus.SCHEDULED, 1), else_=0)).label('scheduled')
            )
        )
        class_counts = class_stats.first()
        
        # Essay statistics
        essay_stats = await db.execute(
            select(
                func.count(Essay.id).label('total'),
                func.sum(func.case((Essay.is_graded == True, 1), else_=0)).label('graded')
            )
        )
        essay_counts = essay_stats.first()
        
        # Speaking task statistics
        speaking_stats = await db.execute(
            select(
                func.count(SpeakingTask.id).label('total'),
                func.sum(func.case((SpeakingTask.is_analyzed == True, 1), else_=0)).label('analyzed')
            )
        )
        speaking_counts = speaking_stats.first()
        
        # AI usage today
        today = datetime.utcnow().date()
        ai_today = await db.execute(
            select(func.count(AIRequest.id)).where(
                func.date(AIRequest.created_at) == today
            )
        )
        ai_requests_today = ai_today.scalar() or 0
        
        # Total AI cost
        ai_cost = await db.execute(
            select(func.sum(AIRequest.cost_usd)).where(
                AIRequest.status == "completed"
            )
        )
        total_ai_cost = ai_cost.scalar() or 0.0
        
        # Average student score
        avg_score = await db.execute(
            select(func.avg(StudentProfile.overall_band)).where(
                StudentProfile.overall_band > 0
            )
        )
        avg_student_score = avg_score.scalar() or 0.0
        
        return PlatformStats(
            total_users=user_counts.total or 0,
            total_students=user_counts.students or 0,
            total_teachers=user_counts.teachers or 0,
            total_classes=class_counts.total or 0,
            completed_classes=class_counts.completed or 0,
            scheduled_classes=class_counts.scheduled or 0,
            total_essays=essay_counts.total or 0,
            graded_essays=essay_counts.graded or 0,
            total_speaking_tasks=speaking_counts.total or 0,
            analyzed_speaking_tasks=speaking_counts.analyzed or 0,
            ai_requests_today=ai_requests_today,
            total_ai_cost=round(total_ai_cost, 2),
            avg_student_score=round(avg_student_score, 2)
        )
    
    @staticmethod
    async def get_user_analytics(
        db: AsyncSession,
        role_filter: Optional[str] = None,
        limit: int = 50
    ) -> List[UserAnalytics]:
        """Get detailed user analytics"""
        
        query = select(User).options(selectinload(User.student_profile))
        
        if role_filter:
            query = query.where(User.role == UserRole(role_filter))
        
        query = query.where(User.is_active == True).limit(limit)
        
        result = await db.execute(query)
        users = result.scalars().all()
        
        user_analytics = []
        for user in users:
            # Get class count
            class_count = await db.execute(
                select(
                    func.count(Class.id).label('total'),
                    func.sum(func.case((Class.status == ClassStatus.COMPLETED, 1), else_=0)).label('completed')
                ).where(
                    or_(Class.student_id == user.id, Class.teacher_id == user.id)
                )
            )
            class_stats = class_count.first()
            
            # Get average score for students
            avg_score = None
            if user.role == UserRole.STUDENT and user.student_profile:
                avg_score = user.student_profile.overall_band
            
            user_analytics.append(UserAnalytics(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
                role=user.role.value,
                total_classes=class_stats.total or 0,
                completed_classes=class_stats.completed or 0,
                avg_score=avg_score,
                last_activity=user.last_login,
                registration_date=user.created_at
            ))
        
        return user_analytics
    
    @staticmethod
    async def get_teacher_performance(db: AsyncSession) -> List[TeacherPerformance]:
        """Get teacher performance analytics"""
        
        teachers_result = await db.execute(
            select(User).where(
                and_(User.role == UserRole.TEACHER, User.is_active == True)
            )
        )
        teachers = teachers_result.scalars().all()
        
        performance_data = []
        for teacher in teachers:
            # Get class statistics
            class_stats = await db.execute(
                select(
                    func.count(Class.id).label('total'),
                    func.sum(func.case((Class.status == ClassStatus.COMPLETED, 1), else_=0)).label('completed'),
                    func.avg(Class.student_feedback_rating).label('avg_rating'),
                    func.sum(Class.cost).label('revenue')
                ).where(Class.teacher_id == teacher.id)
            )
            stats = class_stats.first()
            
            # Calculate student improvement rate
            improvement_rate = await AdminAnalyticsService._calculate_student_improvement(
                db, teacher.id
            )
            
            performance_data.append(TeacherPerformance(
                teacher_id=teacher.id,
                teacher_name=teacher.full_name,
                total_classes=stats.total or 0,
                completed_classes=stats.completed or 0,
                avg_student_rating=round(stats.avg_rating or 0.0, 2),
                specializations=teacher.specializations or [],
                student_improvement_rate=improvement_rate,
                revenue_generated=round(stats.revenue or 0.0, 2)
            ))
        
        return performance_data
    
    @staticmethod
    async def _calculate_student_improvement(db: AsyncSession, teacher_id: int) -> float:
        """Calculate average student improvement rate for a teacher"""
        
        # Get students who have had classes with this teacher
        student_classes = await db.execute(
            select(Class.student_id).where(
                and_(
                    Class.teacher_id == teacher_id,
                    Class.status == ClassStatus.COMPLETED
                )
            ).distinct()
        )
        student_ids = [row[0] for row in student_classes.fetchall()]
        
        if not student_ids:
            return 0.0
        
        # Calculate improvement for each student
        improvements = []
        for student_id in student_ids:
            # Get first and latest essay scores
            first_essay = await db.execute(
                select(EssayGrading.overall_band).join(Essay).where(
                    Essay.author_id == student_id
                ).order_by(Essay.submitted_at.asc()).limit(1)
            )
            
            latest_essay = await db.execute(
                select(EssayGrading.overall_band).join(Essay).where(
                    Essay.author_id == student_id
                ).order_by(Essay.submitted_at.desc()).limit(1)
            )
            
            first_score = first_essay.scalar()
            latest_score = latest_essay.scalar()
            
            if first_score and latest_score:
                improvement = latest_score - first_score
                improvements.append(improvement)
        
        return round(sum(improvements) / len(improvements), 2) if improvements else 0.0

# API Endpoints

@router.get("/stats/platform")
async def get_platform_stats(
    admin_user: User = Depends(verify_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive platform statistics"""
    
    stats = await AdminAnalyticsService.get_platform_statistics(db)
    
    return {
        "platform_stats": stats.dict(),
        "generated_at": datetime.utcnow().isoformat(),
        "generated_by": admin_user.username
    }

@router.get("/analytics/users")
async def get_user_analytics(
    role: Optional[str] = Query(None, description="Filter by user role"),
    limit: int = Query(50, le=200, description="Limit results"),
    admin_user: User = Depends(verify_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed user analytics"""
    
    analytics = await AdminAnalyticsService.get_user_analytics(db, role, limit)
    
    return {
        "user_analytics": [user.dict() for user in analytics],
        "total_users": len(analytics),
        "filters": {"role": role, "limit": limit}
    }

@router.get("/analytics/teachers")
async def get_teacher_performance(
    admin_user: User = Depends(verify_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Get teacher performance analytics"""
    
    performance = await AdminAnalyticsService.get_teacher_performance(db)
    
    return {
        "teacher_performance": [teacher.dict() for teacher in performance],
        "total_teachers": len(performance),
        "top_performers": sorted(performance, key=lambda x: x.avg_student_rating, reverse=True)[:5]
    }

@router.get("/analytics/ai-usage")
async def get_ai_usage_analytics(
    days: int = Query(30, le=365, description="Number of days to analyze"),
    admin_user: User = Depends(verify_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Get AI usage and cost analytics"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Daily usage
    daily_usage = await db.execute(
        text("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as total_requests,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_requests,
            SUM(total_tokens) as total_tokens,
            SUM(cost_usd) as daily_cost,
            AVG(processing_time) as avg_processing_time
        FROM ai_requests 
        WHERE created_at >= :start_date
        GROUP BY DATE(created_at)
        ORDER BY date DESC
        """),
        {"start_date": start_date}
    )
    
    daily_data = [
        {
            "date": row.date.isoformat(),
            "total_requests": row.total_requests,
            "successful_requests": row.successful_requests,
            "success_rate": round((row.successful_requests / row.total_requests) * 100, 2) if row.total_requests > 0 else 0,
            "total_tokens": row.total_tokens or 0,
            "daily_cost": round(row.daily_cost or 0, 4),
            "avg_processing_time": round(row.avg_processing_time or 0, 2)
        }
        for row in daily_usage.fetchall()
    ]
    
    # Model usage breakdown
    model_usage = await db.execute(
        select(
            AIRequest.ai_model,
            func.count(AIRequest.id).label('requests'),
            func.sum(AIRequest.cost_usd).label('total_cost'),
            func.avg(AIRequest.processing_time).label('avg_time')
        ).where(
            AIRequest.created_at >= start_date
        ).group_by(AIRequest.ai_model)
    )
    
    model_data = [
        {
            "model": row.ai_model,
            "requests": row.requests,
            "total_cost": round(row.total_cost or 0, 4),
            "avg_processing_time": round(row.avg_time or 0, 2)
        }
        for row in model_usage.fetchall()
    ]
    
    # Request type breakdown
    type_usage = await db.execute(
        select(
            AIRequest.request_type,
            func.count(AIRequest.id).label('requests'),
            func.sum(AIRequest.cost_usd).label('total_cost')
        ).where(
            AIRequest.created_at >= start_date
        ).group_by(AIRequest.request_type)
    )
    
    type_data = [
        {
            "request_type": row.request_type,
            "requests": row.requests,
            "total_cost": round(row.total_cost or 0, 4)
        }
        for row in type_usage.fetchall()
    ]
    
    # Total summary
    total_summary = await db.execute(
        select(
            func.count(AIRequest.id).label('total_requests'),
            func.sum(AIRequest.cost_usd).label('total_cost'),
            func.avg(AIRequest.processing_time).label('avg_processing_time')
        ).where(
            AIRequest.created_at >= start_date
        )
    )
    summary = total_summary.first()
    
    return {
        "ai_usage_analytics": {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": datetime.utcnow().isoformat(),
            "summary": {
                "total_requests": summary.total_requests or 0,
                "total_cost": round(summary.total_cost or 0, 4),
                "avg_processing_time": round(summary.avg_processing_time or 0, 2),
                "estimated_monthly_cost": round((summary.total_cost or 0) * (30 / days), 2) if days > 0 else 0
            },
            "daily_usage": daily_data,
            "model_breakdown": model_data,
            "request_type_breakdown": type_data
        }
    }

@router.get("/analytics/student-progress")
async def get_student_progress_analytics(
    student_id: Optional[int] = Query(None, description="Specific student ID"),
    days: int = Query(90, le=365, description="Days to analyze"),
    admin_user: User = Depends(verify_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Get student learning progress analytics"""
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Base query
    query = select(User).where(
        and_(
            User.role == UserRole.STUDENT,
            User.is_active == True
        )
    ).options(selectinload(User.student_profile))
    
    if student_id:
        query = query.where(User.id == student_id)
    
    result = await db.execute(query)
    students = result.scalars().all()
    
    student_progress = []
    for student in students:
        # Get essay progress
        essay_progress = await db.execute(
            select(
                Essay.submitted_at,
                EssayGrading.overall_band
            ).join(EssayGrading).where(
                and_(
                    Essay.author_id == student.id,
                    Essay.submitted_at >= start_date
                )
            ).order_by(Essay.submitted_at)
        )
        
        essays = essay_progress.fetchall()
        
        # Get speaking progress
        speaking_progress = await db.execute(
            select(
                SpeakingTask.submitted_at,
                SpeakingAnalysis.overall_band
            ).join(SpeakingAnalysis).where(
                and_(
                    SpeakingTask.student_id == student.id,
                    SpeakingTask.submitted_at >= start_date
                )
            ).order_by(SpeakingTask.submitted_at)
        )
        
        speaking_tasks = speaking_progress.fetchall()
        
        # Calculate improvement
        essay_improvement = 0.0
        speaking_improvement = 0.0
        
        if len(essays) >= 2:
            essay_improvement = essays[-1].overall_band - essays[0].overall_band
        
        if len(speaking_tasks) >= 2:
            speaking_improvement = speaking_tasks[-1].overall_band - speaking_tasks[0].overall_band
        
        # Get class attendance
        class_attendance = await db.execute(
            select(func.count(Class.id)).where(
                and_(
                    Class.student_id == student.id,
                    Class.status == ClassStatus.COMPLETED,
                    Class.scheduled_start >= start_date
                )
            )
        )
        
        classes_attended = class_attendance.scalar() or 0
        
        student_data = {
            "student_id": student.id,
            "student_name": student.full_name,
            "current_level": student.current_level,
            "target_band": student.ielts_target_band,
            "profile": {
                "overall_band": student.student_profile.overall_band if student.student_profile else 0.0,
                "speaking_band": student.student_profile.speaking_band if student.student_profile else 0.0,
                "writing_band": student.student_profile.writing_band if student.student_profile else 0.0,
                "reading_band": student.student_profile.reading_band if student.student_profile else 0.0,
                "listening_band": student.student_profile.listening_band if student.student_profile else 0.0
            },
            "progress": {
                "essay_improvement": round(essay_improvement, 2),
                "speaking_improvement": round(speaking_improvement, 2),
                "total_essays": len(essays),
                "total_speaking_tasks": len(speaking_tasks),
                "classes_attended": classes_attended
            },
            "timeline": {
                "essays": [
                    {
                        "date": essay.submitted_at.isoformat(),
                        "score": essay.overall_band
                    }
                    for essay in essays
                ],
                "speaking": [
                    {
                        "date": task.submitted_at.isoformat(),
                        "score": task.overall_band
                    }
                    for task in speaking_tasks
                ]
            }
        }
        
        student_progress.append(student_data)
    
    return {
        "student_progress": student_progress,
        "period_days": days,
        "total_students": len(student_progress)
    }

@router.post("/manage/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int,
    reason: Optional[str] = None,
    admin_user: User = Depends(verify_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a user account"""
    
    # Get the user
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Cannot deactivate admin users")
    
    # Deactivate user
    user.is_active = False
    
    # Cancel future scheduled classes
    future_classes = await db.execute(
        select(Class).where(
            and_(
                or_(Class.teacher_id == user_id, Class.student_id == user_id),
                Class.status == ClassStatus.SCHEDULED,
                Class.scheduled_start > datetime.utcnow()
            )
        )
    )
    
    cancelled_classes = 0
    for cls in future_classes.scalars():
        cls.status = ClassStatus.CANCELLED
        cls.teacher_notes = f"Cancelled due to user deactivation by admin: {reason or 'No reason provided'}"
        cancelled_classes += 1
    
    await db.commit()
    
    return {
        "message": "User deactivated successfully",
        "user_id": user_id,
        "reason": reason,
        "cancelled_classes": cancelled_classes,
        "deactivated_by": admin_user.username,
        "deactivated_at": datetime.utcnow().isoformat()
    }

@router.post("/manage/users/{user_id}/activate")
async def activate_user(
    user_id: int,
    admin_user: User = Depends(verify_admin_access),
    db: AsyncSession = Depends(get_db)
):
    """Reactivate a user account"""
    
    user_result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    
    await db.commit()
    
    return {
        "message": "User activated successfully",
        "user_id": user_id,
        "activated_by": admin_user.username,
        "activated_at": datetime.utcnow().isoformat()
    }