# alembic/versions/001_initial_migration.py
"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('role', sa.Enum('STUDENT', 'TEACHER', 'ADMIN', name='userrole'), default='STUDENT', nullable=True),
        sa.Column('preferred_language', sa.Enum('ENGLISH', 'FRENCH', 'SPANISH', name='language'), default='ENGLISH', nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=True),
        sa.Column('timezone', sa.String(), default='UTC', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('ielts_target_band', sa.Float(), nullable=True),
        sa.Column('current_level', sa.String(), nullable=True),
        sa.Column('specializations', sa.JSON(), nullable=True),
        sa.Column('hourly_rate', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_role'), 'users', ['role'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # Create student_profiles table
    op.create_table('student_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('speaking_band', sa.Float(), default=0.0, nullable=True),
        sa.Column('writing_band', sa.Float(), default=0.0, nullable=True),
        sa.Column('reading_band', sa.Float(), default=0.0, nullable=True),
        sa.Column('listening_band', sa.Float(), default=0.0, nullable=True),
        sa.Column('overall_band', sa.Float(), default=0.0, nullable=True),
        sa.Column('grammar_score', sa.Float(), default=0.0, nullable=True),
        sa.Column('vocabulary_score', sa.Float(), default=0.0, nullable=True),
        sa.Column('pronunciation_score', sa.Float(), default=0.0, nullable=True),
        sa.Column('fluency_score', sa.Float(), default=0.0, nullable=True),
        sa.Column('coherence_score', sa.Float(), default=0.0, nullable=True),
        sa.Column('total_study_hours', sa.Float(), default=0.0, nullable=True),
        sa.Column('essays_completed', sa.Integer(), default=0, nullable=True),
        sa.Column('speaking_sessions', sa.Integer(), default=0, nullable=True),
        sa.Column('classes_attended', sa.Integer(), default=0, nullable=True),
        sa.Column('weak_areas', sa.JSON(), default=list, nullable=True),
        sa.Column('focus_areas', sa.JSON(), default=list, nullable=True),
        sa.Column('target_band', sa.Float(), nullable=True),
        sa.Column('target_date', sa.DateTime(), nullable=True),
        sa.Column('current_curriculum_id', sa.Integer(), nullable=True),
        sa.Column('curriculum_progress', sa.Float(), default=0.0, nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )

    # Create rooms table
    op.create_table('rooms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('capacity', sa.Integer(), default=1, nullable=True),
        sa.Column('room_type', sa.String(), default='virtual', nullable=True),
        sa.Column('equipment', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create curriculums table
    op.create_table('curriculums',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_language', sa.Enum('ENGLISH', 'FRENCH', 'SPANISH', name='language'), nullable=False),
        sa.Column('target_level', sa.String(), nullable=False),
        sa.Column('target_band', sa.Float(), nullable=True),
        sa.Column('duration_weeks', sa.Integer(), nullable=False),
        sa.Column('curriculum_data', sa.JSON(), nullable=False),
        sa.Column('focus_areas', sa.JSON(), nullable=False),
        sa.Column('difficulty_progression', sa.JSON(), nullable=False),
        sa.Column('created_by_ai', sa.Boolean(), default=True, nullable=True),
        sa.Column('ai_model_used', sa.String(), nullable=True),
        sa.Column('generation_prompt', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=True),
        sa.Column('is_template', sa.Boolean(), default=False, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create teacher_availability table
    op.create_table('teacher_availability',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.String(), nullable=False),
        sa.Column('end_time', sa.String(), nullable=False),
        sa.Column('timezone', sa.String(), default='UTC', nullable=True),
        sa.Column('is_available', sa.Boolean(), default=True, nullable=True),
        sa.Column('recurring', sa.Boolean(), default=True, nullable=True),
        sa.Column('valid_from', sa.DateTime(), nullable=True),
        sa.Column('valid_until', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('teacher_id', 'day_of_week', 'start_time', 'end_time', name='unique_teacher_schedule')
    )
    op.create_index(op.f('ix_teacher_availability_teacher_id'), 'teacher_availability', ['teacher_id'], unique=False)

    # Add foreign key to student_profiles
    op.create_foreign_key(None, 'student_profiles', 'curriculums', ['current_curriculum_id'], ['id'])

    # Create classes table
    op.create_table('classes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('teacher_id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('scheduled_start', sa.DateTime(), nullable=False),
        sa.Column('scheduled_end', sa.DateTime(), nullable=False),
        sa.Column('actual_start', sa.DateTime(), nullable=True),
        sa.Column('actual_end', sa.DateTime(), nullable=True),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('language', sa.Enum('ENGLISH', 'FRENCH', 'SPANISH', name='language'), default='ENGLISH', nullable=True),
        sa.Column('class_type', sa.String(), default='individual', nullable=True),
        sa.Column('status', sa.Enum('SCHEDULED', 'COMPLETED', 'CANCELLED', 'RESCHEDULED', name='classstatus'), default='SCHEDULED', nullable=True),
        sa.Column('lesson_plan', sa.Text(), nullable=True),
        sa.Column('homework_assigned', sa.Boolean(), default=False, nullable=True),
        sa.Column('teacher_notes', sa.Text(), nullable=True),
        sa.Column('student_feedback_rating', sa.Integer(), nullable=True),
        sa.Column('student_feedback_comment', sa.Text(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(), default='USD', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['teacher_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_classes_scheduled_start'), 'classes', ['scheduled_start'], unique=False)
    op.create_index(op.f('ix_classes_status'), 'classes', ['status'], unique=False)
    op.create_index(op.f('ix_classes_student_id'), 'classes', ['student_id'], unique=False)
    op.create_index(op.f('ix_classes_teacher_id'), 'classes', ['teacher_id'], unique=False)

    # Create essays table
    op.create_table('essays',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('task_type', sa.String(), default='task2', nullable=True),
        sa.Column('language', sa.Enum('ENGLISH', 'FRENCH', 'SPANISH', name='language'), default='ENGLISH', nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('is_graded', sa.Boolean(), default=False, nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('ai_model_used', sa.String(), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('graded_at', sa.DateTime(), nullable=True),
        sa.Column('class_id', sa.Integer(), nullable=True),
        sa.Column('is_homework', sa.Boolean(), default=False, nullable=True),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_essays_author_id'), 'essays', ['author_id'], unique=False)
    op.create_index(op.f('ix_essays_is_graded'), 'essays', ['is_graded'], unique=False)
    op.create_index(op.f('ix_essays_submitted_at'), 'essays', ['submitted_at'], unique=False)
    op.create_index(op.f('ix_essays_task_type'), 'essays', ['task_type'], unique=False)

    # Create speaking_tasks table
    op.create_table('speaking_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('task_type', sa.String(), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('language', sa.Enum('ENGLISH', 'FRENCH', 'SPANISH', name='language'), default='ENGLISH', nullable=True),
        sa.Column('audio_filename', sa.String(), nullable=True),
        sa.Column('audio_duration', sa.Float(), nullable=True),
        sa.Column('transcription', sa.Text(), nullable=True),
        sa.Column('is_analyzed', sa.Boolean(), default=False, nullable=True),
        sa.Column('analysis_model', sa.String(), nullable=True),
        sa.Column('class_id', sa.Integer(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['class_id'], ['classes.id'], ),
        sa.ForeignKeyConstraint(['student_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_speaking_tasks_is_analyzed'), 'speaking_tasks', ['is_analyzed'], unique=False)
    op.create_index(op.f('ix_speaking_tasks_student_id'), 'speaking_tasks', ['student_id'], unique=False)

    # Create essay_gradings table
    op.create_table('essay_gradings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('essay_id', sa.Integer(), nullable=False),
        sa.Column('task_achievement', sa.Float(), nullable=False),
        sa.Column('coherence_cohesion', sa.Float(), nullable=False),
        sa.Column('lexical_resource', sa.Float(), nullable=False),
        sa.Column('grammar_accuracy', sa.Float(), nullable=False),
        sa.Column('overall_band', sa.Float(), nullable=False),
        sa.Column('feedback', sa.JSON(), nullable=False),
        sa.Column('error_analysis', sa.JSON(), nullable=True),
        sa.Column('improvement_suggestions', sa.JSON(), nullable=True),
        sa.Column('ai_model_used', sa.String(), default='gpt-4', nullable=True),
        sa.Column('tokens_used', sa.Integer(), default=0, nullable=True),
        sa.Column('processing_cost', sa.Float(), default=0.0, nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['essay_id'], ['essays.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('essay_id')
    )
    op.create_index(op.f('ix_essay_gradings_overall_band'), 'essay_gradings', ['overall_band'], unique=False)

    # Create speaking_analyses table
    op.create_table('speaking_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('speaking_task_id', sa.Integer(), nullable=False),
        sa.Column('fluency_coherence', sa.Float(), nullable=False),
        sa.Column('lexical_resource', sa.Float(), nullable=False),
        sa.Column('grammatical_range', sa.Float(), nullable=False),
        sa.Column('pronunciation', sa.Float(), nullable=False),
        sa.Column('overall_band', sa.Float(), nullable=False),
        sa.Column('speech_rate', sa.Float(), nullable=True),
        sa.Column('pause_frequency', sa.Float(), nullable=True),
        sa.Column('vocabulary_diversity', sa.Float(), nullable=True),
        sa.Column('grammar_errors', sa.Integer(), default=0, nullable=True),
        sa.Column('analysis_data', sa.JSON(), nullable=False),
        sa.Column('pronunciation_errors', sa.JSON(), nullable=True),
        sa.Column('grammar_issues', sa.JSON(), nullable=True),
        sa.Column('ai_model_used', sa.String(), default='whisper+gpt-4', nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['speaking_task_id'], ['speaking_tasks.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('speaking_task_id')
    )
    op.create_index(op.f('ix_speaking_analyses_overall_band'), 'speaking_analyses', ['overall_band'], unique=False)

    # Create ai_requests table
    op.create_table('ai_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('request_type', sa.String(), nullable=False),
        sa.Column('ai_model', sa.String(), nullable=False),
        sa.Column('input_tokens', sa.Integer(), default=0, nullable=True),
        sa.Column('output_tokens', sa.Integer(), default=0, nullable=True),
        sa.Column('total_tokens', sa.Integer(), default=0, nullable=True),
        sa.Column('cost_usd', sa.Float(), default=0.0, nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('status', sa.String(), default='pending', nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('request_data', sa.JSON(), nullable=True),
        sa.Column('response_data', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_requests_created_at'), 'ai_requests', ['created_at'], unique=False)
    op.create_index(op.f('ix_ai_requests_request_type'), 'ai_requests', ['request_type'], unique=False)
    op.create_index(op.f('ix_ai_requests_status'), 'ai_requests', ['status'], unique=False)
    op.create_index(op.f('ix_ai_requests_user_id'), 'ai_requests', ['user_id'], unique=False)

    # Create performance indexes
    op.create_index('idx_essays_author_submitted', 'essays', ['author_id', 'submitted_at'])
    op.create_index('idx_classes_teacher_date', 'classes', ['teacher_id', 'scheduled_start'])
    op.create_index('idx_classes_student_date', 'classes', ['student_id', 'scheduled_start'])
    op.create_index('idx_ai_requests_user_type', 'ai_requests', ['user_id', 'request_type', 'created_at'])

def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_ai_requests_user_type', table_name='ai_requests')
    op.drop_index('idx_classes_student_date', table_name='classes')
    op.drop_index('idx_classes_teacher_date', table_name='classes')
    op.drop_index('idx_essays_author_submitted', table_name='essays')
    
    # Drop tables in reverse order
    op.drop_table('ai_requests')
    op.drop_table('speaking_analyses')
    op.drop_table('essay_gradings')
    op.drop_table('speaking_tasks')
    op.drop_table('essays')
    op.drop_table('classes')
    op.drop_table('teacher_availability')
    op.drop_table('curriculums')
    op.drop_table('rooms')
    op.drop_table('student_profiles')
    op.drop_table('users')
    
    # Drop enums
    op.execute("DROP TYPE IF EXISTS classstatus")
    op.execute("DROP TYPE IF EXISTS language")
    op.execute("DROP TYPE IF EXISTS userrole")

# ===================================
# scripts/init_data.py - Initial Data Setup
# ===================================

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_engine, init_db
from app.models.models import User, Room, Curriculum, UserRole, Language
from app.api.auth.auth import AuthService, UserCreate
from datetime import datetime
import json

async def create_initial_data():
    """Create initial data for the application"""
    
    print("🏗️ Setting up initial data...")
    
    # Initialize database
    await init_db()
    
    async with AsyncSession(async_engine) as db:
        try:
            # Create admin user
            admin_exists = await db.execute(
                select(User).where(User.email == "admin@languageai.com")
            )
            
            if not admin_exists.scalar_one_or_none():
                admin_user = User(
                    email="admin@languageai.com",
                    username="admin",
                    full_name="System Administrator",
                    hashed_password=AuthService.get_password_hash("admin123!"),
                    role=UserRole.ADMIN,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.add(admin_user)
                print("✅ Created admin user: admin@languageai.com / admin123!")
            
            # Create demo teacher
            teacher_exists = await db.execute(
                select(User).where(User.email == "teacher@demo.com")
            )
            
            if not teacher_exists.scalar_one_or_none():
                teacher_user = User(
                    email="teacher@demo.com",
                    username="demo_teacher",
                    full_name="Demo Teacher",
                    hashed_password=AuthService.get_password_hash("teacher123"),
                    role=UserRole.TEACHER,
                    specializations=["IELTS", "Grammar", "Speaking"],
                    hourly_rate=25.0,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.add(teacher_user)
                print("✅ Created demo teacher: teacher@demo.com / teacher123")
            
            # Create demo student
            student_exists = await db.execute(
                select(User).where(User.email == "student@demo.com")
            )
            
            if not student_exists.scalar_one_or_none():
                student_user = User(
                    email="student@demo.com",
                    username="demo_student",
                    full_name="Demo Student",
                    hashed_password=AuthService.get_password_hash("student123"),
                    role=UserRole.STUDENT,
                    current_level="B1",
                    ielts_target_band=7.0,
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.add(student_user)
                print("✅ Created demo student: student@demo.com / student123")
            
            # Create default rooms
            room_names = [
                "Virtual Classroom A",
                "Virtual Classroom B", 
                "Speaking Practice Room",
                "Group Discussion Room",
                "IELTS Preparation Room"
            ]
            
            for room_name in room_names:
                room_exists = await db.execute(
                    select(Room).where(Room.name == room_name)
                )
                
                if not room_exists.scalar_one_or_none():
                    room = Room(
                        name=room_name,
                        capacity=1 if "Group" not in room_name else 6,
                        room_type="virtual",
                        equipment=["audio", "video", "whiteboard", "screen_share"],
                        is_active=True
                    )
                    db.add(room)
            
            print("✅ Created default virtual classrooms")
            
            # Create sample curriculum templates
            curriculum_templates = [
                {
                    "name": "IELTS Beginner to Intermediate",
                    "description": "Complete IELTS preparation for beginners",
                    "target_language": Language.ENGLISH,
                    "target_level": "B1",
                    "target_band": 6.0,
                    "duration_weeks": 12,
                    "focus_areas": ["grammar", "vocabulary", "speaking", "writing"]
                },
                {
                    "name": "IELTS Advanced Preparation",
                    "description": "Advanced IELTS preparation for high scores",
                    "target_language": Language.ENGLISH,
                    "target_level": "C1",
                    "target_band": 7.5,
                    "duration_weeks": 8,
                    "focus_areas": ["advanced_grammar", "academic_vocabulary", "complex_writing"]
                },
                {
                    "name": "French Conversation Basics",
                    "description": "Basic French conversation skills",
                    "target_language": Language.FRENCH,
                    "target_level": "A2",
                    "target_band": None,
                    "duration_weeks": 16,
                    "focus_areas": ["pronunciation", "basic_grammar", "conversation"]
                }
            ]
            
            for template_data in curriculum_templates:
                template_exists = await db.execute(
                    select(Curriculum).where(Curriculum.name == template_data["name"])
                )
                
                if not template_exists.scalar_one_or_none():
                    # Create sample curriculum data
                    curriculum_data = {
                        "curriculum_overview": {
                            "title": template_data["name"],
                            "duration_weeks": template_data["duration_weeks"],
                            "target_improvement": "+1.0 band score",
                            "focus_areas": template_data["focus_areas"]
                        },
                        "weekly_plan": [
                            {
                                "week": i,
                                "theme": f"Week {i} - Progressive Learning",
                                "goals": ["Skill development", "Practice exercises"],
                                "lessons": [
                                    {
                                        "day": j,
                                        "topic": f"Lesson {j}",
                                        "activities": ["Reading", "Writing", "Speaking"],
                                        "duration_minutes": 90,
                                        "homework": "Practice exercises"
                                    } for j in range(1, 4)
                                ],
                                "assessment": f"Week {i} test",
                                "expected_progress": "0.1 band improvement"
                            } for i in range(1, min(template_data["duration_weeks"] + 1, 5))
                        ],
                        "resources": {
                            "textbooks": ["Official Study Materials"],
                            "online_materials": ["Language Learning Platforms"],
                            "practice_tests": ["Mock Exams"]
                        }
                    }
                    
                    curriculum = Curriculum(
                        name=template_data["name"],
                        description=template_data["description"],
                        target_language=template_data["target_language"],
                        target_level=template_data["target_level"],
                        target_band=template_data["target_band"],
                        duration_weeks=template_data["duration_weeks"],
                        curriculum_data=curriculum_data,
                        focus_areas=template_data["focus_areas"],
                        difficulty_progression=[
                            {"week": i, "level": "progressive", "focus": "building"}
                            for i in range(1, template_data["duration_weeks"] + 1, 4)
                        ],
                        created_by_ai=False,
                        is_template=True,
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    db.add(curriculum)
            
            print("✅ Created curriculum templates")
            
            await db.commit()
            print("🎉 Initial data setup complete!")
            
        except Exception as e:
            print(f"❌ Error setting up initial data: {str(e)}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(create_initial_data())

# ===================================
# scripts/seed_demo_data.py - Demo Data for Testing
# ===================================

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import async_engine
from app.models.models import (
    User, Essay, EssayGrading, SpeakingTask, SpeakingAnalysis,
    StudentProfile, TeacherAvailability, Class, ClassStatus
)
from datetime import datetime, timedelta
import random
import json

async def create_demo_data():
    """Create demo data for testing and demonstration"""
    
    print("🎭 Creating demo data...")
    
    async with AsyncSession(async_engine) as db:
        try:
            # Get demo users
            demo_student = await db.execute(
                select(User).where(User.email == "student@demo.com")
            )
            student = demo_student.scalar_one_or_none()
            
            demo_teacher = await db.execute(
                select(User).where(User.email == "teacher@demo.com")
            )
            teacher = demo_teacher.scalar_one_or_none()
            
            if not student or not teacher:
                print("❌ Demo users not found. Run init_data.py first.")
                return
            
            # Create student profile
            profile_exists = await db.execute(
                select(StudentProfile).where(StudentProfile.user_id == student.id)
            )
            
            if not profile_exists.scalar_one_or_none():
                student_profile = StudentProfile(
                    user_id=student.id,
                    speaking_band=5.5,
                    writing_band=6.0,
                    reading_band=6.5,
                    listening_band=6.0,
                    overall_band=6.0,
                    grammar_score=5.5,
                    vocabulary_score=6.0,
                    pronunciation_score=5.5,
                    fluency_score=5.0,
                    coherence_score=6.0,
                    total_study_hours=25.5,
                    essays_completed=3,
                    speaking_sessions=2,
                    classes_attended=5,
                    weak_areas=["grammar", "pronunciation", "fluency"],
                    focus_areas=["speaking", "grammar"],
                    target_band=7.0,
                    target_date=datetime.utcnow() + timedelta(weeks=12),
                    curriculum_progress=25.0,
                    updated_at=datetime.utcnow()
                )
                db.add(student_profile)
                print("✅ Created student profile with progress data")
            
            # Create teacher availability
            availability_exists = await db.execute(
                select(TeacherAvailability).where(TeacherAvailability.teacher_id == teacher.id)
            )
            
            if not availability_exists.scalar_one_or_none():
                # Monday to Friday, 9 AM to 5 PM
                for day in range(5):  # 0-4 = Monday-Friday
                    availability = TeacherAvailability(
                        teacher_id=teacher.id,
                        day_of_week=day,
                        start_time="09:00",
                        end_time="17:00",
                        timezone="UTC",
                        is_available=True,
                        recurring=True,
                        created_at=datetime.utcnow()
                    )
                    db.add(availability)
                print("✅ Created teacher availability schedule")
            
            # Create sample essays with grading
            essay_topics = [
                {
                    "title": "Environmental Protection Essay",
                    "content": """Environmental protection has become one of the most pressing issues of our time. Many people believe that governments should take primary responsibility for protecting the environment, while others argue that individuals must also play a crucial role.

In my opinion, both governments and individuals have important roles to play in environmental protection. Governments have the power to implement large-scale policies such as emissions regulations, renewable energy programs, and environmental protection laws. For example, the Paris Climate Agreement demonstrates how international cooperation can address global environmental challenges.

However, individual actions are equally important. Simple changes like using public transportation, recycling, and reducing energy consumption can have significant cumulative effects. When millions of people make environmentally conscious choices, the impact can be substantial.

In conclusion, environmental protection requires cooperation between governments and individuals. While governments provide the framework and regulations, individual actions ensure that these policies are effective and sustainable.""",
                    "task_type": "task2",
                    "scores": {
                        "task_achievement": 6.5,
                        "coherence_cohesion": 7.0,
                        "lexical_resource": 6.0,
                        "grammar_accuracy": 6.5,
                        "overall_band": 6.5
                    }
                },
                {
                    "title": "Technology in Education",
                    "content": """Technology has revolutionized many aspects of our lives, including education. Some educators believe that traditional teaching methods are more effective, while others advocate for increased use of technology in classrooms.

The integration of technology in education offers numerous benefits. Interactive whiteboards, educational software, and online resources can make learning more engaging and accessible. Students can access vast amounts of information instantly and learn at their own pace through online platforms.

Nevertheless, traditional teaching methods still have value. Face-to-face interaction between teachers and students fosters better communication and allows for immediate feedback. Additionally, some subjects require hands-on practice that cannot be fully replicated through digital means.

I believe the most effective approach combines both traditional and technological methods. This balanced approach can maximize the benefits of both while addressing their respective limitations.""",
                    "task_type": "task2",
                    "scores": {
                        "task_achievement": 6.0,
                        "coherence_cohesion": 6.5,
                        "lexical_resource": 6.5,
                        "grammar_accuracy": 6.0,
                        "overall_band": 6.0
                    }
                }
            ]
            
            for i, essay_data in enumerate(essay_topics):
                essay_exists = await db.execute(
                    select(Essay).where(
                        Essay.author_id == student.id,
                        Essay.title == essay_data["title"]
                    )
                )
                
                if not essay_exists.scalar_one_or_none():
                    essay = Essay(
                        title=essay_data["title"],
                        content=essay_data["content"],
                        task_type=essay_data["task_type"],
                        word_count=len(essay_data["content"].split()),
                        author_id=student.id,
                        is_graded=True,
                        overall_score=essay_data["scores"]["overall_band"],
                        ai_model_used="demo_grading",
                        processing_time=2.5,
                        submitted_at=datetime.utcnow() - timedelta(days=7-i*3),
                        graded_at=datetime.utcnow() - timedelta(days=6-i*3)
                    )
                    db.add(essay)
                    await db.flush()  # Get the essay ID
                    
                    # Create grading
                    grading = EssayGrading(
                        essay_id=essay.id,
                        task_achievement=essay_data["scores"]["task_achievement"],
                        coherence_cohesion=essay_data["scores"]["coherence_cohesion"],
                        lexical_resource=essay_data["scores"]["lexical_resource"],
                        grammar_accuracy=essay_data["scores"]["grammar_accuracy"],
                        overall_band=essay_data["scores"]["overall_band"],
                        feedback={
                            "strengths": ["Clear thesis statement", "Good paragraph structure"],
                            "improvements": ["More varied vocabulary", "Complex sentence structures"],
                            "suggestions": ["Use more linking words", "Provide specific examples"]
                        },
                        ai_model_used="demo_grading",
                        tokens_used=0,
                        processing_cost=0.0,
                        confidence_score=0.85,
                        created_at=datetime.utcnow() - timedelta(days=6-i*3)
                    )
                    db.add(grading)
            
            print("✅ Created sample essays with grading")
            
            # Create sample speaking tasks
            speaking_data = [
                {
                    "task_type": "part2",
                    "question": "Describe a place you would like to visit. You should say: where it is, why you want to visit it, what you would do there, and explain how you think it would be different from your hometown.",
                    "transcription": "I would like to visit Japan, specifically Tokyo. I've always been fascinated by Japanese culture and technology. The city seems to perfectly blend traditional elements with modern innovation. I would love to visit the temples and gardens, try authentic Japanese cuisine, and experience the efficient transportation system. Tokyo appears to be much more organized and technologically advanced compared to my hometown, with its incredible public transport and modern architecture.",
                    "scores": {
                        "fluency_coherence": 6.0,
                        "lexical_resource": 6.5,
                        "grammatical_range": 5.5,
                        "pronunciation": 6.0,
                        "overall_band": 6.0
                    }
                }
            ]
            
            for speaking_item in speaking_data:
                speaking_exists = await db.execute(
                    select(SpeakingTask).where(
                        SpeakingTask.student_id == student.id,
                        SpeakingTask.question == speaking_item["question"]
                    )
                )
                
                if not speaking_exists.scalar_one_or_none():
                    speaking_task = SpeakingTask(
                        student_id=student.id,
                        task_type=speaking_item["task_type"],
                        question=speaking_item["question"],
                        audio_filename="demo_recording.mp3",
                        audio_duration=120.0,
                        transcription=speaking_item["transcription"],
                        is_analyzed=True,
                        analysis_model="demo_analysis",
                        submitted_at=datetime.utcnow() - timedelta(days=3),
                        analyzed_at=datetime.utcnow() - timedelta(days=2)
                    )
                    db.add(speaking_task)
                    await db.flush()
                    
                    # Create analysis
                    analysis = SpeakingAnalysis(
                        speaking_task_id=speaking_task.id,
                        fluency_coherence=speaking_item["scores"]["fluency_coherence"],
                        lexical_resource=speaking_item["scores"]["lexical_resource"],
                        grammatical_range=speaking_item["scores"]["grammatical_range"],
                        pronunciation=speaking_item["scores"]["pronunciation"],
                        overall_band=speaking_item["scores"]["overall_band"],
                        speech_rate=145.0,
                        vocabulary_diversity=0.68,
                        analysis_data={
                            "fluency_coherence": "Good pace with some hesitation",
                            "lexical_resource": "Appropriate vocabulary range",
                            "grammatical_range": "Simple structures used correctly",
                            "pronunciation": "Generally clear with good intonation"
                        },
                        ai_model_used="demo_analysis",
                        processing_time=5.2,
                        confidence_score=0.82,
                        created_at=datetime.utcnow() - timedelta(days=2)
                    )
                    db.add(analysis)
            
            print("✅ Created sample speaking tasks with analysis")
            
            await db.commit()
            print("🎉 Demo data creation complete!")
            
            # Print summary
            print("\n📊 Demo Data Summary:")
            print("- Student profile with progress tracking")
            print("- Teacher availability schedule (Mon-Fri 9-5)")
            print("- 2 graded essays with detailed feedback")
            print("- 1 speaking task with analysis")
            print("- Ready for testing all features!")
            
        except Exception as e:
            print(f"❌ Error creating demo data: {str(e)}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(create_demo_data())