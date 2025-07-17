import openai
import json
import time
import asyncio
from typing import Dict, Any, Optional
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import structlog
from config.settings import settings

logger = structlog.get_logger()

class AIServiceError(Exception):
    """Custom exception for AI service errors"""
    pass

class RateLimitError(AIServiceError):
    """Rate limit exceeded"""
    pass

class OpenAIService:
    """Production-ready OpenAI service with error handling and retries"""
    
    def __init__(self):
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured")
            self.client = None
        else:
            self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError))
    )
    async def grade_essay(self, content: str, task_type: str = "general", word_count: int = 0) -> Dict[str, Any]:
        """Grade an essay using GPT-4 with retry logic"""
        
        if not self.client:
            logger.warning("OpenAI client not available, using fallback")
            return self._get_fallback_grading(content, task_type, word_count)
        
        start_time = time.time()
        
        try:
            prompt = self._build_grading_prompt(content, task_type, word_count)
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4-1106-preview",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert IELTS examiner. Provide accurate, detailed feedback on essays according to official IELTS band descriptors. Always return valid JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            processing_time = time.time() - start_time
            
            try:
                result = json.loads(response.choices[0].message.content)
            except json.JSONDecodeError as e:
                logger.error("Failed to parse OpenAI response", error=str(e))
                return self._get_fallback_grading(content, task_type, word_count)
            
            # Add metadata
            result["tokens_used"] = response.usage.total_tokens
            result["cost"] = self._calculate_cost(response.usage.total_tokens)
            result["processing_time"] = processing_time
            result["ai_model"] = "gpt-4-1106-preview"
            
            logger.info("Essay graded successfully", 
                       tokens=response.usage.total_tokens,
                       cost=result["cost"],
                       processing_time=processing_time)
            
            return result
            
        except openai.RateLimitError as e:
            logger.error("OpenAI rate limit exceeded", error=str(e))
            raise RateLimitError("AI service temporarily unavailable due to rate limits")
        
        except openai.APIError as e:
            logger.error("OpenAI API error", error=str(e))
            return self._get_fallback_grading(content, task_type, word_count)
        
        except Exception as e:
            logger.error("Unexpected error in essay grading", error=str(e))
            return self._get_fallback_grading(content, task_type, word_count)
    
    def _get_fallback_grading(self, content: str, task_type: str, word_count: int) -> Dict[str, Any]:
        """Fallback grading when OpenAI is unavailable"""
        from app.services.free_ai_service import FreeAIService
        
        logger.info("Using fallback AI grading service")
        
        fallback_service = FreeAIService()
        result = fallback_service.grade_essay(content, task_type, word_count)
        
        # Add fallback metadata
        result["ai_model"] = "fallback_rule_based"
        result["is_fallback"] = True
        
        return result
    
    def _build_grading_prompt(self, content: str, task_type: str, word_count: int) -> str:
        """Build the grading prompt for GPT-4"""
        
        task_info = {
            "task1": "IELTS Academic Task 1 (150 words minimum): Describing graphs, charts, or diagrams",
            "task2": "IELTS Academic Task 2 (250 words minimum): Essay responding to a point of view, argument or problem",
            "general": "General Writing Task: Purpose, tone, and format appropriateness"
        }
        
        task_description = task_info.get(task_type, task_info["general"])
        
        return f"""
Grade this {task_type} essay according to IELTS band descriptors (0-9 scale):

Task Type: {task_description}
Word Count: {word_count} words

Essay Content:
{content}

Provide your assessment in this EXACT JSON format:
{{
    "scores": {{
        "task_achievement": 6.5,
        "coherence_cohesion": 7.0,
        "lexical_resource": 6.0,
        "grammar_accuracy": 6.5,
        "overall_band": 6.5
    }},
    "feedback": {{
        "strengths": [
            "Clear thesis statement",
            "Good use of examples"
        ],
        "improvements": [
            "More complex sentence structures needed",
            "Some vocabulary repetition"
        ],
        "suggestions": [
            "Use more linking words between ideas",
            "Develop paragraphs more fully"
        ],
        "detailed_analysis": {{
            "task_achievement": "The essay addresses the question but could develop ideas more fully...",
            "coherence_cohesion": "Good overall structure but some paragraphs lack clear topic sentences...",
            "lexical_resource": "Adequate vocabulary range but some imprecise word choices...",
            "grammar_accuracy": "Generally accurate but limited range of complex structures..."
        }}
    }}
}}

Use increments of 0.5 (e.g., 6.0, 6.5, 7.0). Be precise and constructive in feedback.
"""
    
    def _calculate_cost(self, tokens: int) -> float:
        """Calculate approximate cost of API call"""
        # GPT-4 Turbo pricing: $0.01 per 1K input tokens, $0.03 per 1K output tokens
        # Approximate 70/30 split for input/output
        input_tokens = int(tokens * 0.7)
        output_tokens = int(tokens * 0.3)
        
        input_cost = input_tokens * 0.01 / 1000
        output_cost = output_tokens * 0.03 / 1000
        
        return round(input_cost + output_cost, 4)

