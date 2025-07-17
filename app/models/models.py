from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class User(Base):
    """Users table - stores student/teacher accounts"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    user_type = Column(String(20), default="student", index=True)
    is_active = Column(Boolean, default=True, index=True)
    is_premium = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    essays = relationship("Essay", back_populates="author", cascade="all, delete-orphan")
    speaking_tasks = relationship("SpeakingTask", back_populates="user", cascade="all, delete-orphan")
    ai_requests = relationship("AIRequest", back_populates="user")

class Essay(Base):
    """Essays table - stores student essay submissions"""
    __tablename__ = "essays"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    task_type = Column(String(50), default="general", index=True)
    word_count = Column(Integer, index=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    is_graded = Column(Boolean, default=False, index=True)
    overall_score = Column(Float, index=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    graded_at = Column(DateTime(timezone=True))
    
    # Relationships
    author = relationship("User", back_populates="essays")
    grading = relationship("EssayGrading", back_populates="essay", uselist=False, cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('ix_essays_author_submitted', 'author_id', 'submitted_at'),
        Index('ix_essays_graded_score', 'is_graded', 'overall_score'),
    )

class EssayGrading(Base):
    """Essay grading results - stores AI feedback"""
    __tablename__ = "essay_gradings"
    
    id = Column(Integer, primary_key=True, index=True)
    essay_id = Column(Integer, ForeignKey("essays.id"), nullable=False, unique=True)
    
    # IELTS band scores
    task_achievement = Column(Float)
    coherence_cohesion = Column(Float)
    lexical_resource = Column(Float)
    grammar_accuracy = Column(Float)
    overall_band = Column(Float, index=True)
    
    # Feedback and metadata
    feedback = Column(JSON)
    ai_model_used = Column(String(50), default="gpt-4")
    processing_time = Column(Float)  # seconds
    tokens_used = Column(Integer)
    cost = Column(Float)  # USD
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    essay = relationship("Essay", back_populates="grading")

class SpeakingTask(Base):
    """Speaking tasks - stores audio submissions"""
    __tablename__ = "speaking_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    task_type = Column(String(50), default="part1", index=True)
    question = Column(Text)
    audio_filename = Column(String(255))
    audio_duration = Column(Float)  # seconds
    transcription = Column(Text)
    is_analyzed = Column(Boolean, default=False, index=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now())
    analyzed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="speaking_tasks")
    analysis = relationship("SpeakingAnalysis", back_populates="speaking_task", uselist=False, cascade="all, delete-orphan")

class SpeakingAnalysis(Base):
    """Speaking analysis results"""
    __tablename__ = "speaking_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    speaking_task_id = Column(Integer, ForeignKey("speaking_tasks.id"), nullable=False, unique=True)
    
    # IELTS speaking scores
    fluency_coherence = Column(Float)
    lexical_resource = Column(Float)
    grammatical_range = Column(Float)
    pronunciation = Column(Float)
    overall_band = Column(Float, index=True)
    
    # Analysis data
    analysis_data = Column(JSON)
    ai_model_used = Column(String(50), default="gpt-4")
    processing_time = Column(Float)
    tokens_used = Column(Integer)
    cost = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    speaking_task = relationship("SpeakingTask", back_populates="analysis")

class AIRequest(Base):
    """Track AI API usage for monitoring and billing"""
    __tablename__ = "ai_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    request_type = Column(String(50), nullable=False, index=True)  # essay_grading, speaking_analysis
    ai_model = Column(String(50), nullable=False)
    status = Column(String(20), default="pending", index=True)  # pending, processing, completed, failed
    tokens_used = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    processing_time = Column(Float)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True))
    
    # Relationships
    user = relationship("User", back_populates="ai_requests")
    
    # Indexes
    __table_args__ = (
        Index('ix_ai_requests_user_type', 'user_id', 'request_type'),
        Index('ix_ai_requests_status_created', 'status', 'created_at'),
    )

class SystemSettings(Base):
    """System-wide settings and configuration"""
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text)
    description = Column(String(255))
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    updated_by = Column(Integer, ForeignKey("users.id"))

class AuditLog(Base):
    """Audit log for tracking important actions"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50))
    resource_id = Column(Integer)
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('ix_audit_logs_user_action', 'user_id', 'action'),
        Index('ix_audit_logs_resource', 'resource_type', 'resource_id'),
    )