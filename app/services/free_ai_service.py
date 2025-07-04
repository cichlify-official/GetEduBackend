import re
import json
from typing import Dict, Any, List
from datetime import datetime

class FreeAIService:
    """
    Free, open-source AI grading service using rule-based analysis
    No external APIs required!
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
            'establish', 'framework', 'hypothesis', 'methodology'
        ]
        
        # Transition words for coherence
        self.transitions = [
            'firstly', 'secondly', 'finally', 'in conclusion', 'therefore',
            'however', 'moreover', 'furthermore', 'on the other hand',
            'in addition', 'nevertheless', 'consequently'
        ]
    
    def grade_essay(self, content: str, task_type: str = "general", word_count: int = 0) -> Dict[str, Any]:
        """Grade an essay using intelligent rule-based analysis"""
        
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
        })
        
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
            "tokens_used": 0
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
        
        # Structure indicators
        paragraphs = content.split('\n\n')
        if len(paragraphs) >= 3:  # Introduction, body, conclusion
            score += 0.5
        
        # Topic development (look for examples and explanations)
        if re.search(r'\b(for example|for instance|such as|including)\b', content.lower()):
            score += 0.5
        
        # Clear position/thesis
        if re.search(r'\b(I believe|in my opinion|this essay will|my view)\b', content.lower()):
            score += 0.5
        
        return min(score, 9.0)
    
    def _analyze_coherence_cohesion(self, content: str) -> float:
        """Analyze logical flow and linking"""
        score = 5.0
        
        # Count transition words
        transition_count = sum(1 for transition in self.transitions 
                             if transition.lower() in content.lower())
        
        if transition_count >= 3:
            score += 1.0
        elif transition_count >= 1:
            score += 0.5
        
        # Paragraph structure
        paragraphs = content.split('\n\n')
        if len(paragraphs) >= 4:  # Well-structured
            score += 0.5
        
        # Sentence variety (different sentence lengths)
        sentences = re.split(r'[.!?]+', content)
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        if sentence_lengths and max(sentence_lengths) - min(sentence_lengths) > 5:
            score += 0.5
        
        return min(score, 9.0)
    
    def _analyze_lexical_resource(self, content: str) -> float:
        """Analyze vocabulary range and accuracy"""
        score = 5.0
        words = content.lower().split()
        unique_words = set(words)
        
        # Vocabulary diversity
        if len(words) > 0:
            diversity_ratio = len(unique_words) / len(words)
            if diversity_ratio > 0.6:
                score += 1.0
            elif diversity_ratio > 0.4:
                score += 0.5
        
        # Academic vocabulary
        academic_count = sum(1 for word in self.academic_vocab 
                           if word.lower() in content.lower())
        if academic_count >= 3:
            score += 1.0
        elif academic_count >= 1:
            score += 0.5
        
        # Word length variety (sophisticated vocabulary)
        long_words = [word for word in words if len(word) > 6]
        if len(long_words) / len(words) > 0.2:
            score += 0.5
        
        return min(score, 9.0)
    
    def _analyze_grammar_accuracy(self, content: str) -> float:
        """Analyze grammatical range and accuracy"""
        score = 5.0
        
        # Complex sentence patterns
        complex_count = sum(1 for pattern in self.complex_patterns 
                          if re.search(pattern, content, re.IGNORECASE))
        
        if complex_count >= 3:
            score += 1.0
        elif complex_count >= 1:
            score += 0.5
        
        # Sentence variety
        sentences = re.split(r'[.!?]+', content)
        if len(sentences) > 5:  # Multiple sentences show variety
            score += 0.5
        
        # Punctuation usage
        if ',' in content and ';' in content:
            score += 0.5
        
        return min(score, 9.0)
    
    def _generate_feedback(self, content: str, scores: Dict[str, float]) -> Dict[str, Any]:
        """Generate detailed, helpful feedback"""
        
        strengths = []
        improvements = []
        suggestions = []
        
        # Analyze strengths
        if scores['task_achievement'] >= 6.5:
            strengths.append("Good task response and development")
        if scores['coherence_cohesion'] >= 6.5:
            strengths.append("Clear logical structure and flow")
        if scores['lexical_resource'] >= 6.5:
            strengths.append("Good vocabulary range and usage")
        if scores['grammar_accuracy'] >= 6.5:
            strengths.append("Accurate grammar with some complexity")
        
        # Analyze improvements needed
        if scores['task_achievement'] < 6.0:
            improvements.append("Develop ideas more fully with examples")
            suggestions.append("Add specific examples to support your points")
        
        if scores['coherence_cohesion'] < 6.0:
            improvements.append("Use more linking words between ideas")
            suggestions.append("Try: 'Furthermore', 'However', 'In addition'")
        
        if scores['lexical_resource'] < 6.0:
            improvements.append("Expand vocabulary range")
            suggestions.append("Use more varied and academic vocabulary")
        
        if scores['grammar_accuracy'] < 6.0:
            improvements.append("Use more complex sentence structures")
            suggestions.append("Try combining sentences with 'which', 'although', 'because'")
        
        # General suggestions
        word_count = len(content.split())
        if word_count < 200:
            suggestions.append("Aim for more detailed development (200+ words)")
        
        return {
            "strengths": strengths or ["Essay shows basic understanding of the task"],
            "improvements": improvements or ["Continue practicing to improve all areas"],
            "suggestions": suggestions or ["Keep writing and practicing regularly"],
            "detailed_analysis": {
                "task_achievement": f"Score: {scores['task_achievement']}/9 - " + 
                                  ("Good task response" if scores['task_achievement'] >= 6.0 else "Needs more development"),
                "coherence_cohesion": f"Score: {scores['coherence_cohesion']}/9 - " +
                                    ("Good organization" if scores['coherence_cohesion'] >= 6.0 else "Needs better linking"),
                "lexical_resource": f"Score: {scores['lexical_resource']}/9 - " +
                                  ("Good vocabulary" if scores['lexical_resource'] >= 6.0 else "Needs more variety"),
                "grammar_accuracy": f"Score: {scores['grammar_accuracy']}/9 - " +
                                  ("Good grammar" if scores['grammar_accuracy'] >= 6.0 else "Needs more complexity")
            },
            "word_count_analysis": f"Word count: {word_count} words",
            "next_steps": [
                "Practice writing essays regularly",
                "Read academic texts to improve vocabulary",
                "Focus on the specific areas mentioned above"
            ]
        }
