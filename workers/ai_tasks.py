import asyncio
from celery import current_task
from datetime import datetime
import json
import time
from typing import Dict, Any

from workers.celery_app import celery_app
from app.database import SessionLocal
from app.models.models import Essay, EssayGrading, SpeakingTask, SpeakingAnalysis, AIRequest
from config.settings import settings

# AI Services
from app.services.ai_service import OpenAIService, WhisperService

@celery_app.task(bind=True)
def grade_essay(self, essay_id: int, user_id: int):
    """
    Background task to grade an essay using AI
    
    This runs in a separate process from FastAPI, so it won't block the API
    Think of this as sending the essay to a robot teacher for grading
    """
    start_time = time.time()
    
    # Update task status
    self.update_state(state='PROCESSING', meta={'progress': 0})
    
    # Get database session (synchronous for Celery)
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
            ai_model="gpt-4",
            status="processing"
        )
        db.add(ai_request)
        db.commit()
        
        self.update_state(state='PROCESSING', meta={'progress': 25})
        
        # Initialize AI service
        ai_service = OpenAIService()
        
        # Grade the essay
        grading_result = ai_service.grade_essay(
            content=essay.content,
            task_type=essay.task_type,
            word_count=essay.word_count
        )
        
        self.update_state(state='PROCESSING', meta={'progress': 75})
        
        # Save grading results
        essay_grading = EssayGrading(
            essay_id=essay_id,
            task_achievement=grading_result["scores"]["task_achievement"],
            coherence_cohesion=grading_result["scores"]["coherence_cohesion"],
            lexical_resource=grading_result["scores"]["lexical_resource"],
            grammar_accuracy=grading_result["scores"]["grammar_accuracy"],
            overall_band=grading_result["scores"]["overall_band"],
            feedback=grading_result["feedback"],
            ai_model_used="gpt-4",
            processing_time=time.time() - start_time
        )
        
        db.add(essay_grading)
        
        # Update essay status
        essay.is_graded = True
        essay.overall_score = grading_result["scores"]["overall_band"]
        essay.graded_at = datetime.utcnow()
        
        # Update AI request
        ai_request.status = "completed"
        ai_request.tokens_used = grading_result.get("tokens_used", 0)
        ai_request.cost = grading_result.get("cost", 0.0)
        ai_request.completed_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "status": "completed",
            "essay_id": essay_id,
            "overall_band": grading_result["scores"]["overall_band"],
            "processing_time": time.time() - start_time
        }
        
    except Exception as e:
        # Handle errors gracefully
        if 'ai_request' in locals():
            ai_request.status = "failed"
            ai_request.error_message = str(e)
            ai_request.completed_at = datetime.utcnow()
            db.commit()
        
        db.rollback()
        raise Exception(f"Essay grading failed: {str(e)}")
    
    finally:
        db.close()

@celery_app.task(bind=True)
def analyze_speaking(self, speaking_task_id: int, user_id: int):
    """
    Background task to analyze speaking audio using AI
    
    This transcribes audio and analyzes speaking skills
    """
    start_time = time.time()
    
    # Update task status
    self.update_state(state='PROCESSING', meta={'progress': 0})
    
    db = SessionLocal()
    
    try:
        # Get speaking task from database
        speaking_task = db.query(SpeakingTask).filter(SpeakingTask.id == speaking_task_id).first()
        if not speaking_task:
            raise Exception(f"Speaking task {speaking_task_id} not found")
        
        # Create AI request record
        ai_request = AIRequest(
            user_id=user_id,
            request_type="speaking_analysis",
            ai_model="whisper-1",
            status="processing"
        )
        db.add(ai_request)
        db.commit()
        
        self.update_state(state='PROCESSING', meta={'progress': 20})
        
        # Initialize AI services
        whisper_service = WhisperService()
        openai_service = OpenAIService()
        
        # Step 1: Transcribe audio
        audio_path = f"{settings.upload_folder}/{speaking_task.audio_filename}"
        transcription_result = whisper_service.transcribe_audio(audio_path)
        
        self.update_state(state='PROCESSING', meta={'progress': 50})
        
        # Step 2: Analyze speaking skills
        analysis_result = openai_service.analyze_speaking(
            transcription=transcription_result["text"],
            audio_duration=transcription_result.get("duration", 0),
            task_type=speaking_task.task_type,
            question=speaking_task.question
        )
        
        self.update_state(state='PROCESSING', meta={'progress': 80})
        
        # Save analysis results
        speaking_analysis = SpeakingAnalysis(
            speaking_task_id=speaking_task_id,
            fluency_coherence=analysis_result["scores"]["fluency_coherence"],
            lexical_resource=analysis_result["scores"]["lexical_resource"],
            grammatical_range=analysis_result["scores"]["grammatical_range"],
            pronunciation=analysis_result["scores"]["pronunciation"],
            overall_band=analysis_result["scores"]["overall_band"],
            analysis_data=analysis_result["feedback"],
            ai_model_used="gpt-4",
            processing_time=time.time() - start_time
        )
        
        db.add(speaking_analysis)
        
        # Update speaking task
        speaking_task.is_analyzed = True
        speaking_task.transcription = transcription_result["text"]
        speaking_task.audio_duration = transcription_result.get("duration", 0)
        speaking_task.analyzed_at = datetime.utcnow()
        
        # Update AI request
        ai_request.status = "completed"
        ai_request.tokens_used = analysis_result.get("tokens_used", 0)
        ai_request.cost = analysis_result.get("cost", 0.0)
        ai_request.completed_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "status": "completed",
            "speaking_task_id": speaking_task_id,
            "overall_band": analysis_result["scores"]["overall_band"],
            "transcription": transcription_result["text"],
            "processing_time": time.time() - start_time
        }
        
    except Exception as e:
        if 'ai_request' in locals():
            ai_request.status = "failed"
            ai_request.error_message = str(e)
            ai_request.completed_at = datetime.utcnow()
            db.commit()
        
        db.rollback()
        raise Exception(f"Speaking analysis failed: {str(e)}")
    
    finally:
        db.close()

# Task monitoring functions
def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of a background task
    """
    result = celery_app.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "info": result.info,
        "traceback": result.traceback if result.failed() else None
    }
