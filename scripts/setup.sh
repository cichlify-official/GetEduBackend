echo "🚀 Setting up Language Learning AI Backend..."

# Create virtual environment
echo "📦 Creating virtual environment..."
python -m venv venv

# Activate virtual environment (platform-specific)
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi

# Install dependencies
echo "📚 Installing Python dependencies..."
pip install -r requirements.txt

# Copy environment file
echo "⚙️ Setting up environment variables..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Created .env file - please edit it with your API keys!"
else
    echo "✅ .env file already exists"
fi

# Initialize Alembic
echo "🗃️ Setting up database migrations..."
alembic init alembic

# Create initial migration
echo "📝 Creating initial database migration..."
alembic revision --autogenerate -m "Initial migration"

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your OpenAI API key"
echo "2. Run 'docker-compose up' to start all services"
echo "3. Run 'alembic upgrade head' to create database tables"
echo "4. Visit http://localhost:8000/docs for API documentation"

---

#!/bin/bash
# scripts/dev.sh - Start development environment

echo "🔥 Starting development environment..."

# Start Docker services in background
docker-compose up -d postgres redis

# Wait for services to be ready
echo "⏳ Waiting for database and Redis..."
sleep 5

# Run database migrations
echo "🗃️ Running database migrations..."
alembic upgrade head

# Start FastAPI in development mode
echo "🚀 Starting FastAPI server..."
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

---

#!/bin/bash
# scripts/worker.sh - Start Celery worker

echo "👷 Starting Celery worker..."

# Make sure Redis is running
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running. Start it with: docker-compose up -d redis"
    exit 1
fi

# Start Celery worker
celery -A workers.celery_app worker --loglevel=info --queues=ai_tasks

---

#!/bin/bash
# scripts/test.sh - Run tests

echo "🧪 Running tests..."

# Install test dependencies if not already installed
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/ -v

# Generate coverage report
pytest --cov=app tests/

echo "✅ Tests complete!"

---

# scripts/deploy.sh - Production deployment script

#!/bin/bash
echo "🚀 Deploying to production..."

# Build production Docker image
docker build -t language-ai-backend .

# Stop existing containers
docker-compose -f docker-compose.prod.yml down

# Start production services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

echo "✅ Deployment complete!"

# Make scripts executable:
# chmod +x scripts/*.sh