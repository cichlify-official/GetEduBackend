import openai
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class EnhancedAIService:
    """Comprehensive AI service for all language skills"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4-turbo-preview"
        
    async def grade_essay(self, content: str, task_type: str = "general", word_count: int = 0) -> Dict[str, Any]:
        """Grade an essay using GPT-4 with IELTS standards"""
        
        prompt = self._build_essay_prompt(content, task_type, word_count)
        
        try:
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
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["tokens_used"] = response.usage.total_tokens
            result["cost"] = self._calculate_cost(response.usage.total_tokens)
            
            return result
            
        except Exception as e:
            logger.error(f"Essay grading failed: {str(e)}")
            return self._fallback_essay_response(e)
    
    async def analyze_speaking(self, transcription: str, audio_duration: float = 0, 
                             task_type: str = "general", question: str = "") -> Dict[str, Any]:
        """Analyze speaking performance from transcription"""
        
        prompt = self._build_speaking_prompt(transcription, audio_duration, task_type, question)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert IELTS speaking examiner. 
                        Analyze speaking performance based on transcription and provide detailed feedback.
                        Consider fluency, coherence, pronunciation patterns, lexical resource, and grammatical range.
                        Return actionable recommendations for improvement."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["tokens_used"] = response.usage.total_tokens
            result["cost"] = self._calculate_cost(response.usage.total_tokens)
            
            return result
            
        except Exception as e:
            logger.error(f"Speaking analysis failed: {str(e)}")
            return self._fallback_speaking_response(e)
    
    async def grade_reading(self, questions: List[Dict], student_answers: List[Any], 
                          correct_answers: List[Any], passage: str) -> Dict[str, Any]:
        """Grade reading comprehension based on student answers"""
        
        prompt = self._build_reading_prompt(questions, student_answers, correct_answers, passage)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert reading comprehension assessor.
                        Evaluate student answers against correct answers and provide detailed feedback.
                        Assess different reading skills: inference, vocabulary understanding, scanning, skimming, etc.
                        Provide specific recommendations for improvement."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["tokens_used"] = response.usage.total_tokens
            result["cost"] = self._calculate_cost(response.usage.total_tokens)
            
            return result
            
        except Exception as e:
            logger.error(f"Reading grading failed: {str(e)}")
            return self._fallback_reading_response(e)
    
    async def grade_listening(self, questions: List[Dict], student_answers: List[Any], 
                            correct_answers: List[Any], transcript: str = "") -> Dict[str, Any]:
        """Grade listening comprehension based on student answers"""
        
        prompt = self._build_listening_prompt(questions, student_answers, correct_answers, transcript)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert listening comprehension assessor.
                        Evaluate student answers and provide detailed feedback on listening skills.
                        Assess: detail identification, gist understanding, inference, and note-taking.
                        Provide specific recommendations for improvement."""
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["tokens_used"] = response.usage.total_tokens
            result["cost"] = self._calculate_cost(response.usage.total_tokens)
            
            return result
            
        except Exception as e:
            logger.error(f"Listening grading failed: {str(e)}")
            return self._fallback_listening_response(e)
    
    async def generate_reading_questions(self, passage: str, difficulty: str = "intermediate",
                                       num_questions: int = 10) -> Dict[str, Any]:
        """Generate reading comprehension questions from a passage"""
        
        prompt = f"""
        Create {num_questions} reading comprehension questions for this passage at {difficulty} level.
        
        Passage:
        {passage}
        
        Create a mix of:
        - Multiple choice questions (4 options each)
        - True/False/Not Given questions
        - Short answer questions
        - Gap-fill questions
        
        Return in this JSON format:
        {{
            "questions": [
                {{
                    "id": 1,
                    "type": "multiple_choice",
                    "question": "What is the main idea of the passage?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "skill_tested": "gist_understanding"
                }},
                {{
                    "id": 2,
                    "type": "true_false_not_given",
                    "question": "The author believes...",
                    "correct_answer": "True",
                    "skill_tested": "inference"
                }}
            ],
            "answer_key": [
                {{"question_id": 1, "correct_answer": "A", "explanation": "Because..."}},
                {{"question_id": 2, "correct_answer": "True", "explanation": "The passage states..."}}
            ],
            "difficulty_level": "{difficulty}",
            "skills_tested": ["gist_understanding", "inference", "vocabulary", "detail_identification"]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert test creator specializing in reading comprehension assessments."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["tokens_used"] = response.usage.total_tokens
            result["cost"] = self._calculate_cost(response.usage.total_tokens)
            
            return result
            
        except Exception as e:
            logger.error(f"Reading question generation failed: {str(e)}")
            return {"error": str(e), "questions": [], "answer_key": []}
    
    async def generate_listening_questions(self, transcript: str, difficulty: str = "intermediate",
                                         num_questions: int = 10) -> Dict[str, Any]:
        """Generate listening comprehension questions from a transcript"""
        
        prompt = f"""
        Create {num_questions} listening comprehension questions for this transcript at {difficulty} level.
        
        Transcript:
        {transcript}
        
        Create a mix of:
        - Multiple choice questions
        - Fill-in-the-blank questions
        - Note completion questions
        - Matching questions
        
        Return in this JSON format:
        {{
            "questions": [
                {{
                    "id": 1,
                    "type": "multiple_choice",
                    "question": "What is the speaker's main point?",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "skill_tested": "gist_understanding"
                }},
                {{
                    "id": 2,
                    "type": "fill_blank",
                    "question": "The speaker mentions that the project will take _____ weeks.",
                    "correct_answer": "six",
                    "skill_tested": "detail_identification"
                }}
            ],
            "answer_key": [
                {{"question_id": 1, "correct_answer": "A", "explanation": "Because..."}},
                {{"question_id": 2, "correct_answer": "six", "explanation": "The speaker clearly states..."}}
            ],
            "difficulty_level": "{difficulty}",
            "skills_tested": ["gist_understanding", "detail_identification", "inference", "note_taking"]
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert test creator specializing in listening comprehension assessments."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["tokens_used"] = response.usage.total_tokens
            result["cost"] = self._calculate_cost(response.usage.total_tokens)
            
            return result
            
        except Exception as e:
            logger.error(f"Listening question generation failed: {str(e)}")
            return {"error": str(e), "questions": [], "answer_key": []}
    
    async def generate_lesson_plan(self, skill_profile: Dict[str, Any], 
                                 recent_submissions: List[Dict]) -> Dict[str, Any]:
        """Generate personalized lesson plan based on student performance"""
        
        prompt = f"""
        Create a personalized lesson plan for a student based on their skill profile and recent submissions.
        
        Skill Profile:
        {json.dumps(skill_profile, indent=2)}
        
        Recent Submissions:
        {json.dumps(recent_submissions, indent=2)}
        
        Focus on the student's weakest areas and provide actionable improvement strategies.
        
        Return in this JSON format:
        {{
            "lesson_plan": {{
                "title": "Personalized Learning Plan",
                "focus_skills": ["writing_coherence", "vocabulary_range"],
                "priority_areas": [
                    {{
                        "skill": "writing_coherence",
                        "current_level": 5.5,
                        "target_level": 6.5,
                        "improvement_strategy": "Practice using linking words and paragraph structure"
                    }}
                ],
                "weekly_activities": [
                    {{
                        "week": 1,
                        "title": "Improving Essay Structure",
                        "activities": [
                            {{
                                "type": "writing_practice",
                                "description": "Write 3 essays focusing on clear introduction-body-conclusion structure",
                                "duration": 45,
                                "materials": ["essay templates", "linking words list"]
                            }}
                        ]
                    }}
                ],
                "learning_objectives": [
                    "Improve paragraph coherence by 1 band score",
                    "Expand academic vocabulary by 50 new words"
                ],
                "assessment_methods": [
                    "Weekly essay submissions",
                    "Vocabulary quizzes",
                    "Speaking practice sessions"
                ],
                "estimated_duration": "4 weeks",
                "difficulty_progression": "gradual increase from current level"
            }}
        }}
        """
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert language learning curriculum designer with expertise in personalized education."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["tokens_used"] = response.usage.total_tokens
            result["cost"] = self._calculate_cost(response.usage.total_tokens)
            
            return result
            
        except Exception as e:
            logger.error(f"Lesson plan generation failed: {str(e)}")
            return self._fallback_lesson_plan(e)
    
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
    
    def _build_speaking_prompt(self, transcription: str, duration: float, task_type: str, question: str) -> str:
        """Build speaking analysis prompt"""
        
        return f"""
        Analyze this IELTS speaking performance based on the transcription:
        
        Task Type: {task_type}
        Question: {question}
        Duration: {duration} seconds
        
        Transcription:
        {transcription}
        
        Provide analysis in this JSON format:
        {{
            "scores": {{
                "fluency_coherence": 6.5,
                "lexical_resource": 6.0,
                "grammatical_range": 6.5,
                "pronunciation": 6.0,
                "overall_band": 6.5
            }},
            "analysis": {{
                "fluency_indicators": ["hesitations", "pace", "discourse_markers"],
                "lexical_analysis": ["vocabulary_range", "accuracy", "appropriateness"],
                "grammar_analysis": ["complexity", "accuracy", "range"],
                "pronunciation_notes": ["clarity", "stress", "intonation"]
            }},
            "feedback": {{
                "strengths": ["Clear articulation", "Good vocabulary usage"],
                "improvements": ["Reduce hesitations", "Use more complex grammar"],
                "suggestions": ["Practice with linking words", "Record yourself speaking daily"]
            }},
            "lesson_recommendations": [
                {{
                    "skill": "fluency_development",
                    "priority": "high",
                    "activities": ["Daily speaking practice", "Shadowing exercises"]
                }}
            ]
        }}
        """
    
    def _build_reading_prompt(self, questions: List[Dict], student_answers: List[Any], 
                            correct_answers: List[Any], passage: str) -> str:
        """Build reading grading prompt"""
        
        return f"""
        Grade this reading comprehension submission:
        
        Passage: {passage[:500]}...
        
        Questions and Answers:
        {json.dumps(list(zip(questions, student_answers, correct_answers)), indent=2)}
        
        Provide grading in this JSON format:
        {{
            "scores": {{
                "overall_score": 7.5,
                "accuracy_score": 8.0,
                "comprehension_skills": {{
                    "inference": 7.0,
                    "vocabulary": 8.0,
                    "scanning": 7.5,
                    "gist_understanding": 7.0
                }}
            }},
            "question_analysis": [
                {{
                    "question_id": 1,
                    "correct": true,
                    "skill_tested": "inference",
                    "feedback": "Good understanding of implied meaning"
                }}
            ],
            "feedback": {{
                "strengths": ["Strong vocabulary understanding", "Good scanning skills"],
                "improvements": ["Work on inference skills", "Practice time management"],
                "suggestions": ["Read more academic texts", "Practice timed exercises"]
            }},
            "lesson_recommendations": [
                {{
                    "skill": "inference_development",
                    "priority": "medium",
                    "activities": ["Practice with inference exercises", "Analyze author's tone"]
                }}
            ]
        }}
        """
    
    def _build_listening_prompt(self, questions: List[Dict], student_answers: List[Any], 
                              correct_answers: List[Any], transcript: str) -> str:
        """Build listening grading prompt"""
        
        return f"""
        Grade this listening comprehension submission:
        
        Transcript: {transcript[:500]}...
        
        Questions and Answers:
        {json.dumps(list(zip(questions, student_answers, correct_answers)), indent=2)}
        
        Provide grading in this JSON format:
        {{
            "scores": {{
                "overall_score": 7.0,
                "accuracy_score": 7.5,
                "listening_skills": {{
                    "detail_identification": 7.5,
                    "gist_understanding": 7.0,
                    "inference": 6.5,
                    "note_taking": 7.0
                }}
            }},
            "question_analysis": [
                {{
                    "question_id": 1,
                    "correct": true,
                    "skill_tested": "detail_identification",
                    "feedback": "Correctly identified specific information"
                }}
            ],
            "feedback": {{
                "strengths": ["Good detail identification", "Accurate note-taking"],
                "improvements": ["Work on inference from context", "Practice with different accents"],
                "suggestions": ["Listen to various English accents", "Practice prediction skills"]
            }},
            "lesson_recommendations": [
                {{
                    "skill": "inference_listening",
                    "priority": "high",
                    "activities": ["Practice with inference exercises", "Listen to podcasts"]
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
                "improvements": ["AI grading service unavailable"],
                "suggestions": ["Please try again later"]
            },
            "error": str(error),
            "demo_mode": True
        }
    
    def _fallback_speaking_response(self, error: Exception) -> Dict[str, Any]:
        """Fallback response for speaking analysis"""
        return {
            "scores": {
                "fluency_coherence": 6.0,
                "lexical_resource": 6.0,
                "grammatical_range": 6.0,
                "pronunciation": 6.0,
                "overall_band": 6.0
            },
            "feedback": {
                "strengths": ["Audio submitted successfully"],
                "improvements": ["AI analysis service unavailable"],
                "suggestions": ["Please try again later"]
            },
            "error": str(error),
            "demo_mode": True
        }
    
    def _fallback_reading_response(self, error: Exception) -> Dict[str, Any]:
        """Fallback response for reading grading"""
        return {
            "scores": {
                "overall_score": 6.0,
                "accuracy_score": 6.0,
                "comprehension_skills": {
                    "inference": 6.0,
                    "vocabulary": 6.0,
                    "scanning": 6.0,
                    "gist_understanding": 6.0
                }
            },
            "error": str(error),
            "demo_mode": True
        }
    
    def _fallback_listening_response(self, error: Exception) -> Dict[str, Any]:
        """Fallback response for listening grading"""
        return {
            "scores": {
                "overall_score": 6.0,
                "accuracy_score": 6.0,
                "listening_skills": {
                    "detail_identification": 6.0,
                    "gist_understanding": 6.0,
                    "inference": 6.0,
                    "note_taking": 6.0
                }
            },
            "error": str(error),
            "demo_mode": True
        }
    
    def _fallback_lesson_plan(self, error: Exception) -> Dict[str, Any]:
        """Fallback response for lesson plan generation"""
        return {
            "lesson_plan": {
                "title": "General Learning Plan",
                "focus_skills": ["general_improvement"],
                "error": str(error),
                "demo_mode": True
            }
        }


class WhisperService:
    """Service for audio transcription using OpenAI Whisper"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
    async def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """Transcribe audio file using Whisper"""
        
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )
            
            return {
                "text": transcript.text,
                "duration": transcript.duration if hasattr(transcript, 'duration') else 0,
                "language": transcript.language if hasattr(transcript, 'language') else 'en',
                "segments": transcript.segments if hasattr(transcript, 'segments') else []
            }
            
        except Exception as e:
            logger.error(f"Audio transcription failed: {str(e)}")
            return {
                "text": "Transcription failed - please try again",
                "duration": 0,
                "error": str(e)
            }