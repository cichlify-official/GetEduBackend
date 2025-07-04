from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_db
from app.api.auth.auth import get_current_active_user
from app.models.models import User
from workers.ai_tasks import grade_essay, analyze_speaking, get_task_status

router = APIRouter()

@router.post("/api/tasks/grade-essay/{essay_id}")
async def queue_essay_grading(
    essay_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Queue an essay for AI grading
    Returns immediately with a task ID that can be used to check progress
    """
    # Verify essay belongs to current user
    from sqlalchemy import select
    from app.models.models import Essay
    
    result = await db.execute(
        select(Essay).where(Essay.id == essay_id, Essay.author_id == current_user.id)
    )
    essay = result.scalar_one_or_none()
    
    if not essay:
        raise HTTPException(status_code=404, detail="Essay not found")
    
    if essay.is_graded:
        raise HTTPException(status_code=400, detail="Essay already graded")
    
    # Queue the grading task
    task = grade_essay.delay(essay_id, current_user.id)
    
    return {
        "message": "Essay queued for grading",
        "task_id": task.id,
        "essay_id": essay_id,
        "status": "queued"
    }

@router.post("/api/tasks/analyze-speaking/{speaking_task_id}")
async def queue_speaking_analysis(
    speaking_task_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Queue a speaking task for AI analysis
    """
    # Verify speaking task belongs to current user
    from sqlalchemy import select
    from app.models.models import SpeakingTask
    
    result = await db.execute(
        select(SpeakingTask).where(
            SpeakingTask.id == speaking_task_id, 
            SpeakingTask.user_id == current_user.id
        )
    )
    speaking_task = result.scalar_one_or_none()
    
    if not speaking_task:
        raise HTTPException(status_code=404, detail="Speaking task not found")
    
    if speaking_task.is_analyzed:
        raise HTTPException(status_code=400, detail="Speaking task already analyzed")
    
    # Queue the analysis task
    task = analyze_speaking.delay(speaking_task_id, current_user.id)
    
    return {
        "message": "Speaking task queued for analysis",
        "task_id": task.id,
        "speaking_task_id": speaking_task_id,
        "status": "queued"
    }

@router.get("/api/tasks/status/{task_id}")
async def get_task_status_endpoint(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """
    Check the status of a background task
    Frontend can poll this endpoint to show progress
    """
    task_info = get_task_status(task_id)
    
    return {
        "task_id": task_id,
        "status": task_info["status"],
        "progress": task_info.get("info", {}).get("progress", 0),
        "result": task_info["result"],
        "error": task_info["traceback"] if task_info["status"] == "FAILURE" else None
    }