# app/services/sync_ai_service.py - Synchronous version for Celery workers
import openai
import json
import time
import logging
from typing import Dict, Any, Optional
import requests
import whisper
import torch
from transformers import pipeline, T5ForConditionalGeneration, T5Tokenizer
import re
from config.settings import settings

logger = logging.getLogger(__name__)

class SyncOpenAIService:
    """Synchronous OpenAI service for Celery workers"""
    
    def __init__(self):
        if not settings.openai_api_key:
            raise Exception("OpenAI API key not configured")
        
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.max_retries = 3
        self.timeout = 30
    
    def grade_essay(self, content: str, task_type: str = "task2", language: str = "english", word_count: int = 0) -> Dict[str, Any]:
        """Grade essay using GPT-4"""
        start_time = time.time()
        
        if not word_count:
            word_count = len(content.split())
        
        prompt = self._build_essay_prompt(content, task_type, language, word_count)
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are an expert IELTS examiner for {language.title()} language assessment. Provide accurate, detailed feedback according to official IELTS band descriptors. Always return valid JSON."
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
                    "confidence": 0.95
                })
                
                return result
                
            except Exception as e:
                logger.warning(f"OpenAI attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"OpenAI essay grading failed: {str(e)}")
                time.sleep(2 ** attempt)
    
    def analyze_speaking(self, audio_path: str, question: str, language: str = "english") -> Dict[str, Any]:
        """Analyze speaking using Whisper + GPT-4"""
        start_time = time.time()
        
        try:
            # Transcribe audio
            with open(audio_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )
            
            # Analyze with GPT-4
            analysis_prompt = self._build_speaking_prompt(
                transcription.text, question, language, transcription.duration
            )
            
            response = self.client.chat.completions.create(
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
                "cost": self._calculate_cost(response.usage.total_tokens, "gpt-4") + 0.006,
                "processing_time": time.time() - start_time,
                "ai_service": "openai",
                "model": "whisper+gpt-4",
                "confidence": 0.90
            })
            
            return result
            
        except Exception as e:
            raise Exception(f"OpenAI speaking analysis failed: {str(e)}")
    
    def generate_curriculum(self, student_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate curriculum using GPT-4"""
        start_time = time.time()
        
        prompt = self._build_curriculum_prompt(student_profile)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert language learning curriculum designer. Create detailed, personalized learning plans. Return structured JSON."
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
                "model": "gpt-4"
            })
            
            return result
            
        except Exception as e:
            raise Exception(f"Curriculum generation failed: {str(e)}")
    
    def _build_essay_prompt(self, content: str, task_type: str, language: str, word_count: int) -> str:
        """Build essay grading prompt"""
        
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
    "feedback": {{
        "strengths": ["Point 1", "Point 2"],
        "improvements": ["Area 1", "Area 2"],
        "suggestions": ["Suggestion 1", "Suggestion 2"]
    }},
    "detailed_feedback": {{
        "task_achievement": "Detailed analysis...",
        "coherence_cohesion": "Analysis of organization...",
        "lexical_resource": "Vocabulary assessment...",
        "grammar_accuracy": "Grammar evaluation..."
    }},
    "error_analysis": {{
        "grammar_errors": ["Error with correction"],
        "vocabulary_issues": ["Issue with suggestion"]
    }}
}}

Use 0.5 increments. Be precise and constructive.
"""
    
    def _build_speaking_prompt(self, transcription: str, question: str, language: str, duration: float) -> str:
        """Build speaking analysis prompt"""
        
        word_count = len(transcription.split())
        words_per_minute = (word_count / duration * 60) if duration > 0 else 0
        
        return f"""
Analyze this {language.title()} IELTS speaking response:

Question: {question}
Duration: {duration:.1f} seconds
Speaking Rate: {words_per_minute:.1f} words/minute

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
        "fluency_coherence": "Analysis of speech flow...",
        "lexical_resource": "Vocabulary assessment...",
        "grammatical_range": "Grammar complexity...",
        "pronunciation": "Clarity assessment..."
    }},
    "speech_metrics": {{
        "speech_rate": {words_per_minute:.1f},
        "vocabulary_diversity": 0.65,
        "pause_frequency": "normal"
    }},
    "improvement_areas": ["Area 1", "Area 2"],
    "pronunciation_feedback": ["Point 1", "Point 2"]
}}
"""
    
    def _build_curriculum_prompt(self, student_profile: Dict[str, Any]) -> str:
        """Build curriculum generation prompt"""
        
        return f"""
Create a personalized language learning curriculum:

Student Profile:
- Current Level: {student_profile.get('current_level', 'A2')}
- Overall Band: {student_profile.get('overall_band', 4.0)}
- Target Band: {student_profile.get('target_band', 6.0)}
- Weak Areas: {student_profile.get('weak_areas', [])}
- Language: {student_profile.get('language', 'English')}
- Weekly Hours: {student_profile.get('weekly_hours', 10)}
- Timeline: {student_profile.get('timeline_weeks', 12)} weeks

Provide curriculum in this EXACT JSON format:
{{
    "curriculum_overview": {{
        "title": "Personalized English Course",
        "duration_weeks": 12,
        "target_improvement": "+1.5 band score",
        "focus_areas": ["grammar", "vocabulary", "speaking"]
    }},
    "weekly_plan": [
        {{
            "week": 1,
            "theme": "Foundation Building",
            "goals": ["Master present tenses", "Build core vocabulary"],
            "lessons": [
                {{
                    "day": 1,
                    "topic": "Present Simple vs Continuous",
                    "activities": ["Grammar exercises", "Speaking practice"],
                    "duration_minutes": 90,
                    "homework": "Complete workbook pages 1-5"
                }}
            ],
            "assessment": "Weekly grammar quiz",
            "expected_progress": "0.1 band improvement"
        }}
    ],
    "resources": {{
        "textbooks": ["Cambridge English Grammar", "Vocabulary in Use"],
        "online_materials": ["BBC Learning English", "IELTS Liz"],
        "practice_tests": ["Cambridge IELTS 17", "Mini mock tests"]
    }},
    "difficulty_progression": [
        {{"week": 1, "level": "A2", "focus": "basics"}},
        {{"week": 6, "level": "B1", "focus": "intermediate"}},
        {{"week": 12, "level": "B2", "focus": "advanced"}}
    ]
}}
"""
    
    def _calculate_cost(self, tokens: int, model: str) -> float:
        """Calculate API cost"""
        rates = {
            "gpt-4": 0.03,  # per 1K tokens (simplified)
            "gpt-3.5-turbo": 0.002
        }
        return (tokens * rates.get(model, 0.03)) / 1000

class SyncFallbackAIService:
    """Synchronous fallback AI service using local models"""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize lightweight models"""
        try:
            # Load Whisper for local transcription
            self.whisper_model = whisper.load_model("base")
            
            # Load sentiment analyzer
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",
                device=0 if torch.cuda.is_available() else -1
            )
            
            logger.info("Fallback AI models initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing fallback models: {str(e)}")
            # Set to None if models fail to load
            self.whisper_model = None
            self.sentiment_analyzer = None
    
    def grade_essay(self, content: str, task_type: str = "task2", language: str = "english", word_count: int = 0) -> Dict[str, Any]:
        """Rule-based essay grading with ML assistance"""
        start_time = time.time()
        
        if not word_count:
            word_count = len(content.split())
        
        try:
            # Basic metrics
            sentence_count = len(re.split(r'[.!?]+', content))
            avg_sentence_length = word_count / max(sentence_count, 1)
            
            # Vocabulary analysis
            unique_words = len(set(content.lower().split()))
            vocabulary_diversity = unique_words / max(word_count, 1)
            
            # Grammar patterns
            complex_patterns = self._count_complex_grammar(content)
            
            # Calculate scores
            scores = self._calculate_essay_scores(
                word_count, vocabulary_diversity, complex_patterns,
                avg_sentence_length, task_type
            )
            
            # Generate feedback
            feedback = self._generate_essay_feedback(
                word_count, vocabulary_diversity, complex_patterns, scores
            )
            
            return {
                "scores": scores,
                "feedback": feedback["general"],
                "detailed_feedback": feedback["detailed"],
                "error_analysis": feedback["errors"],
                "processing_time": time.time() - start_time,
                "ai_service": "fallback",
                "model": "rule-based+ml",
                "confidence": 0.75,
                "cost": 0.0
            }
            
        except Exception as e:
            logger.error(f"Fallback essay grading failed: {str(e)}")
            raise Exception(f"Essay grading failed: {str(e)}")
    
    def analyze_speaking(self, audio_path: str, question: str, language: str = "english") -> Dict[str, Any]:
        """Local speech analysis using Whisper + rules"""
        start_time = time.time()
        
        try:
            # Transcribe with local Whisper
            if self.whisper_model:
                result = self.whisper_model.transcribe(audio_path)
                transcription = result["text"]
                # Estimate duration (you'd need audio processing for actual duration)
                duration = 60.0  # Placeholder
            else:
                # Fallback if Whisper not available
                transcription = "Audio transcription unavailable - Whisper model not loaded"
                duration = 60.0
            
            # Calculate metrics
            word_count = len(transcription.split())
            speech_rate = (word_count / duration) * 60 if duration > 0 else 0
            vocabulary_diversity = len(set(transcription.lower().split())) / max(word_count, 1)
            complex_grammar = self._count_complex_grammar(transcription)
            
            # Calculate scores
            scores = self._calculate_speaking_scores(
                speech_rate, vocabulary_diversity, complex_grammar, word_count
            )
            
            # Generate analysis
            analysis = self._generate_speaking_analysis(
                speech_rate, vocabulary_diversity, complex_grammar, scores
            )
            
            return {
                "scores": scores,
                "transcription": transcription,
                "audio_duration": duration,
                "detailed_analysis": analysis,
                "speech_metrics": {
                    "speech_rate": speech_rate,
                    "vocabulary_diversity": vocabulary_diversity,
                    "word_count": word_count
                },
                "improvement_areas": ["Practice fluency", "Expand vocabulary"],
                "pronunciation_feedback": ["Focus on clear articulation"],
                "processing_time": time.time() - start_time,
                "ai_service": "fallback",
                "model": "whisper+rules",
                "confidence": 0.70,
                "cost": 0.0
            }
            
        except Exception as e:
            logger.error(f"Fallback speaking analysis failed: {str(e)}")
            raise Exception(f"Speaking analysis failed: {str(e)}")
    
    def generate_curriculum(self, student_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Template-based curriculum generation"""
        start_time = time.time()
        
        try:
            current_band = student_profile.get('overall_band', 5.0)
            target_band = student_profile.get('target_band', current_band + 1.0)
            weak_areas = student_profile.get('weak_areas', ['grammar', 'vocabulary'])
            weeks = student_profile.get('timeline_weeks', 12)
            
            curriculum = self._generate_template_curriculum(
                current_band, target_band, weak_areas, weeks
            )
            
            return {
                "curriculum_overview": curriculum["overview"],
                "weekly_plan": curriculum["weekly_plan"],
                "resources": curriculum["resources"],
                "difficulty_progression": curriculum["progression"],
                "processing_time": time.time() - start_time,
                "ai_service": "fallback",
                "model": "template-based",
                "confidence": 0.80,
                "cost": 0.0
            }
            
        except Exception as e:
            logger.error(f"Fallback curriculum generation failed: {str(e)}")
            raise Exception(f"Curriculum generation failed: {str(e)}")
    
    def _count_complex_grammar(self, text: str) -> int:
        """Count complex grammatical structures"""
        patterns = [
            r'\b(although|however|nevertheless|furthermore)\b',
            r'\b(which|who|that)\b.*,',
            r'\b(if|unless|provided)\b.*,',
            r'\b(because|since|as)\b',
            r'\b(despite|in spite of)\b'
        ]
        
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, text, re.IGNORECASE))
        return count
    
    def _calculate_essay_scores(self, word_count: int, vocab_diversity: float, 
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
        if word_count >= min_words * 1.3:
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
        pronunciation = 6.0  # Default
        
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
    
    def _generate_essay_feedback(self, word_count: int, vocab_diversity: float, 
                               complex_patterns: int, scores: Dict[str, float]) -> Dict[str, Any]:
        """Generate essay feedback"""
        
        strengths = []
        improvements = []
        
        if scores['task_achievement'] >= 6.0:
            strengths.append("Good task response")
        else:
            improvements.append("Develop ideas more fully")
        
        if vocab_diversity > 0.5:
            strengths.append("Good vocabulary variety")
        else:
            improvements.append("Use more varied vocabulary")
        
        if complex_patterns >= 2:
            strengths.append("Some complex grammar used")
        else:
            improvements.append("Try more complex sentence structures")
        
        return {
            "general": {
                "strengths": strengths or ["Essay submitted successfully"],
                "improvements": improvements or ["Continue practicing"],
                "suggestions": ["Read more academic texts", "Practice writing regularly"]
            },
            "detailed": {
                "task_achievement": f"Word count: {word_count}. Task response adequate.",
                "coherence_cohesion": "Structure shows organization with some linking.",
                "lexical_resource": f"Vocabulary diversity: {vocab_diversity:.2f}. Range appropriate.",
                "grammar_accuracy": f"Complex patterns: {complex_patterns}. Some variety shown."
            },
            "errors": {
                "grammar_errors": ["Minor errors detected"],
                "vocabulary_issues": ["Some repetition noted"]
            }
        }
    
    def _generate_speaking_analysis(self, speech_rate: float, vocab_diversity: float,
                                  complex_grammar: int, scores: Dict[str, float]) -> Dict[str, str]:
        """Generate speaking analysis"""
        
        return {
            "fluency_coherence": f"Speech rate: {speech_rate:.1f} wpm. {'Good pace' if 120 <= speech_rate <= 160 else 'Consider adjusting pace'}",
            "lexical_resource": f"Vocabulary variety: {vocab_diversity:.2f}. {'Good range' if vocab_diversity > 0.6 else 'Expand vocabulary'}",
            "grammatical_range": f"Complex structures: {complex_grammar}. {'Some variety' if complex_grammar > 1 else 'Use more complex grammar'}",
            "pronunciation": "Pronunciation assessment requires audio analysis tools"
        }
    
    def _generate_template_curriculum(self, current_band: float, target_band: float,
                                    weak_areas: list, weeks: int) -> Dict[str, Any]:
        """Generate template-based curriculum"""
        
        improvement_needed = target_band - current_band
        
        # Weekly plan
        weekly_plan = []
        for week in range(1, weeks + 1):
            theme = "Foundation Building" if week <= weeks//3 else "Skill Development" if week <= 2*weeks//3 else "Test Preparation"
            
            weekly_plan.append({
                "week": week,
                "theme": theme,
                "goals": [f"Improve {weak_areas[0] if weak_areas else 'general skills'}", "Practice test techniques"],
                "lessons": [
                    {
                        "day": 1,
                        "topic": f"{weak_areas[0] if weak_areas else 'General'} Practice",
                        "activities": ["Exercises", "Practice tests"],
                        "duration_minutes": 90,
                        "homework": "Complete assigned practice"
                    }
                ],
                "assessment": f"Week {week} progress test",
                "expected_progress": f"{improvement_needed/weeks:.1f} band improvement"
            })
        
        return {
            "overview": {
                "title": f"Language Learning Path: {current_band} → {target_band}",
                "duration_weeks": weeks,
                "target_improvement": f"+{improvement_needed:.1f} band score",
                "focus_areas": weak_areas
            },
            "weekly_plan": weekly_plan,
            "resources": {
                "textbooks": ["Official Practice Materials", "Grammar Reference"],
                "online_materials": ["Language Learning Websites", "Practice Platforms"],
                "practice_tests": ["Mock Tests", "Skill-specific Practice"]
            },
            "progression": [
                {"week": i, "level": f"Week {i}", "focus": "progressive"} 
                for i in range(1, weeks + 1, weeks//4)
            ]
        }

class SyncAIServiceManager:
    """Synchronous AI service manager for Celery workers"""
    
    def __init__(self):
        self.primary_service = None
        self.fallback_service = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize AI services"""
        try:
            if settings.openai_api_key:
                self.primary_service = SyncOpenAIService()
                logger.info("Primary AI service (OpenAI) initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI service: {str(e)}")
        
        try:
            self.fallback_service = SyncFallbackAIService()
            logger.info("Fallback AI service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize fallback service: {str(e)}")
    
    def grade_essay(self, content: str, task_type: str = "task2", 
                   language: str = "english", word_count: int = 0) -> Dict[str, Any]:
        """Grade essay with automatic fallback"""
        if self.primary_service:
            try:
                return self.primary_service.grade_essay(content, task_type, language, word_count)
            except Exception as e:
                logger.warning(f"Primary service failed, using fallback: {str(e)}")
        
        if self.fallback_service:
            return self.fallback_service.grade_essay(content, task_type, language, word_count)
        
        raise Exception("No AI services available for essay grading")
    
    def analyze_speaking(self, audio_path: str, question: str, 
                        language: str = "english") -> Dict[str, Any]:
        """Analyze speaking with automatic fallback"""
        if self.primary_service:
            try:
                return self.primary_service.analyze_speaking(audio_path, question, language)
            except Exception as e:
                logger.warning(f"Primary service failed, using fallback: {str(e)}")
        
        if self.fallback_service:
            return self.fallback_service.analyze_speaking(audio_path, question, language)
        
        raise Exception("No AI services available for speaking analysis")
    
    def generate_curriculum(self, student_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate curriculum with automatic fallback"""
        if self.primary_service:
            try:
                return self.primary_service.generate_curriculum(student_profile)
            except Exception as e:
                logger.warning(f"Primary service failed, using fallback: {str(e)}")
        
        if self.fallback_service:
            return self.fallback_service.generate_curriculum(student_profile)
        
        raise Exception("No AI services available for curriculum generation")