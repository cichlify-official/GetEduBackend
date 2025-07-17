"""Initial migration with all tables

Revision ID: 001
Revises: 
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('user_type', sa.String(length=20), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('is_premium', sa.Boolean(), nullable=True),
        sa.Column('email_verified', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_user_type'), 'users', ['user_type'], unique=False)
    op.create_index(op.f('ix_users_is_active'), 'users', ['is_active'], unique=False)

    # Essays table
    op.create_table('essays',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=True),
        sa.Column('author_id', sa.Integer(), nullable=False),
        sa.Column('is_graded', sa.Boolean(), nullable=True),
        sa.Column('overall_score', sa.Float(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('graded_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_essays_id'), 'essays', ['id'], unique=False)
    op.create_index(op.f('ix_essays_task_type'), 'essays', ['task_type'], unique=False)
    op.create_index(op.f('ix_essays_word_count'), 'essays', ['word_count'], unique=False)
    op.create_index(op.f('ix_essays_author_id'), 'essays', ['author_id'], unique=False)
    op.create_index(op.f('ix_essays_is_graded'), 'essays', ['is_graded'], unique=False)
    op.create_index(op.f('ix_essays_overall_score'), 'essays', ['overall_score'], unique=False)
    op.create_index(op.f('ix_essays_submitted_at'), 'essays', ['submitted_at'], unique=False)
    op.create_index('ix_essays_author_submitted', 'essays', ['author_id', 'submitted_at'], unique=False)
    op.create_index('ix_essays_graded_score', 'essays', ['is_graded', 'overall_score'], unique=False)

    # Essay grading table
    op.create_table('essay_gradings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('essay_id', sa.Integer(), nullable=False),
        sa.Column('task_achievement', sa.Float(), nullable=True),
        sa.Column('coherence_cohesion', sa.Float(), nullable=True),
        sa.Column('lexical_resource', sa.Float(), nullable=True),
        sa.Column('grammar_accuracy', sa.Float(), nullable=True),
        sa.Column('overall_band', sa.Float(), nullable=True),
        sa.Column('feedback', sa.JSON(), nullable=True),
        sa.Column('ai_model_used', sa.String(length=50), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['essay_id'], ['essays.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_essay_gradings_id'), 'essay_gradings', ['id'], unique=False)
    op.create_index(op.f('ix_essay_gradings_essay_id'), 'essay_gradings', ['essay_id'], unique=True)
    op.create_index(op.f('ix_essay_gradings_overall_band'), 'essay_gradings', ['overall_band'], unique=False)

    # Speaking tasks table
    op.create_table('speaking_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=True),
        sa.Column('question', sa.Text(), nullable=True),
        sa.Column('audio_filename', sa.String(length=255), nullable=True),
        sa.Column('audio_duration', sa.Float(), nullable=True),
        sa.Column('transcription', sa.Text(), nullable=True),
        sa.Column('is_analyzed', sa.Boolean(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('analyzed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_speaking_tasks_id'), 'speaking_tasks', ['id'], unique=False)
    op.create_index(op.f('ix_speaking_tasks_user_id'), 'speaking_tasks', ['user_id'], unique=False)
    op.create_index(op.f('ix_speaking_tasks_task_type'), 'speaking_tasks', ['task_type'], unique=False)
    op.create_index(op.f('ix_speaking_tasks_is_analyzed'), 'speaking_tasks', ['is_analyzed'], unique=False)

    # Speaking analyses table
    op.create_table('speaking_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('speaking_task_id', sa.Integer(), nullable=False),
        sa.Column('fluency_coherence', sa.Float(), nullable=True),
        sa.Column('lexical_resource', sa.Float(), nullable=True),
        sa.Column('grammatical_range', sa.Float(), nullable=True),
        sa.Column('pronunciation', sa.Float(), nullable=True),
        sa.Column('overall_band', sa.Float(), nullable=True),
        sa.Column('analysis_data', sa.JSON(), nullable=True),
        sa.Column('ai_model_used', sa.String(length=50), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['speaking_task_id'], ['speaking_tasks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_speaking_analyses_id'), 'speaking_analyses', ['id'], unique=False)
    op.create_index(op.f('ix_speaking_analyses_speaking_task_id'), 'speaking_analyses', ['speaking_task_id'], unique=True)
    op.create_index(op.f('ix_speaking_analyses_overall_band'), 'speaking_analyses', ['overall_band'], unique=False)

    # AI requests table
    op.create_table('ai_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('request_type', sa.String(length=50), nullable=False),
        sa.Column('ai_model', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('cost', sa.Float(), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_requests_id'), 'ai_requests', ['id'], unique=False)
    op.create_index(op.f('ix_ai_requests_user_id'), 'ai_requests', ['user_id'], unique=False)
    op.create_index(op.f('ix_ai_requests_request_type'), 'ai_requests', ['request_type'], unique=False)
    op.create_index(op.f('ix_ai_requests_status'), 'ai_requests', ['status'], unique=False)
    op.create_index(op.f('ix_ai_requests_created_at'), 'ai_requests', ['created_at'], unique=False)
    op.create_index('ix_ai_requests_user_type', 'ai_requests', ['user_id', 'request_type'], unique=False)
    op.create_index('ix_ai_requests_status_created', 'ai_requests', ['status', 'created_at'], unique=False)

    # System settings table
    op.create_table('system_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_system_settings_key'), 'system_settings', ['key'], unique=True)

    # Audit logs table
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)
    op.create_index('ix_audit_logs_user_action', 'audit_logs', ['user_id', 'action'], unique=False)
    op.create_index('ix_audit_logs_resource', 'audit_logs', ['resource_type', 'resource_id'], unique=False)

def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table('audit_logs')
    op.drop_table('system_settings')
    op.drop_table('ai_requests')
    op.drop_table('speaking_analyses')
    op.drop_table('speaking_tasks')
    op.drop_table('essay_gradings')
    op.drop_table('essays')
    op.drop_table('users')