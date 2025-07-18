import openai
import json
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import aiohttp
from abc import ABC, abstractmethod
import whisper
import torch
from transformers import pipeline, T5ForConditionalGeneration, T5Tokenizer
import numpy as np
import re
from config.settings import settings

logger = logging.getLogger(__name__)

class AIServiceError(Exception):
    """Custom exception for AI service errors"""
    pass

class BaseAIService(ABC):
    """Abstract base class for AI services"""
    
    @abstractmethod
    async def grade_essay(self, content: str, task_type: str, language: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def analyze_speaking(self, audio_path: str, question: str, language: str) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def generate_curriculum(self, student_profile: Dict[str, Any]) -> Dict[str, Any]:
        pass

class OpenAIService(BaseAIService):
    """Primary AI service using OpenAI GPT-4 and Whisper"""
    
    def __init__(self):
        if not settings.openai_api_key:
            raise AIServiceError("OpenAI API key not configured")
        
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.max_retries = 3
        self.timeout = 30
    
    async def _make_openai_request(self, **kwargs) -> Any:
        """Make OpenAI API request with retry logic"""
        for attempt in range(self.max_retries):
            try:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(**kwargs),
                    timeout=self.timeout
                )
                return response
            except asyncio.TimeoutError:
                logger.warning(f"OpenAI timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    raise AIServiceError("OpenAI request timed out")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except openai.RateLimitError:
                logger.warning(f"OpenAI rate limit hit on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    raise AIServiceError("OpenAI rate limit exceeded")
                await asyncio.sleep(5 * (attempt + 1))
            except Exception as e:
                logger.error(f"OpenAI error on attempt {attempt + 1}: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise AIServiceError(f"OpenAI request failed: {str(e)}")
                await asyncio.sleep(1)
    
    async def grade_essay(self, content: str, task_type: str = "task2", language: str = "english") -> Dict[str, Any]:
        """Grade essay using GPT-4 with detailed IELTS criteria"""
        start_time = time.time()
        
        prompt = self._build_essay_grading_prompt(content, task_type, language)
        
        try:
            response = await self._make_openai_request(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert IELTS examiner specializing in {language.title()} language assessment. Provide accurate, detailed feedback according to official IELTS band descriptors. Always return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result.update({
                "tokens_used": response.usage.total_tokens,
                "cost": self._calculate_cost(response.usage.total_tokens, "gpt-4"),
                "processing_time": time.time() - start_time,
                "ai_service": "openai",
                "model": "gpt-4",
                "confidence": 0.95  # High confidence for GPT-4
            })
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI essay grading failed: {str(e)}")
            raise AIServiceError(f"Essay grading failed: {str(e)}")
    
    async def analyze_speaking(self, audio_path: str, question: str, language: str = "english") -> Dict[str, Any]:
        """Analyze speaking using Whisper + GPT-4"""
        start_time = time.time()
        
        try:
            # Step 1: Transcribe audio with Whisper
            with open(audio_path, "rb") as audio_file:
                transcription = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )
            
            # Step 2: Analyze transcription with GPT-4
            analysis_prompt = self._build_speaking_analysis_prompt(
                transcription.text, question, language, transcription.duration
            )
            
            response = await self._make_openai_request(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert IELTS speaking examiner for {language.title()}. Analyze speaking performance according to IELTS criteria. Return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                temperature=0.2,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result.update({
                "transcription": transcription.text,
                "audio_duration": transcription.duration,
                "tokens_used": response.usage.total_tokens,
                "cost": self._calculate_cost(response.usage.total_tokens, "gpt-4") + 0.006,  # Whisper cost
                "processing_time": time.time() - start_time,
                "ai_service": "openai",
                "model": "whisper+gpt-4",
                "confidence": 0.90
            })
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI speaking analysis failed: {str(e)}")
            raise AIServiceError(f"Speaking analysis failed: {str(e)}")
    
    async def generate_curriculum(self, student_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized curriculum using GPT-4"""
        start_time = time.time()
        
        prompt = self._build_curriculum_prompt(student_profile)
        
        try:
            response = await self._make_openai_request(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert language learning curriculum designer. Create detailed, personalized learning plans based on student profiles. Return structured JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=3000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result.update({
                "tokens_used": response.usage.total_tokens,
                "cost": self._calculate_cost(response.usage.total_tokens, "gpt-4"),
                "processing_time": time.time() - start_time,
                "ai_service": "openai",
                "model": "gpt-4",
                "generated_at": datetime.utcnow().isoformat()
            })
            
            return result
            
        except Exception as e:
            logger.error(f"OpenAI curriculum generation failed: {str(e)}")
            raise AIServiceError(f"Curriculum generation failed: {str(e)}")
    
    def _build_essay_grading_prompt(self, content: str, task_type: str, language: str) -> str:
        word_count = len(content.split())
        
        task_descriptions = {
            "task1": "IELTS Academic Task 1 (150+ words): Describing visual information",
            "task2": "IELTS Academic Task 2 (250+ words): Argumentative essay",
            "general": "IELTS General Training: Formal/informal letter or essay"
        }
        
        return f"""
Grade this {language.title()} {task_type} essay according to IELTS band descriptors (0-9 scale):

Task: {task_descriptions.get(task_type, 'General writing task')}
Word Count: {word_count} words
Language: {language.title()}

Essay:
{content}

Provide assessment in this EXACT JSON format:
{{
    "scores": {{
        "task_achievement": 6.5,
        "coherence_cohesion": 7.0,
        "lexical_resource": 6.0,
        "grammar_accuracy": 6.5,
        "overall_band": 6.5
    }},
    "detailed_feedback": {{
        "task_achievement": "Detailed analysis of how well the task was addressed...",
        "coherence_cohesion": "Analysis of organization and logical flow...",
        "lexical_resource": "Assessment of vocabulary range and accuracy...",
        "grammar_accuracy": "Evaluation of grammatical range and accuracy..."
    }},
    "error_analysis": {{
        "grammar_errors": ["Error 1 with correction", "Error 2 with correction"],
        "vocabulary_issues": ["Issue 1 with suggestion", "Issue 2 with suggestion"],
        "spelling_mistakes": ["Mistake 1", "Mistake 2"]
    }},
    "improvement_suggestions": [
        "Specific suggestion 1",
        "Specific suggestion 2",
        "Specific suggestion 3"
    ],
    "estimated_study_focus": ["grammar", "vocabulary", "task_response"]
}}

Use 0.5 increments (6.0, 6.5, 7.0). Be precise and constructive.
"""
    
    def _build_speaking_analysis_prompt(self, transcription: str, question: str, language: str, duration: float) -> str:
        word_count = len(transcription.split())
        words_per_minute = (word_count / duration * 60) if duration > 0 else 0
        
        return f"""
Analyze this {language.title()} IELTS speaking response according to band descriptors:

Question: {question}
Duration: {duration:.1f} seconds
Speaking Rate: {words_per_minute:.1f} words/minute
Language: {language.title()}

Transcription:
{transcription}

Provide analysis in this EXACT JSON format:
{{
    "scores": {{
        "fluency_coherence": 6.5,
        "lexical_resource": 6.0,
        "grammatical_range": 6.5,
        "pronunciation": 6.0,
        "overall_band": 6.0
    }},
    "detailed_analysis": {{
        "fluency_coherence": "Analysis of speech flow, hesitations, and coherence...",
        "lexical_resource": "Assessment of vocabulary range and appropriateness...",
        "grammatical_range": "Evaluation of grammar complexity and accuracy...",
        "pronunciation": "Analysis of clarity, stress, and intonation..."
    }},
    "speech_metrics": {{
        "speech_rate": {words_per_minute:.1f},
        "pause_frequency": "estimate",
        "vocabulary_diversity": "calculated ratio",
        "grammar_complexity": "assessment"
    }},
    "improvement_areas": [
        "Specific area 1 with suggestions",
        "Specific area 2 with suggestions"
    ],
    "pronunciation_feedback": [
        "Specific pronunciation point 1",
        "Specific pronunciation point 2"
    ]
}}
"""
    
    def _build_curriculum_prompt(self, student_profile: Dict[str, Any]) -> str:
        return f"""
Create a personalized language learning curriculum based on this student profile:

Current Level: {student_profile.get('current_level', 'Unknown')}
Target Band: {student_profile.get('target_band', 'Not specified')}
Language: {student_profile.get('language', 'English')}
Weak Areas: {student_profile.get('weak_areas', [])}
Study Hours Available: {student_profile.get('weekly_hours', 10)} hours/week
Timeline: {student_profile.get('timeline_weeks', 12)} weeks

Current Scores:
- Speaking: {student_profile.get('speaking_band', 0)}
- Writing: {student_profile.get('writing_band', 0)}
- Reading: {student_profile.get('reading_band', 0)}
- Listening: {student_profile.get('listening_band', 0)}

Provide curriculum in this EXACT JSON format:
{{
    "curriculum_overview": {{
        "title": "Personalized Curriculum Name",
        "duration_weeks": 12,
        "target_improvement": "+1.0 band score",
        "focus_areas": ["speaking", "grammar", "vocabulary"]
    }},
    "weekly_plan": [
        {{
            "week": 1,
            "theme": "Foundation Building",
            "goals": ["Goal 1", "Goal 2"],
            "lessons": [
                {{
                    "day": 1,
                    "topic": "Grammar Basics",
                    "activities": ["Activity 1", "Activity 2"],
                    "duration_minutes": 60,
                    "homework": "Practice exercises"
                }}
            ],
            "assessment": "Week 1 speaking test",
            "expected_progress": "0.1 band improvement"
        }}
    ],
    "resources": {{
        "textbooks": ["Book 1", "Book 2"],
        "online_materials": ["Website 1", "App 1"],
        "practice_tests": ["Test type 1", "Test type 2"]
    }},
    "milestone_assessments": [
        {{
            "week": 4,
            "type": "Speaking Assessment",
            "expected_band": 6.0
        }}
    ]
}}
"""
    
    def _calculate_cost(self, tokens: int, model: str) -> float:
        """Calculate API cost based on model and tokens"""
        rates = {
            "gpt-4": {"input": 0.03, "output": 0.06},  # per 1K tokens
            "gpt-3.5-turbo": {"input": 0.0015, "output": 0.002}
        }
        
        rate = rates.get(model, rates["gpt-4"])
        # Simplified calculation (assuming 50/50 input/output split)
        return (tokens * (rate["input"] + rate["output"]) / 2) / 1000

class FallbackAIService(BaseAIService):
    """Fallback AI service using open-source models"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize lightweight models for fallback"""
        try:
            # T5 for text generation and analysis
            self.t5_model = T5ForConditionalGeneration.from_pretrained("t5-small")
            self.t5_tokenizer = T5Tokenizer.from_pretrained("t5-small")
            
            # Sentiment analysis for basic feedback
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=0 if torch.cuda.is_available() else -1
            )
            
            # Whisper for local speech recognition
            self.whisper_model = whisper.load_model("base")
            
            logger.info("Fallback AI models initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing fallback models: {str(e)}")
            raise AIServiceError(f"Failed to initialize fallback AI: {str(e)}")
    
    async def grade_essay(self, content: str, task_type: str = "task2", language: str = "english") -> Dict[str, Any]:
        """Rule-based essay grading with ML assistance"""
        start_time = time.time()
        
        try:
            # Basic metrics
            word_count = len(content.split())
            sentence_count = len(re.split(r'[.!?]+', content))
            avg_sentence_length = word_count / max(sentence_count, 1)
            
            # Vocabulary analysis
            unique_words = len(set(content.lower().split()))
            vocabulary_diversity = unique_words / max(word_count, 1)
            
            # Grammar patterns
            complex_patterns = self._count_complex_grammar(content)
            
            # Sentiment analysis for coherence
            sentiment_scores = self.sentiment_analyzer(content[:500])  # First 500 chars
            
            # Calculate scores based on rules + ML
            scores = self._calculate_fallback_scores(
                word_count, vocabulary_diversity, complex_patterns,
                avg_sentence_length, task_type
            )
            
            return {
                "scores": scores,
                "detailed_feedback": {
                    "task_achievement": f"Word count: {word_count}. {'Adequate length' if word_count >= 250 else 'Too short for task requirements'}",
                    "coherence_cohesion": f"Sentence variety: {avg_sentence_length:.1f} words/sentence. {'Good structure' if avg_sentence_length > 15 else 'Simple sentence structure'}",
                    "lexical_resource": f"Vocabulary diversity: {vocabulary_diversity:.2f}. {'Good variety' if vocabulary_diversity > 0.5 else 'Limited vocabulary range'}",
                    "grammar_accuracy": f"Complex structures: {complex_patterns}. {'Some complexity shown' if complex_patterns > 2 else 'More complex grammar needed'}"
                },
                "improvement_suggestions": [
                    "Use more varied vocabulary" if vocabulary_diversity < 0.5 else "Good vocabulary range",
                    "Include more complex sentence structures" if complex_patterns < 3 else "Good grammatical variety",
                    "Develop ideas more fully with examples" if word_count < 300 else "Good development"
                ],
                "processing_time": time.time() - start_time,
                "ai_service": "fallback",
                "model": "rule-based+ml",
                "confidence": 0.75,
                "cost": 0.0  # Free fallback
            }
            
        except Exception as e:
            logger.error(f"Fallback essay grading failed: {str(e)}")
            raise AIServiceError(f"Fallback essay grading failed: {str(e)}")
    
    async def analyze_speaking(self, audio_path: str, question: str, language: str = "english") -> Dict[str, Any]:
        """Local speech analysis using Whisper + rule-based scoring"""
        start_time = time.time()
        
        try:
            # Transcribe with local Whisper
            result = self.whisper_model.transcribe(audio_path)
            transcription = result["text"]
            
            # Calculate speech metrics
            word_count = len(transcription.split())
            # Estimate duration from file (you'd need audio processing library)
            duration = 60.0  # Placeholder - implement actual duration detection
            speech_rate = (word_count / duration) * 60 if duration > 0 else 0
            
            # Analysis
            vocabulary_diversity = len(set(transcription.lower().split())) / max(word_count, 1)
            complex_grammar = self._count_complex_grammar(transcription)
            
            # Rule-based scoring
            scores = self._calculate_speaking_scores(
                speech_rate, vocabulary_diversity, complex_grammar, word_count
            )
            
            return {
                "scores": scores,
                "transcription": transcription,
                "speech_metrics": {
                    "speech_rate": speech_rate,
                    "vocabulary_diversity": vocabulary_diversity,
                    "word_count": word_count
                },
                "detailed_analysis": {
                    "fluency_coherence": f"Speech rate: {speech_rate:.1f} wpm. {'Good pace' if 120 <= speech_rate <= 160 else 'Consider adjusting pace'}",
                    "lexical_resource": f"Vocabulary variety: {vocabulary_diversity:.2f}. {'Good range' if vocabulary_diversity > 0.6 else 'Expand vocabulary'}",
                    "grammatical_range": f"Complex structures: {complex_grammar}. {'Some variety' if complex_grammar > 1 else 'Use more complex grammar'}",
                    "pronunciation": "Unable to assess pronunciation with current model"
                },
                "processing_time": time.time() - start_time,
                "ai_service": "fallback",
                "model": "whisper+rules",
                "confidence": 0.70,
                "cost": 0.0
            }
            
        except Exception as e:
            logger.error(f"Fallback speaking analysis failed: {str(e)}")
            raise AIServiceError(f"Fallback speaking analysis failed: {str(e)}")
    
    async def generate_curriculum(self, student_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Template-based curriculum generation"""
        start_time = time.time()
        
        try:
            current_band = student_profile.get('overall_band', 5.0)
            target_band = student_profile.get('target_band', current_band + 1.0)
            weak_areas = student_profile.get('weak_areas', ['grammar', 'vocabulary'])
            weeks = student_profile.get('timeline_weeks', 12)
            
            # Generate template-based curriculum
            curriculum = self._generate_template_curriculum(
                current_band, target_band, weak_areas, weeks
            )
            
            return {
                "curriculum_overview": curriculum["overview"],
                "weekly_plan": curriculum["weekly_plan"],
                "resources": curriculum["resources"],
                "milestone_assessments": curriculum["assessments"],
                "processing_time": time.time() - start_time,
                "ai_service": "fallback",
                "model": "template-based",
                "confidence": 0.80,
                "cost": 0.0,
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Fallback curriculum generation failed: {str(e)}")
            raise AIServiceError(f"Fallback curriculum generation failed: {str(e)}")
    
    def _count_complex_grammar(self, text: str) -> int:
        """Count complex grammatical structures"""
        patterns = [
            r'\b(although|however|nevertheless|furthermore)\b',
            r'\b(which|who|that)\b.*,',  # Relative clauses
            r'\b(if|unless|provided)\b.*,',  # Conditionals
            r'\b(because|since|as)\b',
            r'\b(despite|in spite of)\b'
        ]
        
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, text, re.IGNORECASE))
        return count
    
    def _calculate_fallback_scores(self, word_count: int, vocab_diversity: float, 
                                 complex_grammar: int, avg_sentence_length: float, 
                                 task_type: str) -> Dict[str, float]:
        """Calculate IELTS-style scores using rules"""
        
        # Base scores
        task_achievement = 5.0
        coherence_cohesion = 5.0
        lexical_resource = 5.0
        grammar_accuracy = 5.0
        
        # Task Achievement
        min_words = 250 if task_type == "task2" else 150
        if word_count >= min_words:
            task_achievement += 1.0
        if word_count >= min_words * 1.2:
            task_achievement += 0.5
        
        # Coherence & Cohesion
        if avg_sentence_length > 15:
            coherence_cohesion += 0.5
        if avg_sentence_length > 20:
            coherence_cohesion += 0.5
        
        # Lexical Resource
        if vocab_diversity > 0.5:
            lexical_resource += 1.0
        if vocab_diversity > 0.6:
            lexical_resource += 0.5
        
        # Grammar Accuracy
        if complex_grammar >= 2:
            grammar_accuracy += 0.5
        if complex_grammar >= 4:
            grammar_accuracy += 0.5
        
        # Cap at 9.0
        scores = {
            "task_achievement": min(task_achievement, 9.0),
            "coherence_cohesion": min(coherence_cohesion, 9.0),
            "lexical_resource": min(lexical_resource, 9.0),
            "grammar_accuracy": min(grammar_accuracy, 9.0)
        }
        
        scores["overall_band"] = round(sum(scores.values()) / 4, 1)
        return scores
    
    def _calculate_speaking_scores(self, speech_rate: float, vocab_diversity: float,
                                 complex_grammar: int, word_count: int) -> Dict[str, float]:
        """Calculate speaking scores using rules"""
        
        fluency_coherence = 5.0
        lexical_resource = 5.0
        grammatical_range = 5.0
        pronunciation = 6.0  # Default since we can't assess
        
        # Fluency (optimal 120-160 wpm)
        if 100 <= speech_rate <= 180:
            fluency_coherence += 1.0
        if 120 <= speech_rate <= 160:
            fluency_coherence += 0.5
        
        # Lexical Resource
        if vocab_diversity > 0.6:
            lexical_resource += 1.0
        if vocab_diversity > 0.7:
            lexical_resource += 0.5
        
        # Grammar
        if complex_grammar >= 1:
            grammatical_range += 0.5
        if complex_grammar >= 3:
            grammatical_range += 0.5
        
        scores = {
            "fluency_coherence": min(fluency_coherence, 9.0),
            "lexical_resource": min(lexical_resource, 9.0),
            "grammatical_range": min(grammatical_range, 9.0),
            "pronunciation": pronunciation
        }
        
        scores["overall_band"] = round(sum(scores.values()) / 4, 1)
        return scores
    
    def _generate_template_curriculum(self, current_band: float, target_band: float,
                                    weak_areas: List[str], weeks: int) -> Dict[str, Any]:
        """Generate curriculum from templates"""
        
        improvement_needed = target_band - current_band
        
        # Focus areas based on weakness
        focus_map = {
            'grammar': 'Grammatical Range and Accuracy',
            'vocabulary': 'Lexical Resource',
            'speaking': 'Fluency and Coherence',
            'writing': 'Task Achievement',
            'pronunciation': 'Pronunciation'
        }
        
        focus_areas = [focus_map.get(area, area) for area in weak_areas[:3]]
        
        # Generate weekly plan
        weekly_plan = []
        for week in range(1, weeks + 1):
            theme = f"Week {week}: "
            if week <= weeks // 3:
                theme += "Foundation Building"
            elif week <= 2 * weeks // 3:
                theme += "Skill Development"
            else:
                theme += "Test Preparation"
            
            weekly_plan.append({
                "week": week,
                "theme": theme,
                "goals": [
                    f"Improve {focus_areas[0] if focus_areas else 'general skills'}",
                    "Practice test techniques",
                    "Build confidence"
                ],
                "lessons": [
                    {
                        "day": day,
                        "topic": f"{focus_areas[0] if focus_areas else 'General'} Practice",
                        "activities": ["Reading exercises", "Writing practice", "Speaking drills"],
                        "duration_minutes": 90,
                        "homework": "Complete practice exercises"
                    } for day in range(1, 4)  # 3 lessons per week
                ],
                "assessment": f"Week {week} progress test",
                "expected_progress": f"{(improvement_needed / weeks):.1f} band improvement"
            })
        
        return {
            "overview": {
                "title": f"IELTS Preparation: {current_band} → {target_band}",
                "duration_weeks": weeks,
                "target_improvement": f"+{improvement_needed:.1f} band score",
                "focus_areas": focus_areas
            },
            "weekly_plan": weekly_plan,
            "resources": {
                "textbooks": ["Official IELTS Practice Materials", "Cambridge IELTS Tests"],
                "online_materials": ["IELTSLiz.com", "British Council IELTS"],
                "practice_tests": ["Full IELTS Mock Tests", "Section-specific Practice"]
            },
            "assessments": [
                {
                    "week": weeks // 4,
                    "type": "Progress Assessment",
                    "expected_band": current_band + (improvement_needed * 0.25)
                },
                {
                    "week": weeks // 2,
                    "type": "Mid-course Evaluation",
                    "expected_band": current_band + (improvement_needed * 0.5)
                },
                {
                    "week": 3 * weeks // 4,
                    "type": "Pre-final Assessment",
                    "expected_band": current_band + (improvement_needed * 0.75)
                }
            ]
        }

class AIServiceManager:
    """Manages primary and fallback AI services with automatic switching"""
    
    def __init__(self):
        self.primary_service = None
        self.fallback_service = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize AI services with fallback handling"""
        try:
            # Try to initialize OpenAI service
            if settings.openai_api_key:
                self.primary_service = OpenAIService()
                logger.info("Primary AI service (OpenAI) initialized")
            else:
                logger.warning("OpenAI API key not found, using fallback only")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI service: {str(e)}")
        
        try:
            # Initialize fallback service
            self.fallback_service = FallbackAIService()
            logger.info("Fallback AI service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize fallback service: {str(e)}")
            raise AIServiceError("No AI services available")
    
    async def grade_essay(self, content: str, task_type: str = "task2", 
                         language: str = "english") -> Dict[str, Any]:
        """Grade essay with automatic fallback"""
        if self.primary_service:
            try:
                return await self.primary_service.grade_essay(content, task_type, language)
            except AIServiceError as e:
                logger.warning(f"Primary service failed, using fallback: {str(e)}")
        
        if self.fallback_service:
            return await self.fallback_service.grade_essay(content, task_type, language)
        
        raise AIServiceError("No AI services available for essay grading")
    
    async def analyze_speaking(self, audio_path: str, question: str, 
                             language: str = "english") -> Dict[str, Any]:
        """Analyze speaking with automatic fallback"""
        if self.primary_service:
            try:
                return await self.primary_service.analyze_speaking(audio_path, question, language)
            except AIServiceError as e:
                logger.warning(f"Primary service failed, using fallback: {str(e)}")
        
        if self.fallback_service:
            return await self.fallback_service.analyze_speaking(audio_path, question, language)
        
        raise AIServiceError("No AI services available for speaking analysis")
    
    async def generate_curriculum(self, student_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate curriculum with automatic fallback"""
        if self.primary_service:
            try:
                return await self.primary_service.generate_curriculum(student_profile)
            except AIServiceError as e:
                logger.warning(f"Primary service failed, using fallback: {str(e)}")
        
        if self.fallback_service:
            return await self.fallback_service.generate_curriculum(student_profile)
        
        raise AIServiceError("No AI services available for curriculum generation")

# Global AI service manager instance
ai_service_manager = AIServiceManager()