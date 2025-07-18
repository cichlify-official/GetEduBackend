# app/api/routes/writing.py

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel



router = APIRouter()

class WritingInput(BaseModel):
    essay: str

#async def evaluate_writing(data: WritingInput, current_user = Depends(get_current_user)):
 #  if not content:
  #      raise HTTPException(status_code=400, detail="Essay is empty")

    # integrate OpenAI GPT if possible
   # return {"strengths": ["task achievement"], "weaknesses": ["lexical resource"], "raw_scores": {"task": 6.5, "lexical": 5.5}}

