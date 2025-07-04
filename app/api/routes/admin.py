from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.database import get_db
from app.models.models import User, Essay, EssayGrading
from app.api.auth.auth import get_current_active_user

router = APIRouter(prefix="/api/admin", tags=["Admin Dashboard"])

async def verify_admin(current_user: User = Depends(get_current_active_user)):
    """Verify user is admin (for now, any user can access - you can restrict this)"""
    return current_user

@router.get("/stats")
async def get_platform_stats(
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get platform statistics"""
    
    # Count users
    user_count_result = await db.execute(select(func.count(User.id)))
    total_users = user_count_result.scalar()
    
    # Count essays
    essay_count_result = await db.execute(select(func.count(Essay.id)))
    total_essays = essay_count_result.scalar()
    
    # Count graded essays
    graded_count_result = await db.execute(
        select(func.count(Essay.id)).where(Essay.is_graded == True)
    )
    graded_essays = graded_count_result.scalar()
    
    # Average score
    avg_score_result = await db.execute(
        select(func.avg(EssayGrading.overall_band))
    )
    avg_score = avg_score_result.scalar() or 0
    
    # Recent activity (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_essays_result = await db.execute(
        select(func.count(Essay.id)).where(Essay.submitted_at >= week_ago)
    )
    recent_essays = recent_essays_result.scalar()
    
    return {
        "platform_stats": {
            "total_users": total_users,
            "total_essays": total_essays,
            "graded_essays": graded_essays,
            "pending_grading": total_essays - graded_essays,
            "average_score": round(float(avg_score), 2) if avg_score else 0,
            "essays_this_week": recent_essays
        },
        "system_info": {
            "ai_grading": "Free Rule-Based System",
            "cost_saved": f"${(graded_essays * 0.10):.2f}",
            "uptime": "Running smoothly",
            "database": "SQLite (Development)"
        },
        "generated_at": datetime.utcnow().isoformat()
    }

@router.get("/recent-activity")
async def get_recent_activity(
    limit: int = 10,
    current_user: User = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get recent platform activity"""
    
    # Recent essays
    recent_essays_result = await db.execute(
        select(Essay, User)
        .join(User, Essay.author_id == User.id)
        .order_by(Essay.submitted_at.desc())
        .limit(limit)
    )
    recent_essays = recent_essays_result.all()
    
    return {
        "recent_essays": [
            {
                "id": essay.id,
                "title": essay.title,
                "author": user.username,
                "word_count": essay.word_count,
                "is_graded": essay.is_graded,
                "score": essay.overall_score,
                "submitted_at": essay.submitted_at.isoformat()
            }
            for essay, user in recent_essays
        ],
        "total_shown": len(recent_essays)
    }
