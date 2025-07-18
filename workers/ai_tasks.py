# workers/ai_tasks.py - Complete Implementation
import asyncio
from celery import current_task
from datetime import datetime
import json
import time
import logging
from typing import Dict, Any
import os

from workers.celery_app import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.models import (
    Essay, EssayGrading, SpeakingTask, SpeakingAnalysis, 
    AIRequest, User, StudentProfile, Curriculum
)
from config.settings import settings

# Setup synchronous database for Celery
sync_engine = create_engine(settings.database_url.replace("+asyncpg", ""))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

logger = logging.getLogger(__name__)

@celery_app.task(bind=True, max_retries=3)
def grade_essay(self, essay_id: int, user_id: int):
    """
    Background task to grade an essay using AI
    """
    start_time = time.time()
    task_id = self.request.id
    
    # Update task status
    self.update_state(state='PROCESSING', meta={'progress': 10, 'status': 'Initializing'})
    
    db = SessionLocal()
    
    try:
        # Get essay from database
        essay = db.query(Essay).filter(Essay.id == essay_id).first()
        if not essay:
            raise Exception(f"Essay {essay_id} not found")
        
        # Create AI request record for tracking
        ai_request = AIRequest(
            user_id=user_id,
            request_type="essay_grading",
            ai_model="pending",
            status="processing"
        )
        db.add(ai_request)
        db.commit()
        
        self.update_state(state='PROCESSING', meta={'progress': 25, 'status': 'Analyzing content'})
        
        # Import AI service (synchronous version for Celery)
        from app.services.sync_ai_service import SyncAIServiceManager
        ai_manager = SyncAIServiceManager()
        
        # Grade the essay
        grading_result = ai_manager.grade_essay(
            content=essay.content,
            task_type=essay.task_type,
            language=essay.language.value if essay.language else "english",
            word_count=essay.word_count
        )
        
        self.update_state(state='PROCESSING', meta={'progress': 75, 'status': 'Saving results'})
        
        # Save grading results
        essay_grading = EssayGrading(
            essay_id=essay_id,
            task_achievement=grading_result["scores"]["task_achievement"],
            coherence_cohesion=grading_result["scores"]["coherence_cohesion"],
            lexical_resource=grading_result["scores"]["lexical_resource"],
            grammar_accuracy=grading_result["scores"]["grammar_accuracy"],
            overall_band=grading_result["scores"]["overall_band"],
            feedback=grading_result["feedback"],
            ai_model_used=grading_result.get("model", "ai_service"),
            processing_time=time.time() - start_time,
            tokens_used=grading_result.get("tokens_used", 0),
            processing_cost=grading_result.get("cost", 0.0),
            confidence_score=grading_result.get("confidence", 0.8)
        )
        
        db.add(essay_grading)
        
        # Update essay status
        essay.is_graded = True
        essay.overall_score = grading_result["scores"]["overall_band"]
        essay.graded_at = datetime.utcnow()
        
        # Update AI request
        ai_request.status = "completed"
        ai_request.ai_model = grading_result.get("model", "unknown")
        ai_request.total_tokens = grading_result.get("tokens_used", 0)
        ai_request.cost_usd = grading_result.get("cost", 0.0)
        ai_request.processing_time = time.time() - start_time
        ai_request.completed_at = datetime.utcnow()
        
        # Update student profile
        student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
        if student_profile:
            student_profile.essays_completed += 1
            student_profile.writing_band = grading_result["scores"]["overall_band"]
            # Update overall band as average of all skills
            skills = [student_profile.writing_band, student_profile.speaking_band, 
                     student_profile.reading_band, student_profile.listening_band]
            valid_skills = [s for s in skills if s > 0]
            if valid_skills:
                student_profile.overall_band = sum(valid_skills) / len(valid_skills)
        
        db.commit()
        
        self.update_state(state='SUCCESS', meta={'progress': 100, 'status': 'Completed'})
        
        logger.info(f"Essay {essay_id} graded successfully in {time.time() - start_time:.2f}s")
        
        return {
            "status": "completed",
            "essay_id": essay_id,
            "overall_band": grading_result["scores"]["overall_band"],
            "processing_time": time.time() - start_time,
            "cost": grading_result.get("cost", 0.0),
            "ai_service": grading_result.get("ai_service", "unknown"),
            "task_id": task_id
        }
        
    except Exception as e:
        # Handle errors gracefully
        logger.error(f"Essay grading failed for essay {essay_id}: {str(e)}")
        
        if 'ai_request' in locals():
            ai_request.status = "failed"
            ai_request.error_message = str(e)
            ai_request.completed_at = datetime.utcnow()
            db.commit()
        
        db.rollback()
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying essay grading (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'progress': 0, 'status': 'Failed'}
        )
        
        raise Exception(f"Essay grading failed after {self.max_retries} attempts: {str(e)}")
    
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3)
def analyze_speaking(self, speaking_task_id: int, user_id: int):
    """
    Background task to analyze speaking audio using AI
    """
    start_time = time.time()
    task_id = self.request.id
    
    self.update_state(state='PROCESSING', meta={'progress': 10, 'status': 'Loading audio'})
    
    db = SessionLocal()
    
    try:
        # Get speaking task from database
        speaking_task = db.query(SpeakingTask).filter(SpeakingTask.id == speaking_task_id).first()
        if not speaking_task:
            raise Exception(f"Speaking task {speaking_task_id} not found")
        
        # Verify audio file exists
        audio_path = os.path.join(settings.upload_folder, speaking_task.audio_filename)
        if not os.path.exists(audio_path):
            raise Exception(f"Audio file not found: {speaking_task.audio_filename}")
        
        # Create AI request record
        ai_request = AIRequest(
            user_id=user_id,
            request_type="speaking_analysis",
            ai_model="pending",
            status="processing"
        )
        db.add(ai_request)
        db.commit()
        
        self.update_state(state='PROCESSING', meta={'progress': 30, 'status': 'Transcribing audio'})
        
        # Import AI service
        from app.services.sync_ai_service import SyncAIServiceManager
        ai_manager = SyncAIServiceManager()
        
        # Analyze speaking
        analysis_result = ai_manager.analyze_speaking(
            audio_path=audio_path,
            question=speaking_task.question,
            language=speaking_task.language.value if speaking_task.language else "english"
        )
        
        self.update_state(state='PROCESSING', meta={'progress': 80, 'status': 'Saving analysis'})
        
        # Save analysis results
        speaking_analysis = SpeakingAnalysis(
            speaking_task_id=speaking_task_id,
            fluency_coherence=analysis_result["scores"]["fluency_coherence"],
            lexical_resource=analysis_result["scores"]["lexical_resource"],
            grammatical_range=analysis_result["scores"]["grammatical_range"],
            pronunciation=analysis_result["scores"]["pronunciation"],
            overall_band=analysis_result["scores"]["overall_band"],
            speech_rate=analysis_result.get("speech_metrics", {}).get("speech_rate", 0),
            vocabulary_diversity=analysis_result.get("speech_metrics", {}).get("vocabulary_diversity", 0),
            analysis_data=analysis_result["detailed_analysis"],
            ai_model_used=analysis_result.get("model", "ai_service"),
            processing_time=time.time() - start_time,
            confidence_score=analysis_result.get("confidence", 0.8)
        )
        
        db.add(speaking_analysis)
        
        # Update speaking task
        speaking_task.is_analyzed = True
        speaking_task.transcription = analysis_result.get("transcription", "")
        speaking_task.audio_duration = analysis_result.get("audio_duration", 0)
        speaking_task.analyzed_at = datetime.utcnow()
        
        # Update AI request
        ai_request.status = "completed"
        ai_request.ai_model = analysis_result.get("model", "unknown")
        ai_request.total_tokens = analysis_result.get("tokens_used", 0)
        ai_request.cost_usd = analysis_result.get("cost", 0.0)
        ai_request.processing_time = time.time() - start_time
        ai_request.completed_at = datetime.utcnow()
        
        # Update student profile
        student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
        if student_profile:
            student_profile.speaking_sessions += 1
            student_profile.speaking_band = analysis_result["scores"]["overall_band"]
            # Update overall band
            skills = [student_profile.writing_band, student_profile.speaking_band, 
                     student_profile.reading_band, student_profile.listening_band]
            valid_skills = [s for s in skills if s > 0]
            if valid_skills:
                student_profile.overall_band = sum(valid_skills) / len(valid_skills)
        
        db.commit()
        
        self.update_state(state='SUCCESS', meta={'progress': 100, 'status': 'Completed'})
        
        logger.info(f"Speaking task {speaking_task_id} analyzed successfully")
        
        return {
            "status": "completed",
            "speaking_task_id": speaking_task_id,
            "overall_band": analysis_result["scores"]["overall_band"],
            "transcription": analysis_result.get("transcription", ""),
            "processing_time": time.time() - start_time,
            "cost": analysis_result.get("cost", 0.0),
            "ai_service": analysis_result.get("ai_service", "unknown"),
            "task_id": task_id
        }
        
    except Exception as e:
        logger.error(f"Speaking analysis failed for task {speaking_task_id}: {str(e)}")
        
        if 'ai_request' in locals():
            ai_request.status = "failed"
            ai_request.error_message = str(e)
            ai_request.completed_at = datetime.utcnow()
            db.commit()
        
        db.rollback()
        
        # Retry logic
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'progress': 0, 'status': 'Failed'}
        )
        
        raise Exception(f"Speaking analysis failed: {str(e)}")
    
    finally:
        db.close()

