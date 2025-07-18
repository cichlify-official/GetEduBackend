import re
import json
from typing import Dict, Any, List
from datetime import datetime

class FreeAIService:
    """
    Free, lightweight AI grading service using rule-based analysis
    No external APIs required - perfect for Render deployment!
    """
    
    def __init__(self):
        # Common grammar patterns for analysis
        self.complex_patterns = [
            r'\b(although|however|nevertheless|furthermore|moreover|consequently)\b',
            r'\b(which|who|that|where|when)\b.*,',  # Relative clauses
            r'\b(if|unless|provided|assuming)\b.*,',  # Conditional clauses
            r'\b(because|since|as|due to|owing to)\b',  # Causal relationships
        ]
        
        # Academic vocabulary indicators
        self.academic_vocab = [
            'analyze', 'evaluate', 'demonstrate', 'illustrate', 'furthermore',
            'consequently', 'significant', 'substantial', 'comprehensive',
            'investigate', 'perspective', 'substantial', 'phenomenon',
            'establish', 'framework', 'hypothesis', 'methodology', 'crucial',
            'essential', 'fundamental', 'particularly', 'specifically',
            'obviously', 'clearly', 'evidently', 'undoubtedly', 'certainly'
        ]
        
        # Transition words for coherence
        self.transitions = [
            'firstly', 'secondly', 'finally', 'in conclusion', 'therefore',
            'however', 'moreover', 'furthermore', 'on the other hand',
            'in addition', 'nevertheless', 'consequently', 'as a result',
            'for example', 'for instance', 'such as', 'in particular'
        ]
    
    def grade_essay(self, content: str, task_type: str = "general", word_count: int = 0) -> Dict[str, Any]:
        """Grade an essay using intelligent rule-based analysis"""
        
        if not content.strip():
            return self._get_empty_content_response()
        
        # Calculate word count if not provided
        if word_count == 0:
            word_count = len(content.split())
        
        # Analyze different aspects
        task_score = self._analyze_task_achievement(content, task_type, word_count)
        coherence_score = self._analyze_coherence_cohesion(content)
        lexical_score = self._analyze_lexical_resource(content)
        grammar_score = self._analyze_grammar_accuracy(content)
        
        # Calculate overall band (weighted average)
        overall_band = round((task_score + coherence_score + lexical_score + grammar_score) / 4, 1)
        
        # Generate detailed feedback
        feedback = self._generate_feedback(content, {
            'task_achievement': task_score,
            'coherence_cohesion': coherence_score,
            'lexical_resource': lexical_score,
            'grammar_accuracy': grammar_score
        }, word_count)
        
        return {
            "scores": {
                "task_achievement": task_score,
                "coherence_cohesion": coherence_score,
                "lexical_resource": lexical_score,
                "grammar_accuracy": grammar_score,
                "overall_band": overall_band
            },
            "feedback": feedback,
            "analysis_type": "rule_based",
            "cost": 0.0,  # Free!
            "tokens_used": 0,
            "model": "free_ai_v1"
        }
    
    def _analyze_task_achievement(self, content: str, task_type: str, word_count: int) -> float:
        """Analyze how well the essay achieves the task"""
        score = 5.0  # Base score
        
        # Word count analysis
        if task_type == "task1" and word_count >= 150:
            score += 0.5
        elif task_type == "task2" and word_count >= 250:
            score += 0.5
        elif word_count >= 200:  # General task
            score += 0.5
        
        # Bonus for longer, well-developed essays
        if word_count >= 300:
            score += 0.5
        
        # Structure indicators
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        if len(paragraphs) >= 3:  # Introduction, body, conclusion
            score += 0.5
        
        # Topic development (look for examples and explanations)
        if re.search(r'\b(for example|for instance|such as|including|namely)\b', content.lower()):
            score += 0.5
        
        # Clear position/thesis
        if re.search(r'\b(I believe|in my opinion|this essay will|my view|I think|I argue)\b', content.lower()):
            score += 0.5
        
        # Question addressing indicators
        if re.search(r'\b(discuss|explain|analyze|compare|contrast|describe)\b', content.lower()):
            score += 0.5
        
        return min(score, 9.0)
    
    def _analyze_coherence_cohesion(self, content: str) -> float:
        """Analyze logical flow and linking"""
        score = 5.0
        
        # Count transition words
        transition_count = sum(1 for transition in self.transitions 
                             if transition.lower() in content.lower())
        
        if transition_count >= 5:
            score += 1.5
        elif transition_count >= 3:
            score += 1.0
        elif transition_count >= 1:
            score += 0.5
        
        # Paragraph structure
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        if len(paragraphs) >= 4:  # Well-structured
            score += 0.5
        
        # Sentence variety (different sentence lengths)
        sentences = re.split(r'[.!?]+', content)
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        
        if sentence_lengths:
            length_variety = max(sentence_lengths) - min(sentence_lengths)
            if length_variety > 10:
                score += 0.5
            elif length_variety > 5:
                score += 0.25
        
        # Pronoun reference and cohesion
        if re.search(r'\b(this|these|that|those|it|they)\b', content.lower()):
            score += 0.25
        
        return min(score, 9.0)
    
    def _analyze_lexical_resource(self, content: str) -> float:
        """Analyze vocabulary range and accuracy"""
        score = 5.0
        words = content.lower().split()
        unique_words = set(words)
        
        if len(words) == 0:
            return score
        
        # Vocabulary diversity
        diversity_ratio = len(unique_words) / len(words)
        if diversity_ratio > 0.7:
            score += 1.5
        elif diversity_ratio > 0.6:
            score += 1.0
        elif diversity_ratio > 0.4:
            score += 0.5
        
        # Academic vocabulary
        academic_count = sum(1 for word in self.academic_vocab 
                           if word.lower() in content.lower())
        if academic_count >= 5:
            score += 1.0
        elif academic_count >= 3:
            score += 0.75
        elif academic_count >= 1:
            score += 0.5
        
        # Word length variety (sophisticated vocabulary)
        long_words = [word for word in words if len(word) > 6]
        long_word_ratio = len(long_words) / len(words)
        if long_word_ratio > 0.25:
            score += 0.75
        elif long_word_ratio > 0.15:
            score += 0.5
        
        # Phrasal verbs and collocations
        if re.search(r'\b(carry out|point out|bring about|look into|deal with)\b', content.lower()):
            score += 0.25
        
        return min(score, 9.0)
    
    def _analyze_grammar_accuracy(self, content: str) -> float:
        """Analyze grammatical range and accuracy"""
        score = 5.0
        
        # Complex sentence patterns
        complex_count = sum(1 for pattern in self.complex_patterns 
                          if re.search(pattern, content, re.IGNORECASE))
        
        if complex_count >= 5:
            score += 1.5
        elif complex_count >= 3:
            score += 1.0
        elif complex_count >= 1:
            score += 0.5
        
        # Sentence variety
        sentences = re.split(r'[.!?]+', content)
        valid_sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(valid_sentences) > 8:  # Multiple sentences show variety
            score += 0.5
        
        # Punctuation usage variety
        punct_score = 0
        if ',' in content:
            punct_score += 0.25
        if ';' in content:
            punct_score += 0.25
        if ':' in content:
            punct_score += 0.25
        if re.search(r'["\']', content):  # Quotation marks
            punct_score += 0.25
        
        score += punct_score
        
        # Passive voice usage
        if re.search(r'\b(was|were|is|are|been|being)\s+\w+ed\b', content.lower()):
            score += 0.25
        
        # Conditional sentences
        if re.search(r'\bif\s+.*\s+(would|will|might|could)\b', content.lower()):
            score += 0.25
        
        return min(score, 9.0)
    
    def _generate_feedback(self, content: str, scores: Dict[str, float], word_count: int) -> Dict[str, Any]:
        """Generate detailed, helpful feedback"""
        
        strengths = []
        improvements = []
        suggestions = []
        
        # Analyze strengths
        if scores['task_achievement'] >= 7.0:
            strengths.append("Excellent task response with clear development")
        elif scores['task_achievement'] >= 6.5:
            strengths.append("Good task response and development")
        elif scores['task_achievement'] >= 6.0:
            strengths.append("Adequate task response")
        
        if scores['coherence_cohesion'] >= 7.0:
            strengths.append("Excellent logical structure and flow")
        elif scores['coherence_cohesion'] >= 6.5:
            strengths.append("Clear logical structure and flow")
        
        if scores['lexical_resource'] >= 7.0:
            strengths.append("Wide range of vocabulary used effectively")
        elif scores['lexical_resource'] >= 6.5:
            strengths.append("Good vocabulary range and usage")
        
        if scores['grammar_accuracy'] >= 7.0:
            strengths.append("Wide range of grammar with high accuracy")
        elif scores['grammar_accuracy'] >= 6.5:
            strengths.append("Good grammar with some complexity")
        
        # Analyze improvements needed
        if scores['task_achievement'] < 6.0:
            improvements.append("Develop ideas more fully with specific examples")
            suggestions.append("Add concrete examples to support your main points")
        
        if scores['coherence_cohesion'] < 6.0:
            improvements.append("Use more linking words between ideas")
            suggestions.append("Try transitions like: 'Furthermore', 'However', 'In addition', 'Therefore'")
        
        if scores['lexical_resource'] < 6.0:
            improvements.append("Expand vocabulary range and precision")
            suggestions.append("Use more varied and academic vocabulary")
        
        if scores['grammar_accuracy'] < 6.0:
            improvements.append("Use more complex sentence structures")
            suggestions.append("Try combining sentences with 'which', 'although', 'because', 'while'")
        
        # Word count feedback
        if word_count < 150:
            suggestions.append("Aim for at least 150 words for Task 1 or 250 words for Task 2")
        elif word_count < 200:
            suggestions.append("Consider developing your ideas further with more detail")
        
        # Default messages if lists are empty
        if not strengths:
            strengths.append("Essay shows understanding of the basic task requirements")
        
        if not improvements:
            improvements.append("Continue practicing to refine all areas")
        
        if not suggestions:
            suggestions.append("Keep writing regularly to improve your skills")
        
        return {
            "strengths": strengths,
            "improvements": improvements,
            "suggestions": suggestions,
            "detailed_analysis": {
                "task_achievement": f"Score: {scores['task_achievement']}/9 - " + 
                                  self._get_score_description(scores['task_achievement']),
                "coherence_cohesion": f"Score: {scores['coherence_cohesion']}/9 - " +
                                    self._get_score_description(scores['coherence_cohesion']),
                "lexical_resource": f"Score: {scores['lexical_resource']}/9 - " +
                                  self._get_score_description(scores['lexical_resource']),
                "grammar_accuracy": f"Score: {scores['grammar_accuracy']}/9 - " +
                                  self._get_score_description(scores['grammar_accuracy'])
            },
            "word_count_analysis": f"Word count: {word_count} words",
            "next_steps": [
                "Practice writing essays regularly (aim for 3-4 per week)",
                "Read academic texts to improve vocabulary",
                "Focus on the areas mentioned in improvements",
                "Time yourself to build writing speed and confidence"
            ]
        }
    
    def _get_score_description(self, score: float) -> str:
        """Get description for score range"""
        if score >= 8.0:
            return "Excellent level"
        elif score >= 7.0:
            return "Good level"
        elif score >= 6.0:
            return "Competent level"
        elif score >= 5.0:
            return "Modest level"
        else:
            return "Needs improvement"
    
    def _get_empty_content_response(self) -> Dict[str, Any]:
        """Response for empty content"""
        return {
            "scores": {
                "task_achievement": 0.0,
                "coherence_cohesion": 0.0,
                "lexical_resource": 0.0,
                "grammar_accuracy": 0.0,
                "overall_band": 0.0
            },
            "feedback": {
                "strengths": [],
                "improvements": ["Please provide essay content for analysis"],
                "suggestions": ["Write at least 150 words for meaningful analysis"],
                "detailed_analysis": {
                    "task_achievement": "No content provided",
                    "coherence_cohesion": "No content provided",
                    "lexical_resource": "No content provided",
                    "grammar_accuracy": "No content provided"
                },
                "word_count_analysis": "Word count: 0 words",
                "next_steps": ["Write your essay and submit for analysis"]
            },
            "analysis_type": "rule_based",
            "cost": 0.0,
            "tokens_used": 0,
            "model": "free_ai_v1"
        }