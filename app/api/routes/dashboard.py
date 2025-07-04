from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from app.database import get_db
from app.models.models import User, Essay, EssayGrading
from app.api.auth.auth import get_current_active_user

router = APIRouter(prefix="/api/dashboard", tags=["User Dashboard"])

@router.get("/my-progress")
async def get_my_progress(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's learning progress"""
    
    # Get user's essays
    essays_result = await db.execute(
        select(Essay).where(Essay.author_id == current_user.id)
    )
    user_essays = essays_result.scalars().all()
    
    # Get graded essays with scores
    graded_result = await db.execute(
        select(Essay, EssayGrading)
        .join(EssayGrading, Essay.id == EssayGrading.essay_id)
        .where(Essay.author_id == current_user.id)
        .order_by(Essay.submitted_at.asc())
    )
    graded_essays = graded_result.all()
    
    # Calculate progress metrics
    total_essays = len(user_essays)
    graded_count = len(graded_essays)
    
    # Score progression
    scores = [grading.overall_band for essay, grading in graded_essays]
    avg_score = sum(scores) / len(scores) if scores else 0
    latest_score = scores[-1] if scores else 0
    improvement = (latest_score - scores[0]) if len(scores) > 1 else 0
    
    # Skill analysis
    skill_scores = {}
    if graded_essays:
        skills = ['task_achievement', 'coherence_cohesion', 'lexical_resource', 'grammar_accuracy']
        for skill in skills:
            skill_values = [getattr(grading, skill) for essay, grading in graded_essays]
            skill_scores[skill] = {
                'current': skill_values[-1] if skill_values else 0,
                'average': sum(skill_values) / len(skill_values) if skill_values else 0,
                'improvement': skill_values[-1] - skill_values[0] if len(skill_values) > 1 else 0
            }
    
    return {
        "user_info": {
            "username": current_user.username,
            "full_name": current_user.full_name,
            "member_since": current_user.created_at.isoformat()
        },
        "essay_stats": {
            "total_submitted": total_essays,
            "total_graded": graded_count,
            "pending_grading": total_essays - graded_count,
            "average_score": round(avg_score, 1),
            "latest_score": latest_score,
            "improvement": round(improvement, 1)
        },
        "skill_breakdown": skill_scores,
        "recent_essays": [
            {
                "id": essay.id,
                "title": essay.title,
                "score": essay.overall_score,
                "submitted_at": essay.submitted_at.isoformat()
            }
            for essay in user_essays[-5:]  # Last 5 essays
        ],
        "achievements": [
            "🎯 First Essay Submitted!" if total_essays >= 1 else None,
            "📈 First Essay Graded!" if graded_count >= 1 else None,
            f"🌟 Score Improvement: +{improvement:.1f}" if improvement > 0.5 else None,
            "🏆 Vocabulary Master!" if any(skill_scores.get(skill, {}).get('current', 0) >= 7.0 for skill in ['lexical_resource']) else None
        ],
        "next_goals": [
            f"📝 Submit {5 - total_essays} more essays" if total_essays < 5 else "✅ Essay milestone reached!",
            f"🎯 Improve overall score to {latest_score + 0.5:.1f}" if latest_score > 0 and latest_score < 8.0 else "🎉 Excellent progress!",
            "📚 Focus on weak areas" if skill_scores else "Keep practicing!"
        ]
    }

@router.get("/learning-tips")
async def get_personalized_tips(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get personalized learning tips based on user's performance"""
    
    # Get latest grading
    latest_result = await db.execute(
        select(EssayGrading)
        .join(Essay, EssayGrading.essay_id == Essay.id)
        .where(Essay.author_id == current_user.id)
        .order_by(Essay.submitted_at.desc())
        .limit(1)
    )
    latest_grading = latest_result.scalar_one_or_none()
    
    tips = {
        "general": [
            "📚 Read academic articles daily to improve vocabulary",
            "✍️ Practice writing essays regularly (aim for 3 per week)",
            "🎯 Focus on essay structure: Introduction → Body → Conclusion",
            "🔗 Use linking words to connect your ideas"
        ]
    }
    
    if latest_grading:
        # Personalized tips based on weakest areas
        scores = {
            'task_achievement': latest_grading.task_achievement,
            'coherence_cohesion': latest_grading.coherence_cohesion,
            'lexical_resource': latest_grading.lexical_resource,
            'grammar_accuracy': latest_grading.grammar_accuracy
        }
        
        weakest_skill = min(scores.items(), key=lambda x: x[1])
        
        skill_tips = {
            'task_achievement': [
                "🎯 Ensure you fully answer the essay question",
                "📖 Develop each main point with examples",
                "📝 Write longer paragraphs with detailed explanations"
            ],
            'coherence_cohesion': [
                "🔗 Use more transition words: However, Furthermore, Therefore",
                "📋 Create clear paragraph structure",
                "➡️ Ensure each paragraph has one main idea"
            ],
            'lexical_resource': [
                "📚 Learn 5 new academic words daily",
                "🔄 Avoid repeating the same words",
                "💡 Use synonyms and varied expressions"
            ],
            'grammar_accuracy': [
                "🔧 Practice complex sentence structures",
                "📖 Use conditional sentences (if, unless, provided)",
                "🔗 Combine sentences with relative clauses (which, that, who)"
            ]
        }
        
        tips["personalized"] = skill_tips.get(weakest_skill[0], tips["general"])
        tips["focus_area"] = weakest_skill[0].replace('_', ' ').title()
        tips["current_score"] = weakest_skill[1]
    
    return tips
