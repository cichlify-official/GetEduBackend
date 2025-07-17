from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class UserType(enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"

class TaskType(enum.Enum):
    WRITING = "writing"
    SPEAKING = "speaking"
    READING = "reading"
    LISTENING = "listening"

class ScheduleStatus(enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"

class RescheduleStatus(enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"

class User(Base):
    """Enhanced users table with roles and profiles"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    user_type = Column(Enum(UserType), default=UserType.STUDENT)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    profile_data = Column(JSON, nullable=True)
    
    # Relationships
    essays = relationship("Essay", back_populates="author", foreign_keys="Essay.author_id")
    audio_submissions = relationship("AudioSubmission", back_populates="student")
    reading_submissions = relationship("ReadingSubmission", back_populates="student")
    listening_submissions = relationship("ListeningSubmission", back_populates="student")
    class_schedules = relationship("ClassSchedule", back_populates="student", foreign_keys="ClassSchedule.student_id")
    taught_classes = relationship("ClassSchedule", back_populates="teacher", foreign_keys="ClassSchedule.teacher_id")
    reschedule_requests = relationship("RescheduleRequest", back_populates="student")
    skill_profiles = relationship("SkillProfile", back_populates="user")
    lesson_plans = relationship("LessonPlan", back_populates="student")

class Room(Base):
    """Rooms for class scheduling"""
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    capacity = Column(Integer, default=1)
    is_available = Column(Boolean, default=True)
    equipment = Column(JSON, nullable=True)
    
    # Relationships
    class_schedules = relationship("ClassSchedule", back_populates="room")

class Essay(Base):
    """Enhanced essays table"""
    __tablename__ = "essays"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    task_type = Column(String, default="general")
    word_count = Column(Integer)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_graded = Column(Boolean, default=False)
    overall_score = Column(Float, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    graded_at = Column(DateTime, nullable=True)
    
    # Relationships
    author = relationship("User", back_populates="essays", foreign_keys=[author_id])
    grading = relationship("EssayGrading", back_populates="essay", uselist=False)

class EssayGrading(Base):
    """Essay grading results"""
    __tablename__ = "essay_gradings"
    
    id = Column(Integer, primary_key=True, index=True)
    essay_id = Column(Integer, ForeignKey("essays.id"), nullable=False)
    
    # IELTS band scores
    task_achievement = Column(Float)
    coherence_cohesion = Column(Float)
    lexical_resource = Column(Float)
    grammar_accuracy = Column(Float)
    overall_band = Column(Float)
    
    # Feedback and recommendations
    feedback = Column(JSON)
    lesson_recommendations = Column(JSON)
    ai_model_used = Column(String, default="gpt-4")
    processing_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    essay = relationship("Essay", back_populates="grading")

class AudioSubmission(Base):
    """Speaking task submissions"""
    __tablename__ = "audio_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_type = Column(String, default="general")
    question = Column(Text, nullable=True)
    audio_filename = Column(String, nullable=False)
    audio_duration = Column(Float, nullable=True)
    transcription = Column(Text, nullable=True)
    is_analyzed = Column(Boolean, default=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    analyzed_at = Column(DateTime, nullable=True)
    
    # Relationships
    student = relationship("User", back_populates="audio_submissions")
    analysis = relationship("SpeakingAnalysis", back_populates="audio_submission", uselist=False)

class SpeakingAnalysis(Base):
    """Speaking analysis results"""
    __tablename__ = "speaking_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    audio_submission_id = Column(Integer, ForeignKey("audio_submissions.id"), nullable=False)
    
    # IELTS speaking scores
    fluency_coherence = Column(Float)
    lexical_resource = Column(Float)
    grammatical_range = Column(Float)
    pronunciation = Column(Float)
    overall_band = Column(Float)
    
    # Analysis data
    analysis_data = Column(JSON)
    lesson_recommendations = Column(JSON)
    ai_model_used = Column(String, default="gpt-4")
    processing_time = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    audio_submission = relationship("AudioSubmission", back_populates="analysis")

class ReadingTask(Base):
    """Reading comprehension tasks"""
    __tablename__ = "reading_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    passage = Column(Text, nullable=False)
    questions = Column(JSON, nullable=False)
    answer_key = Column(JSON, nullable=False)
    difficulty_level = Column(String, default="intermediate")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    submissions = relationship("ReadingSubmission", back_populates="task")

class ReadingSubmission(Base):
    """Student reading task submissions"""
    __tablename__ = "reading_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("reading_tasks.id"), nullable=False)
    answers = Column(JSON, nullable=False)
    score = Column(Float, nullable=True)
    is_graded = Column(Boolean, default=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    graded_at = Column(DateTime, nullable=True)
    
    # Relationships
    student = relationship("User", back_populates="reading_submissions")
    task = relationship("ReadingTask", back_populates="submissions")
    grading = relationship("ReadingGrading", back_populates="submission", uselist=False)

class ReadingGrading(Base):
    """Reading comprehension grading results"""
    __tablename__ = "reading_gradings"
    
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("reading_submissions.id"), nullable=False)
    
    # Detailed scoring
    overall_score = Column(Float)
    accuracy_score = Column(Float)
    comprehension_skills = Column(JSON)
    
    # Feedback
    feedback = Column(JSON)
    lesson_recommendations = Column(JSON)
    ai_model_used = Column(String, default="gpt-4")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    submission = relationship("ReadingSubmission", back_populates="grading")

class ListeningTask(Base):
    """Listening comprehension tasks"""
    __tablename__ = "listening_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    audio_filename = Column(String, nullable=False)
    audio_duration = Column(Float, nullable=True)
    transcript = Column(Text, nullable=True)
    questions = Column(JSON, nullable=False)
    answer_key = Column(JSON, nullable=False)
    difficulty_level = Column(String, default="intermediate")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    submissions = relationship("ListeningSubmission", back_populates="task")

class ListeningSubmission(Base):
    """Student listening task submissions"""
    __tablename__ = "listening_submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("listening_tasks.id"), nullable=False)
    answers = Column(JSON, nullable=False)
    score = Column(Float, nullable=True)
    is_graded = Column(Boolean, default=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    graded_at = Column(DateTime, nullable=True)
    
    # Relationships
    student = relationship("User", back_populates="listening_submissions")
    task = relationship("ListeningTask", back_populates="submissions")
    grading = relationship("ListeningGrading", back_populates="submission", uselist=False)

class ListeningGrading(Base):
    """Listening comprehension grading results"""
    __tablename__ = "listening_gradings"
    
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("listening_submissions.id"), nullable=False)
    
    # Detailed scoring
    overall_score = Column(Float)
    accuracy_score = Column(Float)
    listening_skills = Column(JSON)
    
    # Feedback
    feedback = Column(JSON)
    lesson_recommendations = Column(JSON)
    ai_model_used = Column(String, default="gpt-4")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    submission = relationship("ListeningSubmission", back_populates="grading")

class ClassSchedule(Base):
    """Class scheduling system"""
    __tablename__ = "class_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    
    # Schedule details
    scheduled_at = Column(DateTime, nullable=False)
    duration = Column(Integer, default=60)
    subject = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Status
    status = Column(Enum(ScheduleStatus), default=ScheduleStatus.SCHEDULED)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    student = relationship("User", back_populates="class_schedules", foreign_keys=[student_id])
    teacher = relationship("User", back_populates="taught_classes", foreign_keys=[teacher_id])
    room = relationship("Room", back_populates="class_schedules")
    reschedule_requests = relationship("RescheduleRequest", back_populates="original_schedule")

class RescheduleRequest(Base):
    """Rescheduling requests"""
    __tablename__ = "reschedule_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_schedule_id = Column(Integer, ForeignKey("class_schedules.id"), nullable=False)
    
    # Requested changes
    requested_datetime = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=True)
    
    # Status
    status = Column(Enum(RescheduleStatus), default=RescheduleStatus.PENDING)
    teacher_response = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime, nullable=True)
    
    # Relationships
    student = relationship("User", back_populates="reschedule_requests")
    original_schedule = relationship("ClassSchedule", back_populates="reschedule_requests")

class SkillProfile(Base):
    """Individual skill tracking for students"""
    __tablename__ = "skill_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Current skill levels
    writing_level = Column(Float, default=0.0)
    speaking_level = Column(Float, default=0.0)
    reading_level = Column(Float, default=0.0)
    listening_level = Column(Float, default=0.0)
    
    # Skill breakdowns
    writing_skills = Column(JSON)
    speaking_skills = Column(JSON)
    reading_skills = Column(JSON)
    listening_skills = Column(JSON)
    
    # Progress tracking
    strengths = Column(JSON)
    weaknesses = Column(JSON)
    improvement_areas = Column(JSON)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="skill_profiles")

class LessonPlan(Base):
    """AI-generated lesson plans"""
    __tablename__ = "lesson_plans"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Lesson details
    title = Column(String, nullable=False)
    focus_skills = Column(JSON)
    activities = Column(JSON)
    learning_objectives = Column(JSON)
    materials_needed = Column(JSON)
    
    # Difficulty and timing
    difficulty_level = Column(String, default="intermediate")
    estimated_duration = Column(Integer, default=60)
    
    # AI generation info
    generated_by = Column(String, default="gpt-4")
    generation_context = Column(JSON)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    student = relationship("User", back_populates="lesson_plans")

class AIRequest(Base):
    """Track AI API requests for monitoring"""
    __tablename__ = "ai_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    request_type = Column(String, nullable=False)
    ai_model = Column(String, nullable=False)
    
    # Request details
    input_data = Column(JSON, nullable=True)
    output_data = Column(JSON, nullable=True)
    
    # Performance metrics
    tokens_used = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    processing_time = Column(Float, nullable=True)
    
    # Status
    status = Column(String, default="pending")
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