class WhisperService:
    """Service for audio transcription using Whisper"""
    
    def __init__(self):
        if not settings.openai_api_key:
            logger.warning("OpenAI API key not configured for Whisper")
            self.client = None
        else:
            self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError))
    )
    async def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio file using Whisper"""
        
        if not self.client:
            raise AIServiceError("Whisper service not available")
        
        start_time = time.time()
        
        try:
            with open(audio_path, "rb") as audio_file:
                response = await asyncio.to_thread(
                    self.client.audio.transcriptions.create,
                    model="whisper-1",
                    file=audio_file,
                    response_format="json"
                )
            
            processing_time = time.time() - start_time
            
            result = {
                "text": response.text,
                "processing_time": processing_time,
                "ai_model": "whisper-1"
            }
            
            logger.info("Audio transcribed successfully", 
                       text_length=len(response.text),
                       processing_time=processing_time)
            
            return result
            
        except openai.RateLimitError as e:
            logger.error("Whisper rate limit exceeded", error=str(e))
            raise RateLimitError("Transcription service temporarily unavailable")
        
        except Exception as e:
            logger.error("Audio transcription failed", error=str(e))
            raise AIServiceError(f"Transcription failed: {str(e)}")
    
    async def analyze_speaking(self, transcription: str, audio_duration: float, 
                              task_type: str, question: str) -> Dict[str, Any]:
        """Analyze speaking performance"""
        
        if not self.client:
            return self._get_fallback_speaking_analysis(transcription, audio_duration)
        
        try:
            prompt = self._build_speaking_prompt(transcription, audio_duration, task_type, question)
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-4-1106-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert IELTS speaking examiner. Analyze speaking transcriptions and provide detailed feedback."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["tokens_used"] = response.usage.total_tokens
            result["cost"] = self._calculate_cost(response.usage.total_tokens)
            
            return result
            
        except Exception as e:
            logger.error("Speaking analysis failed", error=str(e))
            return self._get_fallback_speaking_analysis(transcription, audio_duration)
    
    def _get_fallback_speaking_analysis(self, transcription: str, audio_duration: float) -> Dict[str, Any]:
        """Fallback speaking analysis"""
        word_count = len(transcription.split())
        words_per_minute = (word_count / audio_duration * 60) if audio_duration > 0 else 0
        
        # Simple analysis based on metrics
        fluency_score = min(9.0, max(4.0, 5.0 + (words_per_minute - 120) * 0.02))
        
        return {
            "scores": {
                "fluency_coherence": round(fluency_score, 1),
                "lexical_resource": 6.0,
                "grammatical_range": 6.0,
                "pronunciation": 6.0,
                "overall_band": round((fluency_score + 18) / 4, 1)
            },
            "feedback": {
                "strengths": ["Speech recorded successfully"],
                "improvements": ["Continue practicing speaking"],
                "analysis": {
                    "word_count": word_count,
                    "duration": audio_duration,
                    "words_per_minute": round(words_per_minute, 1)
                }
            },
            "is_fallback": True
        }
    
    def _build_speaking_prompt(self, transcription: str, duration: float, task_type: str, question: str) -> str:
        """Build speaking analysis prompt"""
        return f"""
Analyze this IELTS speaking performance:

Task Type: {task_type}
Question: {question}
Duration: {duration} seconds
Transcription: {transcription}

Provide analysis in this JSON format:
{{
    "scores": {{
        "fluency_coherence": 7.0,
        "lexical_resource": 6.5,
        "grammatical_range": 6.0,
        "pronunciation": 6.5,
        "overall_band": 6.5
    }},
    "feedback": {{
        "strengths": ["Natural speech flow", "Good vocabulary range"],
        "improvements": ["More complex grammar", "Clearer pronunciation"],
        "suggestions": ["Practice linking words", "Work on intonation"]
    }}
}}
"""