scalars().all()
   
   return {
       "tasks": [
           {
               "id": task.id,
               "title": task.title,
               "difficulty_level": task.difficulty_level,
               "audio_duration": task.audio_duration,
               "created_at": task.created_at.isoformat(),
               "questions_count": len(task.questions)
           }
           for task in tasks
       ]
   }

@router.get("/tasks/{task_id}")
async def get_listening_task(
   task_id: int,
   current_user: User = Depends(get_current_active_user),
   db: AsyncSession = Depends(get_db)
):
   """Get a specific listening task"""
   
   result = await db.execute(
       select(ListeningTask).where(ListeningTask.id == task_id, ListeningTask.is_active == True)
   )
   task = result.scalar_one_or_none()
   
   if not task:
       raise HTTPException(status_code=404, detail="Listening task not found")
   
   return {
       "task": {
           "id": task.id,
           "title": task.title,
           "audio_filename": task.audio_filename,
           "audio_duration": task.audio_duration,
           "questions": task.questions,
           "difficulty_level": task.difficulty_level,
           "created_at": task.created_at.isoformat()
       }
   }

@router.get("/tasks/{task_id}/audio")
async def get_listening_audio(
   task_id: int,
   current_user: User = Depends(get_current_active_user),
   db: AsyncSession = Depends(get_db)
):
   """Get audio file for listening task"""
   
   result = await db.execute(
       select(ListeningTask).where(ListeningTask.id == task_id, ListeningTask.is_active == True)
   )
   task = result.scalar_one_or_none()
   
   if not task:
       raise HTTPException(status_code=404, detail="Listening task not found")
   
   audio_path = os.path.join("uploads", task.audio_filename)
   if not os.path.exists(audio_path):
       raise HTTPException(status_code=404, detail="Audio file not found")
   
   from fastapi.responses import FileResponse
   return FileResponse(audio_path, media_type="audio/mpeg", filename=task.audio_filename)

@router.post("/submit")
async def submit_listening_answers(
   submission_data: ListeningSubmissionCreate,
   current_user: User = Depends(get_current_active_user),
   db: AsyncSession = Depends(get_db)
):
   """Submit answers for a listening comprehension task"""
   
   # Get the task
   task_result = await db.execute(
       select(ListeningTask).where(ListeningTask.id == submission_data.task_id)
   )
   task = task_result.scalar_one_or_none()
   
   if not task:
       raise HTTPException(status_code=404, detail="Listening task not found")
   
   # Create submission
   submission = ListeningSubmission(
       student_id=current_user.id,
       task_id=submission_data.task_id,
       answers=submission_data.answers
   )
   
   db.add(submission)
   await db.commit()
   await db.refresh(submission)
   
   # Grade the submission (simple scoring)
   correct_answers = [answer["correct_answer"] for answer in task.answer_key]
   score = sum(1 for i, answer in enumerate(submission_data.answers) 
               if i < len(correct_answers) and str(answer).lower() == str(correct_answers[i]).lower())
   overall_score = (score / len(correct_answers)) * 9 if correct_answers else 0
   
   # Save grading
   grading = ListeningGrading(
       submission_id=submission.id,
       overall_score=overall_score,
       accuracy_score=overall_score,
       listening_skills={
           "detail_identification": overall_score,
           "gist_understanding": overall_score,
           "inference": overall_score - 0.5,
           "note_taking": overall_score
       },
       feedback={
           "strengths": ["Good listening comprehension"],
           "improvements": ["Practice with different accents"],
           "suggestions": ["Listen to more podcasts and audio materials"]
       },
       lesson_recommendations=[],
       ai_model_used="rule_based"
   )
   
   db.add(grading)
   
   # Update submission
   submission.is_graded = True
   submission.score = overall_score
   submission.graded_at = datetime.utcnow()
   
   await db.commit()
   
   return {
       "message": "Listening submission graded successfully",
       "submission_id": submission.id,
       "score": overall_score,
       "correct_answers": score,
       "total_questions": len(correct_answers),
       "grading": {
           "scores": {
               "overall_score": overall_score,
               "accuracy_score": overall_score,
               "listening_skills": grading.listening_skills
           },
           "feedback": grading.feedback
       }
   }

@router.get("/my-submissions")
async def get_my_listening_submissions(
   current_user: User = Depends(get_current_active_user),
   db: AsyncSession = Depends(get_db)
):
   """Get student's listening submissions"""
   
   result = await db.execute(
       select(ListeningSubmission, ListeningTask, ListeningGrading)
       .join(ListeningTask, ListeningSubmission.task_id == ListeningTask.id)
       .outerjoin(ListeningGrading, ListeningSubmission.id == ListeningGrading.submission_id)
       .where(ListeningSubmission.student_id == current_user.id)
       .order_by(ListeningSubmission.submitted_at.desc())
   )
   
   submissions = result.all()
   
   return {
       "submissions": [
           {
               "id": submission.id,
               "task_title": task.title,
               "task_id": task.id,
               "score": submission.score,
               "is_graded": submission.is_graded,
               "submitted_at": submission.submitted_at.isoformat(),
               "grading": {
                   "overall_score": grading.overall_score,
                   "accuracy_score": grading.accuracy_score,
                   "listening_skills": grading.listening_skills,
                   "feedback": grading.feedback
               } if grading else None
           }
           for submission, task, grading in submissions
       ]
   }
