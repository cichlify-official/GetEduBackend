from fastapi import APIRouter, Body
from pydantic import BaseModel

router = APIRouter()

class EvaluationInput(BaseModel):
    grammar: int
    coherence: int
    vocabulary: int
    fluency: int

@router.post("/recommendations")
def evaluate_skills(data: EvaluationInput):
    strengths = []
    weaknesses = []

    for skill, score in data.dict().items():
        if score >= 7:
            strengths.append(skill)
        elif score <= 5:
            weaknesses.append(skill)

    recommendations = []
    for w in weaknesses:
        if w == "grammar":
            recommendations.append("Focus on sentence structure and verb tenses.")
        elif w == "coherence":
            recommendations.append("Practice organizing ideas clearly.")
        elif w == "vocabulary":
            recommendations.append("Learn more topic-specific words.")
        elif w == "fluency":
            recommendations.append("Practice speaking under time constraints.")

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations
    }
