# workers/celery_app.py - Celery Application Configuration
from celery import Celery
from config.settings import settings
import os

# Configure Celery app
celery_app = Celery(
    "language_ai_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["workers.ai_tasks", "workers.periodic_tasks"]
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Result backend
    result_expires=3600,  # 1 hour
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },
    
    # Task routing
    task_routes={
        "workers.ai_tasks.grade_essay": {"queue": "ai_tasks"},
        "workers.ai_tasks.analyze_speaking": {"queue": "ai_tasks"},
        "workers.ai_tasks.generate_curriculum": {"queue": "ai_tasks"},
        "workers.periodic_tasks.cleanup_old_files": {"queue": "maintenance"},
        "workers.periodic_tasks.update_student_progress": {"queue": "maintenance"},
    },
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=50,
    worker_max_memory_per_child=200000,  # 200MB
    
    # Task execution
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,       # 10 minutes
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'cleanup-old-files': {
            'task': 'workers.periodic_tasks.cleanup_old_files',
            'schedule': 86400.0,  # Run daily
        },
        'update-student-progress': {
            'task': 'workers.periodic_tasks.update_student_progress',
            'schedule': 3600.0,  # Run hourly
        },
    },
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
)

# workers/periodic_tasks.py - Scheduled Background Tasks
from celery import current_task
from datetime import datetime, timedelta
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from workers.celery_app import celery_app
from config.settings import settings
from app.models.models import StudentProfile, AIRequest, Essay, SpeakingTask

