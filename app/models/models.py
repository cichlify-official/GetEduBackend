from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    """Users table - stores student/teacher accounts"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    user_type = Column(String, default="student")  # student, teacher, admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    essays = relationship("Essay", back_populates="author")

class Essay(Base):
    """Essays table - stores student essay submissions"""
    __tablename__ = "essays"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    task_type = Column(String, default="general")  # task1, task2, general
    word_count = Column(Integer)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_graded = Column(Boolean, default=False)
    overall_score = Column(Float, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    author = relationship("User", back_populates="essays")
    grading = relationship("EssayGrading", back_populates="essay", uselist=False)

class EssayGrading(Base):
    """Essay grading results - stores AI feedback"""
    __tablename__ = "essay_gradings"
    
    id = Column(Integer, primary_key=True, index=True)
    essay_id = Column(Integer, ForeignKey("essays.id"), nullable=False)
    
    # IELTS band scores
    task_achievement = Column(Float)
    coherence_cohesion = Column(Float)
    lexical_resource = Column(Float)
    grammar_accuracy = Column(Float)
    overall_band = Column(Float)
    
    # Feedback (JSON format)
    feedback = Column(JSON)
    ai_model_used = Column(String, default="gpt-4")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    essay = relationship("Essay", back_populates="grading")