@celery_app.task(bind=True)
def generate_curriculum(self, user_id: int, curriculum_request: dict):
    """
    Background task to generate personalized curriculum
    """
    start_time = time.time()
    
    self.update_state(state='PROCESSING', meta={'progress': 20, 'status': 'Analyzing student profile'})
    
    db = SessionLocal()
    
    try:
        # Get student profile
        student_profile = db.query(StudentProfile).filter(StudentProfile.user_id == user_id).first()
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            raise Exception(f"User {user_id} not found")
        
        self.update_state(state='PROCESSING', meta={'progress': 40, 'status': 'Generating curriculum'})
        
        # Import AI service
        from app.services.sync_ai_service import SyncAIServiceManager
        ai_manager = SyncAIServiceManager()
        
        # Prepare student analysis
        student_analysis = {
            "current_level": user.current_level or "A2",
            "overall_band": student_profile.overall_band if student_profile else 4.0,
            "weak_areas": student_profile.weak_areas if student_profile else ["grammar", "vocabulary"],
            "strong_areas": student_profile.focus_areas if student_profile else [],
            "total_assessments": (student_profile.essays_completed + student_profile.speaking_sessions) if student_profile else 0,
            "improvement_rate": 0.0,  # Calculate from historical data
            "language": curriculum_request.get("target_language", "english"),
            "target_band": curriculum_request.get("target_band"),
            "weekly_hours": curriculum_request.get("weekly_hours", 10),
            "timeline_weeks": curriculum_request.get("duration_weeks", 12)
        }
        
        # Generate curriculum
        curriculum_result = ai_manager.generate_curriculum(student_analysis)
        
        self.update_state(state='PROCESSING', meta={'progress': 80, 'status': 'Saving curriculum'})
        
        # Create curriculum record
        from app.models.models import Language
        curriculum = Curriculum(
            name=curriculum_result["curriculum_overview"]["title"],
            description=f"Personalized curriculum for {curriculum_request.get('target_language', 'English')}",
            target_language=Language(curriculum_request.get("target_language", "english").upper()),
            target_level=curriculum_request.get("target_level", "B2"),
            target_band=curriculum_request.get("target_band"),
            duration_weeks=curriculum_request.get("duration_weeks", 12),
            curriculum_data=curriculum_result,
            focus_areas=curriculum_request.get("focus_areas", ["grammar", "vocabulary"]),
            difficulty_progression=curriculum_result.get("difficulty_progression", []),
            created_by_ai=True,
            ai_model_used=curriculum_result.get("model", "ai_service"),
            generation_prompt=json.dumps(student_analysis)
        )
        
        db.add(curriculum)
        db.commit()
        db.refresh(curriculum)
        
        # Update student profile
        if student_profile:
            student_profile.current_curriculum_id = curriculum.id
            student_profile.curriculum_progress = 0.0
            student_profile.focus_areas = curriculum_request.get("focus_areas", [])
            db.commit()
        
        self.update_state(state='SUCCESS', meta={'progress': 100, 'status': 'Curriculum generated'})
        
        logger.info(f"Curriculum generated for user {user_id}")
        
        return {
            "status": "completed",
            "curriculum_id": curriculum.id,
            "curriculum_name": curriculum.name,
            "duration_weeks": curriculum.duration_weeks,
            "processing_time": time.time() - start_time,
            "cost": curriculum_result.get("cost", 0.0)
        }
        
    except Exception as e:
        logger.error(f"Curriculum generation failed for user {user_id}: {str(e)}")
        
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'progress': 0, 'status': 'Failed'}
        )
        
        raise Exception(f"Curriculum generation failed: {str(e)}")
    
    finally:
        db.close()

