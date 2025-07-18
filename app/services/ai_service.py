import re
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta

class EnhancedFreeAIService:
    """
    Enhanced free AI service with comprehensive evaluation and course generation
    """
    
    def __init__(self):
        # Grammar patterns for analysis
        self.complex_patterns = [
            r'\b(although|however|nevertheless|furthermore|moreover|consequently)\b',
            r'\b(which|who|that|where|when)\b.*,',
            r'\b(if|unless|provided|assuming)\b.*,',
            r'\b(because|since|as|due to|owing to)\b',
        ]
        
        # Academic vocabulary
        self.academic_vocab = [
            'analyze', 'evaluate', 'demonstrate', 'illustrate', 'furthermore',
            'consequently', 'significant', 'substantial', 'comprehensive',
            'investigate', 'perspective', 'establish', 'framework', 'hypothesis'
        ]
        
        # Transition words
        self.transitions = [
            'firstly', 'secondly', 'finally', 'in conclusion', 'therefore',
            'however', 'moreover', 'furthermore', 'on the other hand',
            'in addition', 'nevertheless', 'consequently'
        ]
        
        # Skill improvement strategies
        self.improvement_strategies = {
            'task_achievement': {
                'tips': [
                    'Answer all parts of the question directly',
                    'Develop each main point with specific examples',
                    'Ensure your conclusion matches your introduction',
                    'Use relevant, specific details to support arguments'
                ],
                'exercises': [
                    'Practice outlining essays before writing',
                    'Write topic sentences for each paragraph',
                    'Create example banks for common topics'
                ]
            },
            'coherence_cohesion': {
                'tips': [
                    'Use linking words between sentences and paragraphs',
                    'Ensure each paragraph has one clear main idea',
                    'Create logical flow from introduction to conclusion',
                    'Use pronouns and synonyms to avoid repetition'
                ],
                'exercises': [
                    'Practice using transition words daily',
                    'Rewrite paragraphs with better connections',
                    'Study model essay structures'
                ]
            },
            'lexical_resource': {
                'tips': [
                    'Learn 5 new academic words daily',
                    'Use synonyms instead of repeating words',
                    'Practice collocations (word combinations)',
                    'Use more precise vocabulary'
                ],
                'exercises': [
                    'Keep a vocabulary journal',
                    'Practice paraphrasing sentences',
                    'Read academic articles in your field'
                ]
            },
            'grammar_accuracy': {
                'tips': [
                    'Use a variety of sentence structures',
                    'Practice complex sentences with subordinate clauses',
                    'Check verb tenses carefully',
                    'Use conditional sentences appropriately'
                ],
                'exercises': [
                    'Practice sentence combining exercises',
                    'Write complex sentences daily',
                    'Focus on one grammar point per week'
                ]
            }
        }
    
    def evaluate_work(self, content: str, work_type: str = "essay", task_type: str = "general", word_count: int = 0) -> Dict[str, Any]:
        """
        Comprehensive evaluation with strengths, weaknesses, and improvement plan
        """
        if work_type == "essay":
            return self._evaluate_essay(content, task_type, word_count)
        elif work_type == "speaking":
            return self._evaluate_speaking(content)
        else:
            return self._evaluate_general(content)
    
    def _evaluate_essay(self, content: str, task_type: str, word_count: int) -> Dict[str, Any]:
        """Evaluate essay with comprehensive feedback"""
        
        # Basic scoring
        task_score = self._analyze_task_achievement(content, task_type, word_count)
        coherence_score = self._analyze_coherence_cohesion(content)
        lexical_score = self._analyze_lexical_resource(content)
        grammar_score = self._analyze_grammar_accuracy(content)
        
        overall_band = round((task_score + coherence_score + lexical_score + grammar_score) / 4, 1)
        
        scores = {
            'task_achievement': task_score,
            'coherence_cohesion': coherence_score,
            'lexical_resource': lexical_score,
            'grammar_accuracy': grammar_score,
            'overall_band': overall_band
        }
        
        # Identify strengths and weaknesses
        strengths, weaknesses = self._identify_strengths_weaknesses(scores, content)
        
        # Generate personalized course
        course = self._generate_improvement_course(scores, weaknesses)
        
        return {
            "scores": scores,
            "evaluation": {
                "strengths": strengths,
                "weaknesses": weaknesses,
                "focus_areas": [area for area, score in scores.items() if score < 6.0 and area != 'overall_band'],
                "next_level_targets": self._get_next_level_targets(scores)
            },
            "improvement_course": course,
            "analysis_type": "comprehensive_ai",
            "cost": 0.0
        }
    
    def _evaluate_speaking(self, transcription: str) -> Dict[str, Any]:
        """Evaluate speaking performance"""
        
        words = transcription.split()
        word_count = len(words)
        
        # Speaking-specific scoring
        fluency_score = self._analyze_fluency(transcription)
        lexical_score = self._analyze_lexical_resource(transcription)
        grammar_score = self._analyze_grammar_accuracy(transcription)
        pronunciation_score = 6.5  # Demo score for transcribed text
        
        overall_band = round((fluency_score + lexical_score + grammar_score + pronunciation_score) / 4, 1)
        
        scores = {
            'fluency_coherence': fluency_score,
            'lexical_resource': lexical_score,
            'grammatical_range': grammar_score,
            'pronunciation': pronunciation_score,
            'overall_band': overall_band
        }
        
        strengths, weaknesses = self._identify_speaking_strengths_weaknesses(scores, transcription)
        course = self._generate_speaking_course(scores, weaknesses)
        
        return {
            "scores": scores,
            "evaluation": {
                "strengths": strengths,
                "weaknesses": weaknesses,
                "word_count": word_count,
                "speaking_time": f"{word_count // 2} seconds (estimated)",
                "pace_analysis": "Good pace" if 100 <= word_count <= 200 else "Consider adjusting pace"
            },
            "improvement_course": course,
            "analysis_type": "speaking_analysis"
        }
    
    def _identify_strengths_weaknesses(self, scores: Dict[str, float], content: str) -> tuple:
        """Identify specific strengths and weaknesses"""
        
        strengths = []
        weaknesses = []
        
        # Analyze each skill area
        for skill, score in scores.items():
            if skill == 'overall_band':
                continue
                
            if score >= 7.0:
                strengths.append(self._get_strength_feedback(skill, score, content))
            elif score < 6.0:
                weaknesses.append(self._get_weakness_feedback(skill, score, content))
        
        # Add content-specific observations
        if len(content.split()) > 250:
            strengths.append("Good essay length - shows ability to develop ideas")
        
        if any(word in content.lower() for word in self.academic_vocab):
            strengths.append("Uses some academic vocabulary appropriately")
        
        return strengths, weaknesses
    
    def _identify_speaking_strengths_weaknesses(self, scores: Dict[str, float], transcription: str) -> tuple:
        """Identify speaking-specific strengths and weaknesses"""
        
        strengths = []
        weaknesses = []
        
        word_count = len(transcription.split())
        
        if word_count > 150:
            strengths.append("Good speaking length - shows fluency")
        elif word_count < 80:
            weaknesses.append("Speaking too briefly - try to expand your answers")
        
        if scores['fluency_coherence'] >= 6.5:
            strengths.append("Generally fluent speech with good coherence")
        else:
            weaknesses.append("Work on speaking more fluently and connecting ideas")
        
        if scores['lexical_resource'] >= 6.5:
            strengths.append("Good vocabulary range for speaking")
        else:
            weaknesses.append("Expand vocabulary for more precise expression")
        
        return strengths, weaknesses
    
    def _generate_improvement_course(self, scores: Dict[str, float], weaknesses: List[str]) -> Dict[str, Any]:
        """Generate personalized improvement course"""
        
        # Identify weakest areas
        skill_scores = {k: v for k, v in scores.items() if k != 'overall_band'}
        weakest_skill = min(skill_scores.items(), key=lambda x: x[1])
        
        # Determine study period
        current_level = scores['overall_band']
        target_level = current_level + 0.5
        study_weeks = max(4, int((target_level - current_level) * 8))
        
        course = {
            "title": f"Personalized Improvement Plan - {study_weeks} Week Program",
            "current_level": current_level,
            "target_level": target_level,
            "estimated_duration": f"{study_weeks} weeks",
            "primary_focus": weakest_skill[0].replace('_', ' ').title(),
            "weekly_plan": self._create_weekly_plan(weakest_skill[0], study_weeks),
            "daily_activities": self._get_daily_activities(weakest_skill[0]),
            "progress_milestones": self._create_milestones(study_weeks, current_level, target_level),
            "resources": self._get_learning_resources(weakest_skill[0])
        }
        
        return course
    
    def _generate_speaking_course(self, scores: Dict[str, float], weaknesses: List[str]) -> Dict[str, Any]:
        """Generate speaking-specific improvement course"""
        
        weakest_skill = min(scores.items(), key=lambda x: x[1] if x[0] != 'overall_band' else 10)
        study_weeks = 6  # Standard speaking improvement period
        
        return {
            "title": f"Speaking Improvement Plan - {study_weeks} Week Program",
            "current_level": scores['overall_band'],
            "target_level": scores['overall_band'] + 0.5,
            "estimated_duration": f"{study_weeks} weeks",
            "primary_focus": "Speaking Fluency and Accuracy",
            "weekly_plan": self._create_speaking_weekly_plan(study_weeks),
            "daily_practice": [
                "15 minutes speaking practice daily",
                "Record yourself speaking on different topics",
                "Practice pronunciation with tongue twisters",
                "Shadow native speakers (repeat after them)"
            ],
            "progress_milestones": [
                "Week 2: Speak for 2 minutes without stopping",
                "Week 4: Use 10 new vocabulary words naturally",
                "Week 6: Complete a full speaking test simulation"
            ]
        }
    
    def _create_weekly_plan(self, focus_skill: str, weeks: int) -> List[Dict[str, str]]:
        """Create detailed weekly study plan"""
        
        base_activities = self.improvement_strategies.get(focus_skill, {})
        
        plan = []
        for week in range(1, weeks + 1):
            week_focus = self._get_week_focus(focus_skill, week, weeks)
            plan.append({
                "week": week,
                "focus": week_focus,
                "goals": self._get_weekly_goals(focus_skill, week),
                "activities": self._get_weekly_activities(focus_skill, week)
            })
        
        return plan
    
    def _create_speaking_weekly_plan(self, weeks: int) -> List[Dict[str, str]]:
        """Create speaking-specific weekly plan"""
        
        speaking_plan = [
            {"week": 1, "focus": "Basic Fluency", "activities": ["Daily 5-minute monologues", "Shadowing exercises"]},
            {"week": 2, "focus": "Vocabulary Building", "activities": ["Learn topic-specific words", "Practice using new words"]},
            {"week": 3, "focus": "Grammar in Speech", "activities": ["Complex sentence practice", "Error correction"]},
            {"week": 4, "focus": "Coherence", "activities": ["Linking words practice", "Story telling"]},
            {"week": 5, "focus": "Pronunciation", "activities": ["Sound drills", "Stress patterns"]},
            {"week": 6, "focus": "Test Practice", "activities": ["Full speaking tests", "Self evaluation"]}
        ]
        
        return speaking_plan[:weeks]
    
    def _get_week_focus(self, skill: str, week: int, total_weeks: int) -> str:
        """Get focus area for specific week"""
        
        focus_map = {
            'task_achievement': [
                "Understanding task requirements",
                "Developing main ideas",
                "Adding supporting details",
                "Improving conclusions"
            ],
            'coherence_cohesion': [
                "Paragraph structure",
                "Linking words",
                "Logical flow",
                "Cohesive devices"
            ],
            'lexical_resource': [
                "Basic vocabulary expansion",
                "Academic word usage",
                "Collocations practice",
                "Precise word choice"
            ],
            'grammar_accuracy': [
                "Sentence variety",
                "Complex structures",
                "Verb tenses",
                "Error correction"
            ]
        }
        
        focuses = focus_map.get(skill, ["General improvement"])
        return focuses[(week - 1) % len(focuses)]
    
    def _get_daily_activities(self, skill: str) -> List[str]:
        """Get daily practice activities"""
        
        activities = {
            'task_achievement': [
                "Read and analyze essay questions (15 mins)",
                "Practice outlining essays (10 mins)",
                "Write one paragraph with examples (20 mins)"
            ],
            'coherence_cohesion': [
                "Practice using 3 linking words (10 mins)",
                "Rewrite sentences for better flow (15 mins)",
                "Study paragraph structures (10 mins)"
            ],
            'lexical_resource': [
                "Learn 5 new academic words (15 mins)",
                "Practice word collocations (10 mins)",
                "Use new words in sentences (15 mins)"
            ],
            'grammar_accuracy': [
                "Write 5 complex sentences (15 mins)",
                "Grammar exercises (20 mins)",
                "Proofread and correct errors (10 mins)"
            ]
        }
        
        return activities.get(skill, ["General practice (30 mins)"])
    
    def _create_milestones(self, weeks: int, current: float, target: float) -> List[str]:
        """Create progress milestones"""
        
        milestones = []
        increment = (target - current) / (weeks // 2)
        
        for i in range(weeks // 2):
            week = (i + 1) * 2
            level = current + (increment * (i + 1))
            milestones.append(f"Week {week}: Reach level {level:.1f}")
        
        return milestones
    
    def _get_learning_resources(self, skill: str) -> List[str]:
        """Get learning resources for specific skill"""
        
        resources = {
            'task_achievement': [
                "IELTS task analysis worksheets",
                "Sample high-scoring essays",
                "Question type practice materials"
            ],
            'coherence_cohesion': [
                "Linking words reference lists",
                "Paragraph structure templates",
                "Essay organization guides"
            ],
            'lexical_resource': [
                "Academic vocabulary lists",
                "Collocation dictionaries",
                "Vocabulary building apps"
            ],
            'grammar_accuracy': [
                "Grammar reference books",
                "Sentence structure guides",
                "Error correction exercises"
            ]
        }
        
        return resources.get(skill, ["General IELTS preparation materials"])
    
    # Helper methods for scoring (keeping existing logic)
    def _analyze_task_achievement(self, content: str, task_type: str, word_count: int) -> float:
        score = 5.0
        if task_type == "task1" and word_count >= 150:
            score += 0.5
        elif task_type == "task2" and word_count >= 250:
            score += 0.5
        elif word_count >= 200:
            score += 0.5
        
        paragraphs = content.split('\n\n')
        if len(paragraphs) >= 3:
            score += 0.5
        
        if re.search(r'\b(for example|for instance|such as|including)\b', content.lower()):
            score += 0.5
        
        if re.search(r'\b(I believe|in my opinion|this essay will|my view)\b', content.lower()):
            score += 0.5
        
        return min(score, 9.0)
    
    def _analyze_coherence_cohesion(self, content: str) -> float:
        score = 5.0
        transition_count = sum(1 for transition in self.transitions 
                             if transition.lower() in content.lower())
        
        if transition_count >= 3:
            score += 1.0
        elif transition_count >= 1:
            score += 0.5
        
        paragraphs = content.split('\n\n')
        if len(paragraphs) >= 4:
            score += 0.5
        
        sentences = re.split(r'[.!?]+', content)
        sentence_lengths = [len(s.split()) for s in sentences if s.strip()]
        if sentence_lengths and max(sentence_lengths) - min(sentence_lengths) > 5:
            score += 0.5
        
        return min(score, 9.0)
    
    def _analyze_lexical_resource(self, content: str) -> float:
        score = 5.0
        words = content.lower().split()
        unique_words = set(words)
        
        if len(words) > 0:
            diversity_ratio = len(unique_words) / len(words)
            if diversity_ratio > 0.6:
                score += 1.0
            elif diversity_ratio > 0.4:
                score += 0.5
        
        academic_count = sum(1 for word in self.academic_vocab 
                           if word.lower() in content.lower())
        if academic_count >= 3:
            score += 1.0
        elif academic_count >= 1:
            score += 0.5
        
        long_words = [word for word in words if len(word) > 6]
        if len(long_words) / len(words) > 0.2:
            score += 0.5
        
        return min(score, 9.0)
    
    def _analyze_grammar_accuracy(self, content: str) -> float:
        score = 5.0
        
        complex_count = sum(1 for pattern in self.complex_patterns 
                          if re.search(pattern, content, re.IGNORECASE))
        
        if complex_count >= 3:
            score += 1.0
        elif complex_count >= 1:
            score += 0.5
        
        sentences = re.split(r'[.!?]+', content)
        if len(sentences) > 5:
            score += 0.5
        
        if ',' in content and ';' in content:
            score += 0.5
        
        return min(score, 9.0)
    
    def _analyze_fluency(self, transcription: str) -> float:
        """Analyze speaking fluency from transcription"""
        words = transcription.split()
        sentences = re.split(r'[.!?]+', transcription)
        
        score = 5.0
        
        # Word count indicates fluency
        if len(words) > 150:
            score += 1.0
        elif len(words) > 100:
            score += 0.5
        
        # Sentence variety
        if len(sentences) > 5:
            score += 0.5
        
        # Use of fillers (negative indicator)
        fillers = ['um', 'uh', 'like', 'you know']
        filler_count = sum(transcription.lower().count(filler) for filler in fillers)
        if filler_count < 3:
            score += 0.5
        
        return min(score, 9.0)
    
    def _get_strength_feedback(self, skill: str, score: float, content: str) -> str:
        """Generate specific strength feedback"""
        
        feedback_map = {
            'task_achievement': f"Strong task response (Score: {score}) - you address the question well",
            'coherence_cohesion': f"Good organization (Score: {score}) - your ideas flow logically",
            'lexical_resource': f"Good vocabulary usage (Score: {score}) - varied and appropriate word choice",
            'grammar_accuracy': f"Strong grammar (Score: {score}) - complex structures used effectively"
        }
        
        return feedback_map.get(skill, f"Good performance in {skill}")
    
    def _get_weakness_feedback(self, skill: str, score: float, content: str) -> str:
        """Generate specific weakness feedback"""
        
        feedback_map = {
            'task_achievement': f"Task response needs work (Score: {score}) - develop ideas more fully",
            'coherence_cohesion': f"Organization could improve (Score: {score}) - use more linking words",
            'lexical_resource': f"Vocabulary needs expansion (Score: {score}) - learn more academic words",
            'grammar_accuracy': f"Grammar needs attention (Score: {score}) - practice complex structures"
        }
        
        return feedback_map.get(skill, f"Area for improvement: {skill}")
    
    def _get_weekly_goals(self, skill: str, week: int) -> List[str]:
        """Get specific goals for the week"""
        
        goals_map = {
            'task_achievement': [
                "Understand all parts of essay questions",
                "Write clear topic sentences",
                "Develop ideas with specific examples",
                "Write stronger conclusions"
            ],
            'coherence_cohesion': [
                "Use 5 different linking words",
                "Write well-structured paragraphs",
                "Create logical flow between ideas",
                "Use cohesive devices effectively"
            ],
            'lexical_resource': [
                "Learn 20 new academic words",
                "Use synonyms effectively",
                "Practice word collocations",
                "Avoid word repetition"
            ],
            'grammar_accuracy': [
                "Write complex sentences",
                "Use various tenses correctly",
                "Practice conditional structures",
                "Eliminate common errors"
            ]
        }
        
        goals = goals_map.get(skill, ["Improve general skills"])
        return [goals[(week - 1) % len(goals)]]
    
    def _get_weekly_activities(self, skill: str, week: int) -> List[str]:
        """Get specific activities for the week"""
        
        activities = self.improvement_strategies.get(skill, {}).get('exercises', ["General practice"])
        return activities
    
    def _get_next_level_targets(self, scores: Dict[str, float]) -> Dict[str, float]:
        """Calculate next level targets for each skill"""
        
        targets = {}
        for skill, score in scores.items():
            if skill != 'overall_band':
                targets[skill] = min(score + 0.5, 9.0)
        
        return targets