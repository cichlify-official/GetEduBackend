import openai
import json
import os
from typing import Dict, Any, Optional
from config.settings import settings

# Set OpenAI API key
openai.api_key = settings.openai_api_key

class OpenAIService:
    """
    Service for interacting with OpenAI GPT models
    This is where the magic happens - we send essays to GPT and get grades back!
    """
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
    def grade_essay(self, content: str, task_type: str = "general", word_count: int = 0) -> Dict[str, Any]:
        """
        Grade an essay using GPT-4
        
        Args:
            content: The essay text
            task_type: Type of essay (task1, task2, general)
            word_count: Number of words in the essay
            
        Returns:
            Dictionary with scores and feedback
        """
        
        # Create the grading prompt
        prompt = self._build_essay_grading_prompt(content, task_type, word_count)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
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
                temperature=0.3,  # Lower temperature for more consistent grading
                max_tokens=1500,
                response_format={"type": "json_object"}  # Ensures JSON response
            )
            
            # Parse the response
            result = json.loads(response.choices[0].message.content)
            
            # Add metadata
            result["tokens_used"] = response.usage.total_tokens
            result["cost"] = self._calculate_cost(response.usage.total_tokens, "gpt-4")
            
            return result
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def analyze_speaking(self, transcription: str, audio_duration: float, 
                        task_type: str = "part1", question: str = "") -> Dict[str, Any]:
        """
        Analyze speaking skills from transcription
        
        Args:
            transcription: The text transcription of the audio
            audio_duration: Length of audio in seconds
            task_type: Speaking task type (part1, part2, part3)
            question: The speaking question asked
            
        Returns:
            Dictionary with speaking scores and feedback
        """
        
        prompt = self._build_speaking_analysis_prompt(
            transcription, audio_duration, task_type, question
        )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert IELTS speaking examiner. Analyze speaking performance according to official IELTS speaking band descriptors. Always return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1200,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["tokens_used"] = response.usage.total_tokens
            result["cost"] = self._calculate_cost(response.usage.total_tokens, "gpt-4")
            
            return result
            
        except Exception as e:
            raise Exception(f"Speaking analysis error: {str(e)}")
    
    def _build_essay_grading_prompt(self, content: str, task_type: str, word_count: int) -> str:
        """
        Build a detailed prompt for essay grading
        This is crucial - the prompt determines the quality of AI feedback!
        """
        
        task_specific_criteria = {
            "task1": """
            For IELTS Academic Task 1 (150 words minimum):
            - Task Achievement: Overview, key features, accurate data description
            - Coherence: Logical organization, clear progression
            - Lexical Resource: Vocabulary range and accuracy
            - Grammar: Range and accuracy of structures
            """,
            "task2": """
            For IELTS Academic Task 2 (250 words minimum):
            - Task Response: Position, development, examples, conclusion
            - Coherence: Logical structure, paragraphing, linking
            - Lexical Resource: Vocabulary sophistication and accuracy
            - Grammar: Complex structures, accuracy, range
            """,
            "general": """
            For General Writing:
            - Task Achievement: Purpose, tone, format appropriateness
            - Coherence: Organization and flow
            - Lexical Resource: Vocabulary appropriateness
            - Grammar: Accuracy and range
            """
        }
        
        criteria = task_specific_criteria.get(task_type, task_specific_criteria["general"])
        
        return f"""
Grade this {task_type} essay according to IELTS band descriptors (0-9 scale):

{criteria}

Essay ({word_count} words):
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
    
    def _build_speaking_analysis_prompt(self, transcription: str, duration: float, 
                                      task_type: str, question: str) -> str:
        """
        Build prompt for speaking analysis
        """
        
        return f"""
Analyze this IELTS speaking performance according to official band descriptors:

Speaking Task: {task_type}
Question: {question}
Duration: {duration:.1f} seconds
Transcription: {transcription}

Assess based on these criteria:
- Fluency and Coherence: Flow, pace, hesitation, logical development
- Lexical Resource: Vocabulary range, precision, appropriateness  
- Grammatical Range and Accuracy: Complexity, variety, accuracy
- Pronunciation: Clarity, stress, intonation, intelligibility

Provide assessment in this EXACT JSON format:
{{
    "scores": {{
        "fluency_coherence": 6.5,
        "lexical_resource": 6.0,
        "grammatical_range": 6.5,
        "pronunciation": 7.0,
        "overall_band": 6.5
    }},
    "feedback": {{
        "strengths": [
            "Clear pronunciation",
            "Good vocabulary range"
        ],
        "improvements": [
            "Reduce hesitation",
            "Use more complex grammar"
        ],
        "suggestions": [
            "Practice linking ideas smoothly",
            "Work on sentence variety"
        ],
        "detailed_analysis": {{
            "fluency_coherence": "Generally fluent but some hesitation affects flow...",
            "lexical_resource": "Good range of vocabulary with mostly accurate usage...",
            "grammatical_range": "Uses some complex structures but errors affect communication...",
            "pronunciation": "Generally clear with good word stress..."
        }},
        "speaking_rate": "{len(transcription.split()) / (duration / 60):.1f} words per minute",
        "key_issues": [
            "Frequent use of filler words",
            "Some unclear consonant sounds"
        ]
    }}
}}

Consider speaking rate, pause patterns, and overall communicative effectiveness.
"""
    
    def _calculate_cost(self, tokens: int, model: str) -> float:
        """
        Calculate approximate cost of API call
        """
        # GPT-4 pricing (as of 2024) - update these as needed
        rates = {
            "gpt-4": 0.03 / 1000,  # $0.03 per 1K tokens
            "gpt-3.5-turbo": 0.002 / 1000  # $0.002 per 1K tokens
        }
        
        return tokens * rates.get(model, 0.03 / 1000)

class WhisperService:
    """
    Service for audio transcription using OpenAI Whisper
    """
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
    def transcribe_audio(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file to text using Whisper API
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            Dictionary with transcription and metadata
        """
        
        try:
            # Check if file exists
            if not os.path.exists(audio_file_path):
                raise Exception(f"Audio file not found: {audio_file_path}")
            
            # Open and transcribe audio file
            with open(audio_file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",  # Gets timestamps and confidence
                    language="en"  # Force English for language learning
                )
            
            # Get audio duration (you might want to use a library like librosa for this)
            duration = self._get_audio_duration(audio_file_path)
            
            return {
                "text": transcript.text,
                "duration": duration,
                "language": transcript.language if hasattr(transcript, 'language') else "en",
                "segments": transcript.segments if hasattr(transcript, 'segments') else []
            }
            
        except Exception as e:
            raise Exception(f"Audio transcription failed: {str(e)}")
    
    def _get_audio_duration(self, audio_file_path: str) -> float:
        """
        Get audio file duration in seconds
        For now, returns 0 - you can integrate librosa or similar library
        """
        # TODO: Install and use librosa or similar library
        # import librosa
        # duration = librosa.get_duration(filename=audio_file_path)
        # return duration
        
        # For now, return estimated duration based on file size
        try:
            file_size = os.path.getsize(audio_file_path)
            # Rough estimate: assume 1MB per minute for typical audio
            estimated_duration = (file_size / (1024 * 1024)) * 60
            return min(estimated_duration, 300)  # Cap at 5 minutes
        except:
            return 0.0