@celery_app.task
def cleanup_old_files():
    """
    Periodic task to clean up old uploaded files
    """
    import os
    import time
    
    upload_dir = settings.upload_folder
    max_age_days = 30
    max_age_seconds = max_age_days * 24 * 60 * 60
    current_time = time.time()
    
    cleaned_files = 0
    
    try:
        for filename in os.listdir(upload_dir):
            file_path = os.path.join(upload_dir, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getctime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    cleaned_files += 1
                    logger.info(f"Cleaned up old file: {filename}")
        
        logger.info(f"Cleanup completed: {cleaned_files} files removed")
        return {"files_cleaned": cleaned_files}
        
    except Exception as e:
        logger.error(f"File cleanup failed: {str(e)}")
        raise

@celery_app.task
def update_student_progress():
    """
    Periodic task to update student progress metrics
    """
    db = SessionLocal()
    
    try:
        profiles = db.query(StudentProfile).all()
        updated_count = 0
        
        for profile in profiles:
            # Calculate total study time from completed essays and speaking sessions
            total_activities = profile.essays_completed + profile.speaking_sessions
            estimated_hours = total_activities * 0.5  # Estimate 30 minutes per activity
            
            profile.total_study_hours = estimated_hours
            profile.updated_at = datetime.utcnow()
            updated_count += 1
        
        db.commit()
        logger.info(f"Updated progress for {updated_count} student profiles")
        
        return {"profiles_updated": updated_count}
        
    except Exception as e:
        logger.error(f"Progress update failed: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

# Task monitoring functions
def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of a background task
    """
    result = celery_app.AsyncResult(task_id)
    
    if result.state == 'PENDING':
        response = {
            'state': result.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif result.state != 'FAILURE':
        response = {
            'state': result.state,
            'current': result.info.get('progress', 0),
            'total': 100,
            'status': result.info.get('status', '')
        }
        if 'result' in result.info:
            response['result'] = result.info['result']
    else:
        # Something went wrong
        response = {
            'state': result.state,
            'current': 1,
            'total': 1,
            'status': str(result.info),  # This is the exception raised
        }
    
    return response

def cancel_task(task_id: str) -> bool:
    """
    Cancel a running task
    """
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return True
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {str(e)}")
        return False