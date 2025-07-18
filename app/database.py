from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON, Enum, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"

class Language(enum.Enum):
    ENGLISH = "english"
    FRENCH = "french"
    SPANISH = "spanish"

class IELTSSection(enum.Enum):
    SPEAKING = "speaking"
    WRITING = "writing"
    READING = "reading"
    LISTENING = "listening"

class ClassStatus(enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    RESCHEDULED = "rescheduled"

class User(Base):
    """Enhanced Users table with role-based access"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.STUDENT, index=True)
    preferred_language = Column(Enum(Language), default=Language.ENGLISH)
    is_active = Column(Boolean, default=True)
    timezone = Column(String, default="UTC")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Student-specific fields
    ielts_target_band = Column(Float, nullable=True)
    current_level = Column(String, nullable=True)  # A1, A2, B1, B2, C1, C2
    
    # Teacher-specific fields
    specializations = Column(JSON, nullable=True)  # ["writing", "speaking", "ielts"]
    hourly_rate = Column(Float, nullable=True)
    
    # Relationships
    essays = relationship("Essay", back_populates="author")
    speaking_tasks = relationship("SpeakingTask", back_populates="student")
    teacher_classes = relationship("Class", back_populates="teacher", foreign_keys="Class.teacher_id")
    student_classes = relationship("Class", back_populates="student", foreign_keys="Class.student_id")
    student_profile = relationship("StudentProfile", back_populates="user", uselist=False)
    teacher_availability = relationship("TeacherAvailability", back_populates="teacher")

class StudentProfile(Base):
    """Detailed student learning profile"""
    __tablename__ = "student_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # IELTS Band Scores
    speaking_band = Column(Float, default=0.0)
    writing_band = Column(Float, default=0.0)
    reading_band = Column(Float, default=0.0)
    listening_band = Column(Float, default=0.0)
    overall_band = Column(Float, default=0.0)
    
    # Skill Analysis
    grammar_score = Column(Float, default=0.0)
    vocabulary_score = Column(Float, default=0.0)
    pronunciation_score = Column(Float, default=0.0)
    fluency_score = Column(Float, default=0.0)
    coherence_score = Column(Float, default=0.0)
    
    # Learning Progress
    total_study_hours = Column(Float, default=0.0)
    essays_completed = Column(Integer, default=0)
    speaking_sessions = Column(Integer, default=0)
    classes_attended = Column(Integer, default=0)
    
    # Weak Areas (JSON array)
    weak_areas = Column(JSON, default=list)
    focus_areas = Column(JSON, default=list)
    
    # Learning Goals
    target_band = Column(Float, nullable=True)
    target_date = Column(DateTime, nullable=True)
    
    # Curriculum
    current_curriculum_id = Column(Integer, ForeignKey("curriculums.id"))
    curriculum_progress = Column(Float, default=0.0)  # Percentage
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="student_profile")
    current_curriculum = relationship("Curriculum", back_populates="students")

class Essay(Base):
    """Enhanced Essays table"""
    __tablename__ = "essays"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    task_type = Column(String, default="task2", index=True)  # task1, task2, general
    language = Column(Enum(Language), default=Language.ENGLISH)
    word_count = Column(Integer)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Grading Status
    is_graded = Column(Boolean, default=False, index=True)
    overall_score = Column(Float, nullable=True)
    ai_model_used = Column(String, nullable=True)
    processing_time = Column(Float, nullable=True)
    
    # Timestamps
    submitted_at = Column(DateTime, default=datetime.utcnow, index=True)
    graded_at = Column(DateTime, nullable=True)
    
    # Class Assignment
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    is_homework = Column(Boolean, default=False)
    
    # Relationships
    author = relationship("User", back_populates="essays")
    grading = relationship("EssayGrading", back_populates="essay", uselist=False)
    assigned_class = relationship("Class", back_populates="homework_essays")

class EssayGrading(Base):
    """Enhanced Essay grading with detailed feedback"""
    __tablename__ = "essay_gradings"
    
    id = Column(Integer, primary_key=True, index=True)
    essay_id = Column(Integer, ForeignKey("essays.id"), nullable=False, unique=True)
    
    # IELTS Band Scores (0-9 scale)
    task_achievement = Column(Float, nullable=False)
    coherence_cohesion = Column(Float, nullable=False)
    lexical_resource = Column(Float, nullable=False)
    grammar_accuracy = Column(Float, nullable=False)
    overall_band = Column(Float, nullable=False, index=True)
    
    # Detailed Analysis
    feedback = Column(JSON, nullable=False)  # Structured feedback
    error_analysis = Column(JSON, nullable=True)  # Grammar/vocabulary errors
    improvement_suggestions = Column(JSON, nullable=True)
    
    # AI Processing Info
    ai_model_used = Column(String, default="gpt-4")
    tokens_used = Column(Integer, default=0)
    processing_cost = Column(Float, default=0.0)
    confidence_score = Column(Float, nullable=True)  # AI confidence in grading
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    essay = relationship("Essay", back_populates="grading")

class SpeakingTask(Base):
    """Speaking evaluation tasks"""
    __tablename__ = "speaking_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Task Details
    task_type = Column(String, nullable=False)  # part1, part2, part3
    question = Column(Text, nullable=False)
    language = Column(Enum(Language), default=Language.ENGLISH)
    
    # Audio Processing
    audio_filename = Column(String, nullable=True)
    audio_duration = Column(Float, nullable=True)  # seconds
    transcription = Column(Text, nullable=True)
    
    # Analysis Status
    is_analyzed = Column(Boolean, default=False, index=True)
    analysis_model = Column(String, nullable=True)
    
    # Class Assignment
    class_id = Column(Integer, ForeignKey("classes.id"), nullable=True)
    
    # Timestamps
    submitted_at = Column(DateTime, default=datetime.utcnow)
    analyzed_at = Column(DateTime, nullable=True)
    
    # Relationships
    student = relationship("User", back_populates="speaking_tasks")
    analysis = relationship("SpeakingAnalysis", back_populates="speaking_task", uselist=False)
    assigned_class = relationship("Class", back_populates="speaking_tasks")

class SpeakingAnalysis(Base):
    """Detailed speaking analysis results"""
    __tablename__ = "speaking_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    speaking_task_id = Column(Integer, ForeignKey("speaking_tasks.id"), nullable=False, unique=True)
    
    # IELTS Speaking Criteria (0-9 scale)
    fluency_coherence = Column(Float, nullable=False)
    lexical_resource = Column(Float, nullable=False)
    grammatical_range = Column(Float, nullable=False)
    pronunciation = Column(Float, nullable=False)
    overall_band = Column(Float, nullable=False, index=True)
    
    # Detailed Metrics
    speech_rate = Column(Float, nullable=True)  # words per minute
    pause_frequency = Column(Float, nullable=True)
    vocabulary_diversity = Column(Float, nullable=True)
    grammar_errors = Column(Integer, default=0)
    
    # Analysis Data
    analysis_data = Column(JSON, nullable=False)  # Detailed feedback
    pronunciation_errors = Column(JSON, nullable=True)
    grammar_issues = Column(JSON, nullable=True)
    
    # AI Processing
    ai_model_used = Column(String, default="whisper+gpt-4")
    processing_time = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    speaking_task = relationship("SpeakingTask", back_populates="analysis")

class Room(Base):
    """Virtual/Physical classroom rooms"""
    __tablename__ = "rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    capacity = Column(Integer, default=1)
    room_type = Column(String, default="virtual")  # virtual, physical
    equipment = Column(JSON, nullable=True)  # ["whiteboard", "audio", "video"]
    is_active = Column(Boolean, default=True)
    
    # Relationships
    classes = relationship("Class", back_populates="room")

class Class(Base):
    """Scheduled classes between teachers and students"""
    __tablename__ = "classes"
    
    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    
    # Schedule
    scheduled_start = Column(DateTime, nullable=False, index=True)
    scheduled_end = Column(DateTime, nullable=False)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    
    # Class Details
    subject = Column(String, nullable=False)  # "IELTS Speaking", "Grammar", "Conversation"
    language = Column(Enum(Language), default=Language.ENGLISH)
    class_type = Column(String, default="individual")  # individual, group
    status = Column(Enum(ClassStatus), default=ClassStatus.SCHEDULED, index=True)
    
    # Content
    lesson_plan = Column(Text, nullable=True)
    homework_assigned = Column(Boolean, default=False)
    
    # Feedback
    teacher_notes = Column(Text, nullable=True)
    student_feedback_rating = Column(Integer, nullable=True)  # 1-5
    student_feedback_comment = Column(Text, nullable=True)
    
    # Pricing
    cost = Column(Float, nullable=True)
    currency = Column(String, default="USD")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    teacher = relationship("User", back_populates="teacher_classes", foreign_keys=[teacher_id])
    student = relationship("User", back_populates="student_classes", foreign_keys=[student_id])
    room = relationship("Room", back_populates="classes")
    homework_essays = relationship("Essay", back_populates="assigned_class")
    speaking_tasks = relationship("SpeakingTask", back_populates="assigned_class")

class TeacherAvailability(Base):
    """Teacher availability schedule"""
    __tablename__ = "teacher_availability"
    
    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Time Slots
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(String, nullable=False)  # "09:00"
    end_time = Column(String, nullable=False)    # "17:00"
    timezone = Column(String, default="UTC")
    
    # Availability Status
    is_available = Column(Boolean, default=True)
    recurring = Column(Boolean, default=True)  # Weekly recurring
    
    # Date Range (for specific availability)
    valid_from = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Unique constraint to prevent overlapping availability
    __table_args__ = (
        UniqueConstraint('teacher_id', 'day_of_week', 'start_time', 'end_time', name='unique_teacher_schedule'),
    )
    
    # Relationships
    teacher = relationship("User", back_populates="teacher_availability")

class Curriculum(Base):
    """AI-generated personalized curriculums"""
    __tablename__ = "curriculums"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Target Settings
    target_language = Column(Enum(Language), nullable=False)
    target_level = Column(String, nullable=False)  # A1, A2, B1, B2, C1, C2
    target_band = Column(Float, nullable=True)  # IELTS target
    duration_weeks = Column(Integer, nullable=False)
    
    # Curriculum Content (AI Generated)
    curriculum_data = Column(JSON, nullable=False)  # Detailed lesson plan
    focus_areas = Column(JSON, nullable=False)  # ["grammar", "vocabulary", "speaking"]
    difficulty_progression = Column(JSON, nullable=False)  # Week-by-week difficulty
    
    # Metadata
    created_by_ai = Column(Boolean, default=True)
    ai_model_used = Column(String, nullable=True)
    generation_prompt = Column(Text, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_template = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    students = relationship("StudentProfile", back_populates="current_curriculum")

class AIRequest(Base):
    """Track all AI API requests for monitoring and cost control"""
    __tablename__ = "ai_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Request Details
    request_type = Column(String, nullable=False, index=True)  # "essay_grading", "speaking_analysis", "curriculum_generation"
    ai_model = Column(String, nullable=False)  # "gpt-4", "whisper", "fallback"
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Cost Tracking
    cost_usd = Column(Float, default=0.0)
    processing_time = Column(Float, nullable=True)
    
    # Status
    status = Column(String, default="pending", index=True)  # pending, completed, failed
    error_message = Column(Text, nullable=True)
    
    # Metadata
    request_data = Column(JSON, nullable=True)  # Input parameters
    response_data = Column(JSON, nullable=True)  # AI response
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User")

# Database Indexes for Performance
# These would be created in Alembic migrations:
# 
# CREATE INDEX idx_essays_author_submitted ON essays (author_id, submitted_at DESC);
# CREATE INDEX idx_classes_teacher_date ON classes (teacher_id, scheduled_start);
# CREATE INDEX idx_classes_student_date ON classes (student_id, scheduled_start);
# CREATE INDEX idx_ai_requests_user_type ON ai_requests (user_id, request_type, created_at);
# CREATE INDEX idx_essay_gradings_band ON essay_gradings (overall_band);
# CREATE INDEX idx_speaking_analyses_band ON speaking_analyses (overall_band);