from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import os
import uuid
from typing import Optional
import json

from app.database import get_db
from app.models.models import User
from app.api.auth.auth import get_current_active_user
from app.services.ai_service import EnhancedFreeAIService

router = APIRouter(prefix="/api/speaking", tags=["Speaking Tasks"])

class SpeakingAnalysisRequest(BaseModel):
    transcription: str
    speaking_time: float
    task_type: str = "general"
    question: str = ""

@router.post("/submit-recording")
async def submit_speaking_recording(
    audio_file: UploadFile = File(...),
    video_file: Optional[UploadFile] = File(None),
    task_type: str = Form("general"),
    question: str = Form(""),
    speaking_time: float = Form(0.0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit audio/video recording for speaking analysis"""
    
    # Validate audio file
    if not audio_file.content_type or not audio_file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="Audio file must be in audio format")
    
    # Generate unique filenames
    audio_extension = audio_file.filename.split('.')[-1] if '.' in audio_file.filename else 'wav'
    unique_audio_filename = f"{uuid.uuid4()}.{audio_extension}"
    audio_path = os.path.join("uploads", unique_audio_filename)
    
    video_path = None
    if video_file:
        video_extension = video_file.filename.split('.')[-1] if '.' in video_file.filename else 'webm'
        unique_video_filename = f"{uuid.uuid4()}.{video_extension}"
        video_path = os.path.join("uploads", unique_video_filename)
    
    # Save files
    os.makedirs("uploads", exist_ok=True)
    
    # Save audio
    with open(audio_path, "wb") as f:
        audio_content = await audio_file.read()
        f.write(audio_content)
    
    # Save video if provided
    if video_file and video_path:
        with open(video_path, "wb") as f:
            video_content = await video_file.read()
            f.write(video_content)
    
    # For demo purposes, we'll simulate transcription
    # In a real application, you would use speech-to-text API
    demo_transcription = f"This is a demo transcription for the speaking task about {question}. The user spoke for {speaking_time} seconds on the topic of {task_type}. In a real application, this would be the actual transcription from the audio file."
    
    return {
        "message": "Recording uploaded successfully",
        "audio_filename": unique_audio_filename,
        "video_filename": video_path.split('/')[-1] if video_path else None,
        "task_type": task_type,
        "question": question,
        "speaking_time": speaking_time,
        "demo_transcription": demo_transcription,
        "status": "uploaded",
        "next_step": "Use the analyze-speaking endpoint to get detailed evaluation"
    }

@router.post("/analyze-speaking")
async def analyze_speaking_performance(
    analysis_request: SpeakingAnalysisRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Analyze speaking performance with comprehensive feedback"""
    
    if not analysis_request.transcription.strip():
        raise HTTPException(status_code=400, detail="Transcription cannot be empty")
    
    # Validate speaking time
    if analysis_request.speaking_time < 30:
        return {
            "message": "Speaking time too short",
            "recommendation": "Try to speak for at least 30 seconds to get accurate analysis",
            "minimum_time": 30,
            "your_time": analysis_request.speaking_time
        }
    
    # Analyze with enhanced AI service
    ai_service = EnhancedFreeAIService()
    evaluation_result = ai_service.evaluate_work(
        content=analysis_request.transcription,
        work_type="speaking"
    )
    
    # Add speaking-specific metrics
    words_per_minute = len(analysis_request.transcription.split()) / (analysis_request.speaking_time / 60) if analysis_request.speaking_time > 0 else 0
    
    # Determine pace feedback
    pace_feedback = "Good pace" if 120 <= words_per_minute <= 180 else \
                   "Too fast - try to slow down" if words_per_minute > 180 else \
                   "Too slow - try to speak more fluently"
    
    evaluation_result["evaluation"]["speaking_metrics"] = {
        "words_per_minute": round(words_per_minute, 1),
        "pace_feedback": pace_feedback,
        "speaking_time": analysis_request.speaking_time,
        "word_count": len(analysis_request.transcription.split())
    }
    
    # Generate specific speaking tips
    speaking_tips = []
    
    if evaluation_result["scores"]["fluency_coherence"] < 6.0:
        speaking_tips.append("Practice speaking on topics for 2-3 minutes daily")
        speaking_tips.append("Record yourself and listen for hesitations")
    
    if evaluation_result["scores"]["lexical_resource"] < 6.0:
        speaking_tips.append("Learn topic-specific vocabulary")
        speaking_tips.append("Practice using new words in context")
    
    if evaluation_result["scores"]["grammatical_range"] < 6.0:
        speaking_tips.append("Practice speaking with complex sentence structures")
        speaking_tips.append("Focus on accurate verb tenses")
    
    evaluation_result["evaluation"]["speaking_tips"] = speaking_tips
    
    return {
        "message": "Speaking analysis completed",
        "user_id": current_user.id,
        "overall_band": evaluation_result["scores"]["overall_band"],
        "evaluation": evaluation_result["evaluation"],
        "improvement_course": evaluation_result["improvement_course"],
        "scores": evaluation_result["scores"],
        "analysis_type": "comprehensive_speaking",
        "cost": 0.0
    }

@router.post("/quick-speaking-test")
async def quick_speaking_test(
    text_input: dict,
    current_user: User = Depends(get_current_active_user)
):
    """Quick speaking test using text input (for demo purposes)"""
    
    content = text_input.get("content", "")
    topic = text_input.get("topic", "general")
    
    if not content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    # Simulate speaking analysis from text
    ai_service = EnhancedFreeAIService()
    evaluation_result = ai_service.evaluate_work(
        content=content,
        work_type="speaking"
    )
    
    # Add demo speaking metrics
    word_count = len(content.split())
    estimated_time = word_count / 2  # Rough estimate: 2 words per second
    
    evaluation_result["evaluation"]["demo_metrics"] = {
        "word_count": word_count,
        "estimated_speaking_time": f"{estimated_time:.1f} seconds",
        "topic": topic,
        "analysis_note": "This is a demo analysis based on text input"
    }
    
    return {
        "message": "Quick speaking test completed",
        "overall_band": evaluation_result["scores"]["overall_band"],
        "evaluation": evaluation_result["evaluation"],
        "improvement_course": evaluation_result["improvement_course"],
        "scores": evaluation_result["scores"],
        "analysis_type": "quick_speaking_demo"
    }

@router.get("/speaking-topics")
async def get_speaking_topics(
    level: str = "intermediate",
    current_user: User = Depends(get_current_active_user)
):
    """Get speaking practice topics based on user level"""
    
    topics = {
        "beginner": [
            "Describe your hometown",
            "Talk about your favorite hobby",
            "Describe your daily routine",
            "Talk about your family",
            "Describe your favorite food"
        ],
        "intermediate": [
            "Discuss the advantages and disadvantages of social media",
            "Talk about environmental problems in your city",
            "Describe a memorable trip you took",
            "Discuss the importance of learning foreign languages",
            "Talk about changes in your country over the last decade"
        ],
        "advanced": [
            "Analyze the impact of technology on modern relationships",
            "Discuss the role of government in addressing climate change",
            "Evaluate the effectiveness of online education",
            "Examine the cultural differences between generations",
            "Assess the influence of globalization on local traditions"
        ]
    }
    
    level_topics = topics.get(level, topics["intermediate"])
    
    return {
        "level": level,
        "topics": level_topics,
        "instructions": {
            "preparation_time": "1 minute to think about the topic",
            "speaking_time": "2-3 minutes for main response",
            "follow_up": "Be prepared for follow-up questions",
            "tips": [
                "Structure your answer with clear points",
                "Use specific examples and details",
                "Speak clearly and at a natural pace",
                "Don't worry about perfect grammar - focus on communication"
            ]
        },
        "evaluation_criteria": [
            "Fluency and Coherence",
            "Lexical Resource (Vocabulary)",
            "Grammatical Range and Accuracy",
            "Pronunciation"
        ]
    }

@router.get("/speaking-progress")
async def get_speaking_progress(
    current_user: User = Depends(get_current_active_user)
):
    """Get user's speaking progress (demo data for now)"""
    
    # In a real application, this would fetch from database
    demo_progress = {
        "total_speaking_sessions": 12,
        "average_score": 6.2,
        "improvement_trend": "+0.8 points over last month",
        "skill_breakdown": {
            "fluency_coherence": {"current": 6.0, "trend": "+0.5"},
            "lexical_resource": {"current": 6.5, "trend": "+0.3"},
            "grammatical_range": {"current": 6.0, "trend": "+0.7"},
            "pronunciation": {"current": 6.3, "trend": "+0.2"}
        },
        "recent_topics": [
            {"topic": "Environmental Issues", "score": 6.5, "date": "2024-01-15"},
            {"topic": "Technology in Education", "score": 6.0, "date": "2024-01-12"},
            {"topic": "Cultural Differences", "score": 6.8, "date": "2024-01-10"}
        ],
        "next_goals": [
            "Improve fluency by practicing daily speaking",
            "Expand vocabulary in academic topics",
            "Work on complex sentence structures"
        ],
        "recommended_practice": {
            "daily_time": "15-20 minutes",
            "focus_areas": ["Fluency", "Grammar"],
            "practice_methods": [
                "Record yourself speaking on different topics",
                "Practice with speaking partners",
                "Listen to native speakers and imitate"
            ]
        }
    }
    
    return {
        "user_id": current_user.id,
        "progress": demo_progress,
        "recommendations": {
            "next_session": "Try speaking about 'Future of Work' topic",
            "skill_focus": "Work on grammatical range and accuracy",
            "practice_tip": "Record yourself and listen for areas to improve"
        }
    }

@router.post("/speaking-feedback")
async def provide_speaking_feedback(
    feedback_data: dict,
    current_user: User = Depends(get_current_active_user)
):
    """Provide detailed feedback on specific speaking aspects"""
    
    transcription = feedback_data.get("transcription", "")
    focus_area = feedback_data.get("focus_area", "general")  # fluency, vocabulary, grammar, pronunciation
    
    if not transcription.strip():
        raise HTTPException(status_code=400, detail="Transcription required for feedback")
    
    # Generate focused feedback
    ai_service = EnhancedFreeAIService()
    
    feedback = {
        "focus_area": focus_area,
        "general_feedback": [],
        "specific_suggestions": [],
        "practice_exercises": []
    }
    
    if focus_area == "fluency":
        feedback["general_feedback"] = [
            "Focus on maintaining steady speech flow",
            "Use natural pauses between ideas",
            "Practice speaking without excessive hesitation"
        ]
        feedback["specific_suggestions"] = [
            "Practice speaking on topics for 2-3 minutes daily",
            "Record yourself and identify hesitation patterns",
            "Use filler words sparingly (um, uh, like)"
        ]
        feedback["practice_exercises"] = [
            "Daily 5-minute monologues on various topics",
            "Shadowing exercises with native speakers",
            "Timed speaking practice with increasing duration"
        ]
    
    elif focus_area == "vocabulary":
        feedback["general_feedback"] = [
            "Expand range of vocabulary usage",
            "Use more precise and varied expressions",
            "Practice topic-specific vocabulary"
        ]
        feedback["specific_suggestions"] = [
            "Learn 5-10 new words daily and use them in context",
            "Practice paraphrasing common expressions",
            "Study collocations and natural word combinations"
        ]
        feedback["practice_exercises"] = [
            "Vocabulary journals with example sentences",
            "Synonym and antonym practice",
            "Topic-based vocabulary building"
        ]
    
    elif focus_area == "grammar":
        feedback["general_feedback"] = [
            "Increase variety of sentence structures",
            "Focus on accurate verb tenses",
            "Practice complex grammatical forms"
        ]
        feedback["specific_suggestions"] = [
            "Practice using conditional sentences",
            "Work on relative clauses in speech",
            "Focus on accurate present/past/future forms"
        ]
        feedback["practice_exercises"] = [
            "Daily complex sentence construction",
            "Grammar pattern drills",
            "Sentence combining exercises"
        ]
    
    # Add content-specific analysis
    word_count = len(transcription.split())
    sentence_count = len([s for s in transcription.split('.') if s.strip()])
    
    feedback["content_analysis"] = {
        "word_count": word_count,
        "sentence_count": sentence_count,
        "average_sentence_length": round(word_count / max(sentence_count, 1), 1),
        "complexity_level": "Good" if word_count > 100 else "Needs development"
    }
    
    return {
        "message": f"Focused feedback provided for {focus_area}",
        "feedback": feedback,
        "improvement_timeline": {
            "short_term": "1-2 weeks: Focus on daily practice",
            "medium_term": "1-2 months: Noticeable improvement",
            "long_term": "3-6 months: Significant skill development"
        }
    }