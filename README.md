# 🎓 Language Learning AI Backend

A powerful, scalable backend for language learning applications with AI-powered essay grading and speaking analysis.

## 🌟 Features

- **AI Essay Grading**: Automatic IELTS/TOEFL essay scoring using GPT-4
- **Speaking Analysis**: Audio transcription and pronunciation feedback
- **Real-time Processing**: Asynchronous task queue with Celery
- **User Management**: JWT authentication with role-based access
- **Scalable Architecture**: Docker containerization with PostgreSQL and Redis
- **Comprehensive API**: RESTful endpoints with OpenAPI documentation
- **Production Ready**: Monitoring, logging, and deployment automation

## 🏗️ Architecture Overview

```
Frontend (SvelteKit) ←→ FastAPI ←→ PostgreSQL
                         ↓
                    Celery Workers ←→ Redis Queue
                         ↓
                    OpenAI API (GPT-4, Whisper)
```

### Core Components

- **FastAPI**: High-performance Python web framework
- **PostgreSQL**: Robust relational database
- **Redis**: Message broker for background tasks
- **Celery**: Distributed task queue
- **OpenAI API**: AI models for grading and analysis
- **Docker**: Containerization for easy deployment

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- OpenAI API key
- Git

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/language-ai-backend.git
cd language-ai-backend

