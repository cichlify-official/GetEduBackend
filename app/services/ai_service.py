import openai
import json
from typing import Dict, Any
from config.settings import settings

class OpenAIService:
    """Service for AI essay grading using OpenAI GPT-4"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)
    
    def grade_essay(self, content: str, task_type: str = "general", word_count: int = 0) -> Dict[str, Any]:
        """Grade an essay using GPT-4"""
        
        prompt = self._build_grading_prompt(content, task_type, word_count)
        
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
                temperature=0.3,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            result["tokens_used"] = response.usage.total_tokens
            result["cost"] = self._calculate_cost(response.usage.total_tokens)
            
            return result
            
        except Exception as e:
            # Fallback response if OpenAI fails
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
                    "improvements": ["AI grading service unavailable - using demo scores"],
                    "suggestions": ["Please add your OpenAI API key to enable real AI grading"],
                    "detailed_analysis": {
                        "task_achievement": "Demo grading - add OpenAI key for real analysis",
                        "coherence_cohesion": "Demo grading - add OpenAI key for real analysis",
                        "lexical_resource": "Demo grading - add OpenAI key for real analysis",
                        "grammar_accuracy": "Demo grading - add OpenAI key for real analysis"
                    }
                },
                "error": str(e),
                "demo_mode": True
            }
    
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
        # GPT-4 pricing: $0.03 per 1K tokens (approximate)
        return tokens * 0.03 / 1000