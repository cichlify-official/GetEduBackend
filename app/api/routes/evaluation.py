from fastapi import APIRouter, Body
from pydantic import BaseModel

router = APIRouter()

class EvaluationInput(BaseModel):
    student_name: str
    scores: dict  # e.g., {"math": 80, "reading": 65, "writing": 55}

@router.post("/evaluate")
def evaluate(input: EvaluationInput):
    strengths = [k for k, v in input.scores.items() if v >= 70]
    weaknesses = [k for k, v in input.scores.items() if v < 70]
    
    recommendations = [f"Focus on improving your {w} skills." for w in weaknesses]

    return {
        "student": input.student_name,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendations": recommendations
    }