# Run setup script
chmod +x scripts/*.sh
./scripts/setup.sh
```

### 2. Configure Environment

```bash
# Copy and edit environment file
cp .env.example .env

# Add your OpenAI API key
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. Start Development Environment

```bash
# Start all services
docker-compose up -d

# Run database migrations
alembic upgrade head

# Start FastAPI server
./scripts/dev.sh
```

### 4. Start Background Workers

```bash
# In a new terminal
./scripts/worker.sh
```

### 5. Access the Application

- **API Documentation**: http://localhost:8000/docs
- **Flower (Task Monitor)**: http://localhost:5555
- **API Health Check**: http://localhost:8000/health

## 📖 API Usage Examples

### Authentication

```bash
# Register new user
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "username": "student1",
    "full_name": "John Student",
    "password": "securepassword"
  }'

# Login
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@example.com",
    "password": "securepassword"
  }'
```

### Essay Submission and Grading

```bash
# Submit essay
curl -X POST "http://localhost:8000/api/essays/submit" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Climate Change Essay",
    "content": "Climate change is one of the most pressing issues...",
    "task_type": "task2"
  }'

# Queue for grading
curl -X POST "http://localhost:8000/api/tasks/grade-essay/1" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Check grading status
curl -X GET "http://localhost:8000/api/tasks/status/TASK_ID" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Speaking Analysis

```bash
# Submit audio file
curl -X POST "http://localhost:8000/api/speaking/submit" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "audio_file=@recording.mp3" \
  -F "task_type=part2" \
  -F "question=Describe your hometown"

# Queue for analysis
curl -X POST "http://localhost:8000/api/tasks/analyze-speaking/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🗃️ Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    user_type VARCHAR(20) DEFAULT 'student',
    is_active BOOLEAN DEFAULT true,
    is_premium BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Essays Table
```sql
CREATE TABLE essays (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    task_type VARCHAR(50),
    word_count INTEGER,
    author_id INTEGER REFERENCES users(id),
    is_graded BOOLEAN DEFAULT false,
    overall_score FLOAT,
    submitted_at TIMESTAMP DEFAULT NOW()
);
```

### Essay Grading Table
```sql
CREATE TABLE essay_gradings (
    id SERIAL PRIMARY KEY,
    essay_id INTEGER REFERENCES essays(id),
    task_achievement FLOAT,
    coherence_cohesion FLOAT,
    lexical_resource FLOAT,
    grammar_accuracy FLOAT,
    overall_band FLOAT,
    feedback JSON,
    ai_model_used VARCHAR(50),
    processing_time FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 🔧 Development Commands

### Database Operations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# Reset database (DANGER: deletes all data)
python -c "
from app.database import DatabaseManager
import asyncio
asyncio.run(DatabaseManager.reset_db())
"
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test file
pytest tests/test_auth.py -v

# Run tests with live database
pytest tests/ --live-db
```

### Code Quality

```bash
# Format code
black app/ tests/
isort app/ tests/

# Type checking
mypy app/

# Lint code
flake8 app/ tests/
```

## 🚀 Production Deployment

### Using Docker Compose

```bash
# Build production images
docker build -f Dockerfile.prod -t language-ai-backend:latest .

# Deploy to production
./scripts/deploy.sh

# Monitor deployment
docker-compose -f docker-compose.prod.yml logs -f
```

### Environment Variables (Production)

```bash
# Required production variables
DATABASE_URL=postgresql://user:pass@host:5432/dbname
REDIS_URL=redis://user:pass@host:6379/0
SECRET_KEY=very-long-random-secret-key
OPENAI_API_KEY=sk-your-production-key
DEBUG=false
```

### SSL/HTTPS Setup

1. Obtain SSL certificates (Let's Encrypt recommended)
2. Update `nginx/nginx.conf` with your domain
3. Place certificates in `nginx/ssl/`
4. Restart nginx service

## 📊 Monitoring and Maintenance

### Application Metrics

- **Response Time**: Average API response time
- **Request Volume**: Requests per minute/hour
- **Error Rate**: Percentage of failed requests
- **AI Usage**: OpenAI API costs and token usage
- **User Activity**: Daily/monthly active users

### Log Analysis

```bash
# View application logs
docker-compose logs -f api

# View worker logs
docker-compose logs -f celery-worker

# View database logs
docker-compose logs -f postgres
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Database health
docker-compose exec postgres pg_isready

# Redis health
docker-compose exec redis redis-cli ping
```

## 🔒 Security Considerations

### Authentication & Authorization
- JWT tokens with expiration
- Password hashing with bcrypt
- Role-based access control
- Rate limiting on sensitive endpoints

### Data Protection
- SQL injection prevention (SQLAlchemy ORM)
- Input validation with Pydantic
- CORS configuration
- HTTPS enforcement in production

### API Security
- Request size limits
- File upload validation
- API key management
- Audit logging

## 🧪 Testing Strategy

### Test Types
- **Unit Tests**: Individual function testing
- **Integration Tests**: Database and API testing
- **End-to-End Tests**: Complete user workflows
- **Performance Tests**: Load and stress testing

### Test Coverage
- Aim for >90% code coverage
- Test all API endpoints
- Mock external services (OpenAI)
- Test error scenarios

## 🐛 Troubleshooting

### Common Issues

**Database Connection Error**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View database logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U user -d language_ai -c "SELECT 1;"
```

**Redis Connection Error**
```bash
# Check Redis status
docker-compose ps redis

# Test Redis connection
docker-compose exec redis redis-cli ping
```

**OpenAI API Errors**
```bash
# Check API key in logs
docker-compose logs api | grep -i openai

# Verify API key format
echo $OPENAI_API_KEY | grep -E "^sk-[a-zA-Z0-9]{48}$"
```

**Celery Tasks Not Processing**
```bash
# Check worker status
docker-compose logs celery-worker

# Monitor task queue
docker-compose exec redis redis-cli llen celery

# Restart workers
docker-compose restart celery-worker
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run tests: `pytest tests/`
5. Commit changes: `git commit -m "Add feature"`
6. Push to branch: `git push origin feature-name`
7. Submit pull request

### Code Style
- Use Black for code formatting
- Follow PEP 8 guidelines
- Add type hints
- Write docstrings for functions
- Update tests for new features

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Documentation**: Check `/docs` endpoint when running
- **Issues**: Submit GitHub issues for bugs
- **Discussions**: Use GitHub Discussions for questions
- **Email**: support@yourdomain.com

## 🗺️ Roadmap

### Phase 1 (Current)
- ✅ Basic essay grading
- ✅ Speaking analysis
- ✅ User authentication
- ✅ Background task processing

### Phase 2 (Next)
- 🔄 Advanced AI feedback
- 🔄 Writing improvement suggestions
- 🔄 Progress tracking
- 🔄 Teacher dashboard

### Phase 3 (Future)
- 📅 Multiple language support
- 📅 Real-time collaboration
- 📅 Mobile app integration
- 📅 Advanced analytics

---

Built with using FastAPI, PostgreSQL, Redis, and OpenAI.