# Setup synchronous database for Celery
sync_engine = create_engine(settings.database_url.replace("+asyncpg", ""))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def cleanup_old_files(self):
    """
    Periodic task to clean up old uploaded files
    Runs daily to remove files older than 30 days
    """
    try:
        upload_dir = settings.upload_folder
        max_age_days = 30
        max_age_seconds = max_age_days * 24 * 60 * 60
        current_time = datetime.utcnow().timestamp()
        
        if not os.path.exists(upload_dir):
            logger.warning(f"Upload directory {upload_dir} does not exist")
            return {"status": "skipped", "reason": "directory_not_found"}
        
        cleaned_files = 0
        total_size_cleaned = 0
        
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)
            
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getctime(file_path)
                
                if file_age > max_age_seconds:
                    try:
                        file_size = os.path.getsize(file_path)
                        os.remove(file_path)
                        cleaned_files += 1
                        total_size_cleaned += file_size
                        logger.info(f"Cleaned up old file: {filename} ({file_size} bytes)")
                    except OSError as e:
                        logger.error(f"Failed to delete file {filename}: {str(e)}")
        
        self.update_state(
            state='SUCCESS',
            meta={
                'files_cleaned': cleaned_files,
                'total_size_cleaned': total_size_cleaned,
                'max_age_days': max_age_days
            }
        )
        
        logger.info(f"Cleanup completed: {cleaned_files} files removed, {total_size_cleaned} bytes freed")
        
        return {
            "status": "completed",
            "files_cleaned": cleaned_files,
            "total_size_cleaned": total_size_cleaned,
            "max_age_days": max_age_days
        }
        
    except Exception as e:
        logger.error(f"File cleanup failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise

@celery_app.task(bind=True)
def update_student_progress(self):
    """
    Periodic task to update student progress metrics
    Runs hourly to recalculate progress statistics
    """
    db = SessionLocal()
    
    try:
        # Get all student profiles
        profiles = db.query(StudentProfile).all()
        updated_count = 0
        
        for profile in profiles:
            try:
                # Calculate total study time from activities
                total_activities = profile.essays_completed + profile.speaking_sessions
                estimated_hours = total_activities * 0.5  # Estimate 30 minutes per activity
                
                # Update study hours if it has increased
                if estimated_hours > profile.total_study_hours:
                    profile.total_study_hours = estimated_hours
                
                # Update curriculum progress if curriculum is assigned
                if profile.current_curriculum_id:
                    # Calculate progress based on completed activities vs expected activities
                    expected_activities_per_week = 3
                    weeks_since_start = max(1, total_activities // expected_activities_per_week)
                    curriculum_weeks = 12  # Default curriculum length
                    
                    progress_percentage = min(100.0, (weeks_since_start / curriculum_weeks) * 100)
                    
                    if progress_percentage > profile.curriculum_progress:
                        profile.curriculum_progress = progress_percentage
                
                profile.updated_at = datetime.utcnow()
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Failed to update profile {profile.id}: {str(e)}")
                continue
        
        db.commit()
        
        self.update_state(
            state='SUCCESS',
            meta={'profiles_updated': updated_count}
        )
        
        logger.info(f"Updated progress for {updated_count} student profiles")
        
        return {
            "status": "completed",
            "profiles_updated": updated_count,
            "total_profiles": len(profiles)
        }
        
    except Exception as e:
        logger.error(f"Progress update failed: {str(e)}")
        db.rollback()
        
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise
        
    finally:
        db.close()

@celery_app.task(bind=True)
def generate_analytics_report(self):
    """
    Generate daily analytics report
    Runs daily at midnight to compile platform statistics
    """
    db = SessionLocal()
    
    try:
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        # Count yesterday's activities
        essays_submitted = db.query(Essay).filter(
            Essay.submitted_at >= yesterday.date(),
            Essay.submitted_at < datetime.utcnow().date()
        ).count()
        
        speaking_tasks = db.query(SpeakingTask).filter(
            SpeakingTask.submitted_at >= yesterday.date(),
            SpeakingTask.submitted_at < datetime.utcnow().date()
        ).count()
        
        ai_requests = db.query(AIRequest).filter(
            AIRequest.created_at >= yesterday.date(),
            AIRequest.created_at < datetime.utcnow().date()
        ).count()
        
        # Calculate total AI cost for yesterday
        total_cost = db.query(func.sum(AIRequest.cost_usd)).filter(
            AIRequest.created_at >= yesterday.date(),
            AIRequest.created_at < datetime.utcnow().date(),
            AIRequest.status == "completed"
        ).scalar() or 0.0
        
        report = {
            "date": yesterday.date().isoformat(),
            "essays_submitted": essays_submitted,
            "speaking_tasks_submitted": speaking_tasks,
            "ai_requests": ai_requests,
            "total_ai_cost": round(total_cost, 4),
            "generated_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Daily analytics report generated: {report}")
        
        return {
            "status": "completed",
            "report": report
        }
        
    except Exception as e:
        logger.error(f"Analytics report generation failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise
        
    finally:
        db.close()

# workers/monitoring.py - Worker Health Monitoring
from celery import current_task
from workers.celery_app import celery_app
import psutil
import logging

logger = logging.getLogger(__name__)

@celery_app.task(bind=True)
def health_check_worker(self):
    """
    Worker health check task
    Reports worker status and system metrics
    """
    try:
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Worker info
        worker_info = {
            "worker_id": self.request.id,
            "hostname": self.request.hostname,
            "task_name": self.name,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # System metrics
        system_metrics = {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2)
        }
        
        return {
            "status": "healthy",
            "worker_info": worker_info,
            "system_metrics": system_metrics
        }
        
    except Exception as e:
        logger.error(f"Worker health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

# workers/__init__.py
"""
Celery workers package for background task processing

This package contains:
- celery_app: Main Celery application configuration
- ai_tasks: AI processing tasks (essay grading, speaking analysis)
- periodic_tasks: Scheduled maintenance tasks
- monitoring: Worker health monitoring
"""

from .celery_app import celery_app

__all__ = ['celery_app']

# workers/utils.py - Utility Functions for Workers
import logging
import time
from functools import wraps
from typing import Any, Callable
from celery import current_task

logger = logging.getLogger(__name__)

def task_monitor(func: Callable) -> Callable:
    """
    Decorator to monitor task execution
    Adds logging and performance tracking to Celery tasks
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        task_name = func.__name__
        start_time = time.time()
        
        logger.info(f"Starting task: {task_name}")
        
        try:
            # Update task state to PROGRESS
            if current_task:
                current_task.update_state(
                    state='PROGRESS',
                    meta={'progress': 0, 'status': f'Starting {task_name}'}
                )
            
            # Execute the task
            result = func(*args, **kwargs)
            
            execution_time = time.time() - start_time
            logger.info(f"Task {task_name} completed successfully in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Task {task_name} failed after {execution_time:.2f}s: {str(e)}")
            
            if current_task:
                current_task.update_state(
                    state='FAILURE',
                    meta={'error': str(e), 'execution_time': execution_time}
                )
            
            raise
    
    return wrapper

def get_task_progress(task_id: str) -> dict:
    """
    Get the current progress of a task
    """
    from workers.celery_app import celery_app
    
    result = celery_app.AsyncResult(task_id)
    
    if result.state == 'PENDING':
        return {
            'state': result.state,
            'progress': 0,
            'status': 'Task is waiting to be processed'
        }
    elif result.state == 'PROGRESS':
        return {
            'state': result.state,
            'progress': result.info.get('progress', 0),
            'status': result.info.get('status', 'Processing...')
        }
    elif result.state == 'SUCCESS':
        return {
            'state': result.state,
            'progress': 100,
            'status': 'Task completed successfully',
            'result': result.result
        }
    else:  # FAILURE
        return {
            'state': result.state,
            'progress': 0,
            'status': 'Task failed',
            'error': str(result.info)
        }

def cancel_task(task_id: str) -> bool:
    """
    Cancel a running task
    """
    from workers.celery_app import celery_app
    
    try:
        celery_app.control.revoke(task_id, terminate=True)
        logger.info(f"Task {task_id} cancelled successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {str(e)}")
        return False

# scripts/start_worker.py - Worker Startup Script
#!/usr/bin/env python3
"""
Start Celery worker with proper configuration
"""
import sys
import os
import subprocess
import argparse

def start_worker(
    queue: str = "ai_tasks",
    concurrency: int = 2,
    loglevel: str = "info",
    pool: str = "prefork"
):
    """Start Celery worker with specified configuration"""
    
    # Ensure we're in the right directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    cmd = [
        "celery",
        "-A", "workers.celery_app",
        "worker",
        f"--loglevel={loglevel}",
        f"--queues={queue}",
        f"--concurrency={concurrency}",
        f"--pool={pool}",
        "--optimization=fair"
    ]
    
    print(f"🚀 Starting Celery worker...")
    print(f"Queue: {queue}")
    print(f"Concurrency: {concurrency}")
    print(f"Pool: {pool}")
    print(f"Log level: {loglevel}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 Worker stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Worker failed to start: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Start Celery worker")
    parser.add_argument("--queue", default="ai_tasks", help="Queue to process")
    parser.add_argument("--concurrency", type=int, default=2, help="Number of worker processes")
    parser.add_argument("--loglevel", default="info", help="Log level")
    parser.add_argument("--pool", default="prefork", help="Pool implementation")
    
    args = parser.parse_args()
    
    start_worker(
        queue=args.queue,
        concurrency=args.concurrency,
        loglevel=args.loglevel,
        pool=args.pool
    )

if __name__ == "__main__":
    main()

# scripts/start_beat.py - Celery Beat Scheduler
#!/usr/bin/env python3
"""
Start Celery Beat scheduler for periodic tasks
"""
import os
import subprocess
import sys

def start_beat(loglevel: str = "info"):
    """Start Celery Beat scheduler"""
    
    # Ensure we're in the right directory
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    cmd = [
        "celery",
        "-A", "workers.celery_app",
        "beat",
        f"--loglevel={loglevel}",
        "--schedule=/tmp/celerybeat-schedule",
        "--pidfile=/tmp/celerybeat.pid"
    ]
    
    print(f"⏰ Starting Celery Beat scheduler...")
    print(f"Log level: {loglevel}")
    print(f"Command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n👋 Beat scheduler stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Beat scheduler failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Start Celery Beat scheduler")
    parser.add_argument("--loglevel", default="info", help="Log level")
    
    args = parser.parse_args()
    start_beat(args.loglevel)