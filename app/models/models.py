from sqlalchemy import Column, Integer, String, Datetime, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primaty_key=True, index=True)

    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(50), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)

    user_type = Column(String(50), default="student")
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)

    created_at = Column(Datetime, default=datetime.utcnow)
    updated_at = Column(Datetime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    essays = relationship("Essay",back_populates="author")
    speaking_tasks = relationship("SpeakingTask", back_populates="user")
    ai_requests= relationship("AIRequest", back_populates="user")


class Essay(Base):
    __tablename__ = "essays"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(String(255), nullable=False)

    task_type = Column(String(50))
    world_count = Column(Integer)

    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    is_graded = Column(Boolean, default=False)
    overall_score = Column(Float, nullable=True)
    submitted_at = Column(Datetime, default=datetime.utcnow)
    graded_at = Column(Datetime, nullable=True)

    author = relationship("User", back_populates="essays")
    grading_result = relationship("GradingResult", back_populates="essay")


class GradingResult(Base):
    __tablename__ = "essay_gradings"

    id = Column(Integer, primary_key=True, index=True)
    essay_id = Column(Integer, ForeignKey("essays.id"), nullable=False)

    #IELTS/TOEFL BANDS 0.0 TO 9.0
    task_achievement = Column(Float)
    coherence_cohesion = Column(Float)
    lexical_resource = Column(Float)
    grammar_accuracy = Column(Float)
    fluency = Column(Float)
    overall_score = Column(Float)

    feedback = Column(JSON)
    ai_model_used = Column(String(50))
    processing_time = Column(Float)
    created_at = Column(Datetime, default=datetime.utcnow)

    essay = relationship("Essay", back_populates="grading_result")

class SpeakingTask(Base):
    __table__ = "speaking_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    audio_filename = Column(String(255), nullable=False)
    audio_duration = Column(Float)
    task_type = Column(String(255), nullable=False)
    audio_duration = Column(Float)
    task_type = Column(String(50))
    question = Column(Text)
    is_analyzed = Column(Boolean, default=False)
    transcription = Column(Text, nullable=True)
    submitted_at = Column(Datetime, default=datetime.utcnow)
    analyzed_at = Column(Datetime, nullable=True)
    user = relationship("User", back_populates="speaking_tasks")
    analysis = relationship("SpeakingAnalysis", back_populates="speaking_task", uselist=False)

class SpeakingAnalysis(Base):
    __tablename__ = "speaking_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    speaking_task_id = Column(Integer, ForeignKey("speaking_tasks.id"), nullable=False)
    fluency_coherence = Column(Float)
    lexical_resource = Column(Float)
    grammatical_range = Column(Float)
    pronunciation = Column(Float)
    overall_band = Column(Float)
    
    analysis_data = Column(JSON)
    
    ai_model_used = Column(String(50))
    processing_time = Column(Float)
    
    created_at = Column(Datetime, default=datetime.utcnow)
    
    speaking_task = relationship("SpeakingTask", back_populates="analysis")

class AIRequest(Base):
    __tablename__ = "ai_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    request_type = Column(String(50))
    ai_model = Column(String(50))
    tokens_used = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)
    
    status = Column(String(20), default="pending")
    error_message = Column(Text, nullable=True)
    
    created_at = Column(Datetime, default=datetime.utcnow)
    completed_at = Column(Datetime, nullable=True)
    
    user = relationship("User", back_populates="ai_requests")




