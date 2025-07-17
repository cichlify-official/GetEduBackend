import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

try:
    import openai
    from openai import OpenAI
    OPENAI_NEW_VERSION = True
except ImportError:
    import openai
    OPENAI_NEW_VERSION = False

from config.settings import settings

logger = logging.getLogger(__name__)

class EnhancedAIService:
    """Comprehensive AI service for all language skills - Compatible with multiple OpenAI versions"""
    
    def __init__(self):
        if OPENAI_NEW_VERSION and settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)
            self.model = "gpt-4"
        elif settings.openai_api_key:
            openai.api_key = settings.openai_api_key
            self.client = openai
            self.model = "gpt-4"
        else:
            self.client = None
            self.model = None
        
    async def grade_essay(self, content: str, task_type: str = "general", word_count: int = 0) -> Dict[str, Any]:
        """Grade an essay using GPT-4 with IELTS standards"""
        
        if not self.client:
            return self._fallback_essay_response("No OpenAI API key configured")
        
        prompt = self._build_essay_prompt(content, task_type, word_count)
        
        try:
            if OPENAI_NEW_VERSION:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": """You are an expert IELTS examiner with 20+ years of experience. 
                            You provide accurate, detailed feedback according to official IELTS band descriptors.
                            Your feedback helps students improve their writing skills effectively.
                            Always return valid JSON with detailed analysis and actionable recommendations."""
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
                
                result = json.loads(response.choices[0].message.content)
                result["tokens_used"] = response.usage.total_tokens
                result["cost"] = self._calculate_cost(response.usage.total_tokens)
                
            else:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: openai.ChatCompletion.create(
                        model=self.model,
                        messages=[
                            {
                                "role": "system",
                                "content": """You are an expert IELTS examiner with 20+ years of experience. 
                                You provide accurate, detailed feedback according to official IELTS band descriptors.
                                Your feedback helps students improve their writing skills effectively.
                                Always return valid JSON with detailed analysis and actionable recommendations."""
                            },
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.3,
                        max_tokens=2000
                    )
                )
                
                result = json.loads(response.choices[0].message.content)
                result["tokens_used"] = response.usage.total_tokens
                result["cost"] = self._calculate_cost(response.usage.total_tokens)
            
            return result
            
        except Exception as e:
            logger.error(f"Essay grading failed: {str(e)}")
            return self._fallback_essay_response(e)
    
    def _build_essay_prompt(self, content: str, task_type: str, word_count: int) -> str:
        """Build essay grading prompt"""
        
        task_info = {
            "task1": "IELTS Academic Task 1 (150 words minimum): Describing graphs, charts, or diagrams",
            "task2": "IELTS Academic Task 2 (250 words minimum): Essay responding to a point of view, argument or problem",
            "general": "General Writing Task: Purpose, tone, and format appropriateness"
        }
        
        return f"""
        Grade this {task_type} essay according to IELTS band descriptors (0-9 scale):
        
        Task Type: {task_info.get(task_type, task_info['general'])}
        Word Count: {word_count} words
        
        Essay Content:
        {content}
        
        Provide assessment in this JSON format:
        {{
            "scores": {{
                "task_achievement": 6.5,
                "coherence_cohesion": 7.0,
                "lexical_resource": 6.0,
                "grammar_accuracy": 6.5,
                "overall_band": 6.5
            }},
            "feedback": {{
                "strengths": ["Clear thesis statement", "Good use of examples"],
                "improvements": ["More complex sentence structures needed", "Some vocabulary repetition"],
                "suggestions": ["Use more linking words between ideas", "Develop paragraphs more fully"]
            }},
            "detailed_analysis": {{
                "task_achievement": "The essay addresses the question but could develop ideas more fully...",
                "coherence_cohesion": "Good overall structure but some paragraphs lack clear topic sentences...",
                "lexical_resource": "Adequate vocabulary range but some imprecise word choices...",
                "grammar_accuracy": "Generally accurate but limited range of complex structures..."
            }},
            "lesson_recommendations": [
                {{
                    "skill": "paragraph_development",
                    "priority": "high",
                    "activities": ["Practice expanding main ideas with examples", "Use paragraph templates"]
                }}
            ]
        }}
        """
    
    def _calculate_cost(self, tokens: int) -> float:
        """Calculate approximate cost of API call"""
        return tokens * 0.01 / 1000  # Approximate GPT-4 pricing
    
    def _fallback_essay_response(self, error: Exception) -> Dict[str, Any]:
        """Fallback response for essay grading"""
        return {
            "scores": {
                "task_achievement": 6.0,
                "coherence_cohesion": 6.0,
                "lexical_resource": 6.0,
                "grammar_accuracy": 6.0,
                "overall_band": 6.0
            },
            "feedback": {
                "strengths": ["Essay submitted successfully"],
                "improvements": ["AI grading service unavailable - add OpenAI API key"],
                "suggestions": ["Please add your OpenAI API key to enable real AI grading"]
            },
            "detailed_analysis": {
                "task_achievement": "Demo grading - add OpenAI key for real analysis",
                "coherence_cohesion": "Demo grading - add OpenAI key for real analysis",
                "lexical_resource": "Demo grading - add OpenAI key for real analysis",
                "grammar_accuracy": "Demo grading - add OpenAI key for real analysis"
            },
            "lesson_recommendations": [],
            "error": str(error),
            "demo_mode": True
        }

class WhisperService:
    """Service for audio transcription - Compatible with multiple OpenAI versions"""
    
    def __init__(self):
        if OPENAI_NEW_VERSION and settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)
        elif settings.openai_api_key:
            openai.api_key = settings.openai_api_key
            self.client = openai
        else:
            self.client = None
    
    async def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe audio file using Whisper"""
        
        if not self.client:
            return {
                "text": "Transcription failed - no OpenAI API key configured",
                "duration": 0,
                "error": "No API key"
            }
        
        try:
            if OPENAI_NEW_VERSION:
                with open(audio_file_path, "rb") as audio_file:
                    transcript = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        response_format="text"
                    )
                
                return {
                    "text": transcript,
                    "duration": 0,
                    "language": 'en'
                }
            else:
                with open(audio_file_path, "rb") as audio_file:
                    transcript = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: openai.Audio.transcribe(
                            model="whisper-1",
                            file=audio_file,
                            response_format="text"
                        )
                    )
                
                return {
                    "text": transcript,
                    "duration": 0,
                    "language": 'en'
                }
            
        except Exception as e:
            logger.error(f"Audio transcription failed: {str(e)}")
            return {
                "text": "Transcription failed - please try again",
                "duration": 0,
                "error": str(e)
            }
