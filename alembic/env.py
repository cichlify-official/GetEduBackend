import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context
import asyncio

# Add your project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import your models and settings
from config.settings import settings
from app.models.models import Base

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from environment or settings
database_url = os.getenv("DATABASE_URL") or settings.database_url

# Handle Render's postgres:// URLs
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Set the SQLAlchemy URL
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    
    # Create engine with connection pooling appropriate for production
    connectable = create_engine(
        config.get_main_option("sqlalchemy.url"),
        poolclass=pool.NullPool,  # Good for serverless environments
        echo=False,  # Disable SQL logging in production
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            # Include object names in migration filenames
            include_name=lambda name, type_, parent_names: True,
            # Render schema items with their types
            render_item=lambda type_, obj, autogen_context: obj,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()