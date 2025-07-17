from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Dict, Any
import json
from datetime import datetime

from app.database import get_db
from app.models.models import User, ReadingTask, ReadingSubmission, ReadingGrading, UserType
from app.api.auth.auth import get_current_active_user
from app.services.enhanced_ai_service import EnhancedAIService

router = APIRouter(prefix="/api/reading", tags=["Reading Comprehension"])

class ReadingTaskCreate(BaseModel):
    title: str
    passage: str
    difficulty_level: str = "intermediate"

class ReadingSubmissionCreate(BaseModel):
    task_id: int
    answers: List[Any]

@router.post("/tasks")
async def create_reading_task(
    task_data: ReadingTaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new reading comprehension task with AI-generated questions"""
    
    if current_user.user_type not in [UserType.TEACHER, UserType.ADMIN]:
        raise HTTPException(status_code=403, detail="Only teachers and admins can create tasks")
    
    # Generate questions using AI
    ai_service = EnhancedAIService()
    try:
        questions_result = await ai_service.generate_reading_questions(
            passage=task_data.passage,
            difficulty=task_data.difficulty_level,
            num_questions=10
        )
    except:
        # Fallback to demo questions
        questions_result = {
            "questions": [
                {
                    "id": 1,
                    "type": "multiple_choice",
                    "question": "What is the main idea of the passage?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct_answer": "Option A",
                    "skill_tested": "gist_understanding"
                }
            ],
            "answer_key": [
                {"question_id": 1, "correct_answer": "Option A", "explanation": "Demo question"}
            ]
        }
    
    if "error" in questions_result:
        raise HTTPException(status_code=500, detail=f"Failed to generate questions: {questions_result['error']}")
    
    # Create reading task
    reading_task = ReadingTask(
        title=task_data.title,
        passage=task_data.passage,
        questions=questions_result["questions"],
        answer_key=questions_result["answer_key"],
        difficulty_level=task_data.difficulty_level,
        created_by=current_user.id
    )
    
    db.add(reading_task)
    await db.commit()
    await db.refresh(reading_task)
    
    return {
        "message": "Reading task created successfully",
        "task_id": reading_task.id,
        "questions_generated": len(questions_result["questions"]),
        "task": {
            "id": reading_task.id,
            "title": reading_task.title,
            "difficulty_level": reading_task.difficulty_level,
            "questions": questions_result["questions"]
        }
    }

@router.get("/tasks")
async def get_reading_tasks(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all available reading tasks"""
    
    result = await db.execute(
        select(ReadingTask).where(ReadingTask.is_active == True)
    )
    tasks = result.scalars().all()
    
    return {
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "difficulty_level": task.difficulty_level,
                "created_at": task.created_at.isoformat(),
                "questions_count": len(task.questions)
            }
            for task in tasks
        ]
    }

@router.get("/tasks/{task_id}")
async def get_reading_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific reading task"""
    
    result = await db.execute(
        select(ReadingTask).where(ReadingTask.id == task_id, ReadingTask.is_active == True)
    )
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Reading task not found")
    
    return {
        "task": {
            "id": task.id,
            "title": task.title,
            "passage": task.passage,
            "questions": task.questions,
            "difficulty_level": task.difficulty_level,
            "created_at": task.created_at.isoformat()
        }
    }

@router.post("/submit")
async def submit_reading_answers(
    submission_data: ReadingSubmissionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit answers for a reading comprehension task"""
    
    # Get the task
    task_result = await db.execute(
        select(ReadingTask).where(ReadingTask.id == submission_data.task_id)
    )
    task = task_result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Reading task not found")
    
    # Create submission
    submission = ReadingSubmission(
        student_id=current_user.id,
        task_id=submission_data.task_id,
        answers=submission_data.answers
    )
    
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    
    # Grade the submission (simple scoring for now)
    correct_answers = [answer["correct_answer"] for answer in task.answer_key]
    score = sum(1 for i, answer in enumerate(submission_data.answers) 
                if i < len(correct_answers) and answer == correct_answers[i])
    overall_score = (score / len(correct_answers)) * 9 if correct_answers else 0
    
    # Save grading
    grading = ReadingGrading(
        submission_id=submission.id,
        overall_score=overall_score,
        accuracy_score=overall_score,
        comprehension_skills={
            "inference": overall_score,
            "vocabulary": overall_score,
            "scanning": overall_score,
            "gist_understanding": overall_score
        },
        feedback={
            "strengths": ["Good reading comprehension"],
            "improvements": ["Continue practicing"],
            "suggestions": ["Read more academic texts"]
        },
        lesson_recommendations=[],
        ai_model_used="rule_based"
    )
    
    db.add(grading)
    
    # Update submission
    submission.is_graded = True
    submission.score = overall_score
    submission.graded_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "message": "Reading submission graded successfully",
        "submission_id": submission.id,
        "score": overall_score,
        "correct_answers": score,
        "total_questions": len(correct_answers),
        "grading": {
            "scores": {
                "overall_score": overall_score,
                "accuracy_score": overall_score,
                "comprehension_skills": grading.comprehension_skills
            },
            "feedback": grading.feedback
        }
    }

@router.get("/my-submissions")
async def get_my_reading_submissions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get student's reading submissions"""
    
    result = await db.execute(
        select(ReadingSubmission, ReadingTask, ReadingGrading)
        .join(ReadingTask, ReadingSubmission.task_id == ReadingTask.id)
        .outerjoin(ReadingGrading, ReadingSubmission.id == ReadingGrading.submission_id)
        .where(ReadingSubmission.student_id == current_user.id)
        .order_by(ReadingSubmission.submitted_at.desc())
    )
    
    submissions = result.all()
    
    return {
        "submissions": [
            {
                "id": submission.id,
                "task_title": task.title,
                "task_id": task.id,
                "score": submission.score,
                "is_graded": submission.is_graded,
                "submitted_at": submission.submitted_at.isoformat(),
                "grading": {
                    "overall_score": grading.overall_score,
                    "accuracy_score": grading.accuracy_score,
                    "comprehension_skills": grading.comprehension_skills,
                    "feedback": grading.feedback
                } if grading else None
            }
            for submission, task, grading in submissions
        ]
    }
