from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime, timedelta
import json

from app.database import get_db
from app.models.models import User
from app.api.auth.auth import get_current_active_user

router = APIRouter(prefix="/api/curriculum", tags=["AI Curriculum"])

class CurriculumRequest(BaseModel):
    current_level: str
    target_band: float
    exam_date: str
    study_time_per_day: int  # minutes
    weak_areas: List[str] = []
    priority_skills: List[str] = []

class StudyPlan(BaseModel):
    week: int
    focus_area: str
    daily_tasks: List[Dict[str, Any]]
    goals: List[str]
    estimated_improvement: float

class CurriculumResponse(BaseModel):
    plan_id: str
    total_weeks: int
    study_plans: List[StudyPlan]
    daily_schedule: Dict[str, List[str]]
    progress_milestones: List[Dict[str, Any]]

@router.post("/generate", response_model=CurriculumResponse)
async def generate_ai_curriculum(
    request: CurriculumRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate AI-powered personalized curriculum"""
    
    # Calculate study duration
    exam_date = datetime.fromisoformat(request.exam_date.replace('Z', '+00:00'))
    today = datetime.now()
    days_to_exam = (exam_date - today).days
    weeks_available = max(1, days_to_exam // 7)
    
    # Determine current band from level
    level_to_band = {
        "beginner": 4.5,
        "intermediate": 5.5,
        "advanced": 6.5,
        "expert": 7.5
    }
    current_band = level_to_band.get(request.current_level, 5.5)
    
    # Generate weekly study plans
    study_plans = []
    skills = ["reading", "listening", "writing", "speaking"]
    
    for week in range(1, min(weeks_available + 1, 12)):  # Max 12 weeks
        # Determine focus based on week and weak areas
        if week <= 2:
            focus = "Foundation Building"
            focus_skills = ["reading", "listening"]
        elif week <= 4:
            focus = "Core Skills Development"
            focus_skills = request.weak_areas if request.weak_areas else ["writing", "speaking"]
        elif week <= 6:
            focus = "Advanced Practice"
            focus_skills = request.priority_skills if request.priority_skills else skills
        else:
            focus = "Exam Preparation"
            focus_skills = skills
        
        # Generate daily tasks
        daily_tasks = generate_daily_tasks(
            week, focus_skills, request.study_time_per_day, current_band, request.target_band
        )
        
        # Set goals for the week
        goals = generate_weekly_goals(week, focus_skills, current_band)
        
        # Estimate improvement
        improvement = min(0.5, (request.target_band - current_band) / weeks_available)
        
        study_plans.append(StudyPlan(
            week=week,
            focus_area=focus,
            daily_tasks=daily_tasks,
            goals=goals,
            estimated_improvement=improvement
        ))
    
    # Generate daily schedule template
    daily_schedule = generate_daily_schedule(request.study_time_per_day)
    
    # Generate progress milestones
    milestones = generate_milestones(weeks_available, current_band, request.target_band)
    
    return CurriculumResponse(
        plan_id=f"plan_{current_user.id}_{datetime.now().strftime('%Y%m%d')}",
        total_weeks=len(study_plans),
        study_plans=study_plans,
        daily_schedule=daily_schedule,
        progress_milestones=milestones
    )

def generate_daily_tasks(week: int, focus_skills: List[str], study_time: int, current_band: float, target_band: float) -> List[Dict[str, Any]]:
    """Generate daily tasks based on focus skills and time available"""
    
    task_templates = {
        "reading": [
            {"activity": "Academic passage practice", "time": 20, "difficulty": "progressive"},
            {"activity": "Vocabulary building", "time": 10, "difficulty": "adaptive"},
            {"activity": "Question type practice", "time": 15, "difficulty": "targeted"}
        ],
        "listening": [
            {"activity": "IELTS listening sections", "time": 30, "difficulty": "progressive"},
            {"activity": "Note-taking practice", "time": 10, "difficulty": "basic"},
            {"activity": "Accent familiarization", "time": 15, "difficulty": "varied"}
        ],
        "writing": [
            {"activity": "Task 1 practice", "time": 25, "difficulty": "progressive"},
            {"activity": "Task 2 essay", "time": 45, "difficulty": "structured"},
            {"activity": "Grammar review", "time": 15, "difficulty": "targeted"}
        ],
        "speaking": [
            {"activity": "Part 1 practice", "time": 10, "difficulty": "basic"},
            {"activity": "Part 2 topic preparation", "time": 15, "difficulty": "creative"},
            {"activity": "Part 3 discussion", "time": 20, "difficulty": "analytical"}
        ]
    }
    
    daily_tasks = []
    time_per_skill = study_time // len(focus_skills) if focus_skills else study_time // 4
    
    for skill in focus_skills:
        skill_tasks = task_templates.get(skill, [])
        allocated_time = 0
        
        for task in skill_tasks:
            if allocated_time + task["time"] <= time_per_skill:
                daily_tasks.append({
                    "skill": skill,
                    "activity": task["activity"],
                    "duration": task["time"],
                    "difficulty": adjust_difficulty(task["difficulty"], current_band, target_band, week),
                    "priority": get_priority(skill, week)
                })
                allocated_time += task["time"]
    
    return daily_tasks

def generate_weekly_goals(week: int, focus_skills: List[str], current_band: float) -> List[str]:
    """Generate specific goals for each week"""
    
    goal_templates = {
        1: [
            "Complete diagnostic test for all skills",
            "Establish baseline scores",
            "Learn IELTS test format"
        ],
        2: [
            "Improve reading speed by 20%",
            "Master basic question types",
            "Build core vocabulary (100 words)"
        ],
        3: [
            "Achieve 70% accuracy in listening Section 1",
            "Complete first Task 2 essay",
            "Practice Part 1 speaking fluently"
        ],
        4: [
            "Score 6+ in reading practice test",
            "Master Task 1 report structure",
            "Speak for 2 minutes without hesitation"
        ]
    }
    
    base_goals = goal_templates.get(week, [
        f"Improve {', '.join(focus_skills)} skills",
        "Complete weekly practice tests",
        "Review and strengthen weak areas"
    ])
    
    return base_goals

def generate_daily_schedule(study_time: int) -> Dict[str, List[str]]:
    """Generate optimal daily study schedule"""
    
    if study_time <= 30:
        return {
            "short_session": [
                "5min: Vocabulary review",
                "20min: Focused skill practice",
                "5min: Progress tracking"
            ]
        }
    elif study_time <= 60:
        return {
            "medium_session": [
                "10min: Warm-up (vocabulary/grammar)",
                "40min: Main practice (2 skills)",
                "10min: Review and planning"
            ]
        }
    else:
        return {
            "long_session": [
                "15min: Warm-up and review",
                "30min: Reading/Listening practice",
                "30min: Writing/Speaking practice", 
                "15min: Vocabulary and review"
            ]
        }

def generate_milestones(weeks: int, current_band: float, target_band: float) -> List[Dict[str, Any]]:
    """Generate progress milestones"""
    
    milestones = []
    improvement_per_milestone = (target_band - current_band) / max(1, weeks // 2)
    
    for i in range(1, weeks // 2 + 1):
        milestone_week = i * 2
        expected_band = current_band + (i * improvement_per_milestone)
        
        milestones.append({
            "week": milestone_week,
            "target_band": round(expected_band, 1),
            "assessment_type": "Practice test",
            "skills_focus": ["reading", "listening", "writing", "speaking"],
            "success_criteria": [
                f"Achieve {expected_band}+ overall",
                "Complete test within time limits",
                "Show improvement in weak areas"
            ]
        })
    
    return milestones

def adjust_difficulty(base_difficulty: str, current_band: float, target_band: float, week: int) -> str:
    """Adjust task difficulty based on progress"""
    
    if current_band >= 7.0:
        return "advanced"
    elif current_band >= 6.0:
        return "intermediate" if week <= 4 else "advanced"
    else:
        return "basic" if week <= 2 else "intermediate"

def get_priority(skill: str, week: int) -> str:
    """Determine priority level for skill"""
    
    # Early weeks focus on receptive skills
    if week <= 2 and skill in ["reading", "listening"]:
        return "high"
    # Later weeks focus on productive skills
    elif week > 2 and skill in ["writing", "speaking"]:
        return "high"
    else:
        return "medium"

@router.get("/progress/{plan_id}")
async def get_curriculum_progress(
    plan_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """Get progress on current curriculum"""
    
    # Mock progress data - in real app, track actual completion
    return {
        "plan_id": plan_id,
        "current_week": 3,
        "overall_progress": 65,  # percentage
        "skills_progress": {
            "reading": 70,
            "listening": 75,
            "writing": 55,
            "speaking": 60
        },
        "completed_tasks": 45,
        "total_tasks": 70,
        "current_estimated_band": 6.0,
        "next_milestone": {
            "week": 4,
            "target": "Complete practice test",
            "due_date": "2025-07-25"
        },
        "recommendations": [
            "Focus more on writing practice",
            "Complete missed listening exercises",
            "Schedule practice test for this week"
        ]
    }

@router.post("/update-progress")
async def update_task_completion(
    task_data: Dict[str, Any],
    current_user: User = Depends(get_current_active_user)
):
    """Update completion status of curriculum tasks"""
    
    # In real app, save to database
    return {
        "message": "Progress updated successfully",
        "task_id": task_data.get("task_id"),
        "completed": task_data.get("completed", False),
        "score": task_data.get("score"),
        "time_spent": task_data.get("time_spent"),
        "updated_at": datetime.now().isoformat()
    }

@router.get("/recommendations")
async def get_ai_recommendations(
    current_user: User = Depends(get_current_active_user)
):
    """Get AI-powered study recommendations"""
    
    return {
        "immediate_focus": [
            "Complete 2 reading passages today",
            "Practice Task 1 writing (charts/graphs)",
            "Listen to Section 2 audio exercises"
        ],
        "this_week": [
            "Take a full practice test",
            "Review grammar: conditionals and passive voice",
            "Build vocabulary: academic word list 1-100"
        ],
        "skill_specific": {
            "reading": "Focus on True/False/Not Given questions - your accuracy is 45%",
            "listening": "Practice note completion - you're missing 3/10 answers",
            "writing": "Work on coherence and cohesion - use more linking words",
            "speaking": "Extend your Part 2 responses - aim for full 2 minutes"
        },
        "motivation": "You're 65% through your study plan. Keep going! 🎯"
    }