import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.database import get_async_db
from app.models.models import Base
from config.settings import settings

# Test database URL (use a separate test database)
TEST_DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/language_ai_test"

# Create test database engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=True)
TestSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    """Override database dependency for tests"""
    async with TestSessionLocal() as session:
        yield session

app.dependency_overrides[get_async_db] = override_get_db

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def setup_database():
    """Set up test database"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def db_session():
    """Get database session for tests"""
    async with TestSessionLocal() as session:
        yield session

@pytest.fixture
def client():
    """Get test client"""
    with TestClient(app) as c:
        yield c

@pytest.fixture
async def async_client():
    """Get async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
async def test_user(db_session):
    """Create a test user"""
    from app.models.models import User
    from app.api.auth.auth import AuthService
    
    user = await AuthService.create_user(
        db=db_session,
        email="test@example.com",
        username="testuser",
        full_name="Test User",
        password="testpassword"
    )
    return user

@pytest.fixture
async def auth_headers(test_user):
    """Get authentication headers for test user"""
    from app.api.auth.auth import AuthService
    
    token = AuthService.create_access_token(data={"sub": test_user.email})
    return {"Authorization": f"Bearer {token}"}

# ==========================================
# tests/test_auth.py
# ==========================================

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register_user(async_client: AsyncClient, setup_database):
    """Test user registration"""
    response = await async_client.post("/api/auth/register", json={
        "email": "newuser@example.com",
        "username": "newuser",
        "full_name": "New User",
        "password": "newpassword"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "User created successfully"
    assert "user_id" in data

@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, test_user, setup_database):
    """Test successful login"""
    response = await async_client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "test@example.com"

@pytest.mark.asyncio
async def test_login_invalid_credentials(async_client: AsyncClient, setup_database):
    """Test login with wrong password"""
    response = await async_client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "wrongpassword"
    })
    
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]

@pytest.mark.asyncio
async def test_get_current_user(async_client: AsyncClient, auth_headers, setup_database):
    """Test getting current user info"""
    response = await async_client.get("/api/auth/me", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"

# ==========================================
# tests/test_essays.py
# ==========================================

@pytest.mark.asyncio
async def test_submit_essay(async_client: AsyncClient, auth_headers, setup_database):
    """Test essay submission"""
    essay_data = {
        "title": "Test Essay",
        "content": "This is a test essay with some content to analyze.",
        "task_type": "task2"
    }
    
    response = await async_client.post(
        "/api/essays/submit", 
        json=essay_data, 
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Essay submitted successfully"
    assert "essay_id" in data
    assert "word_count" in data

@pytest.mark.asyncio
async def test_get_my_essays(async_client: AsyncClient, auth_headers, setup_database):
    """Test getting user's essays"""
    # First submit an essay
    await async_client.post("/api/essays/submit", json={
        "title": "My Essay",
        "content": "Essay content here",
        "task_type": "general"
    }, headers=auth_headers)
    
    # Then get essays
    response = await async_client.get("/api/essays/my-essays", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "essays" in data
    assert len(data["essays"]) > 0

@pytest.mark.asyncio
async def test_get_essay_details(async_client: AsyncClient, auth_headers, setup_database):
    """Test getting specific essay details"""
    # Submit essay first
    submit_response = await async_client.post("/api/essays/submit", json={
        "title": "Detailed Essay",
        "content": "This essay will have details",
        "task_type": "task1"
    }, headers=auth_headers)
    
    essay_id = submit_response.json()["essay_id"]
    
    # Get essay details
    response = await async_client.get(f"/api/essays/{essay_id}", headers=auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    assert data["essay"]["title"] == "Detailed Essay"
    assert data["grading"] is None  # Not graded yet

# ==========================================
# tests/test_ai_service.py
# ==========================================

import pytest
from unittest.mock import Mock, patch
from app.services.ai_service import OpenAIService

class TestOpenAIService:
    """Test AI service functionality"""
    
    @patch('app.services.ai_service.openai.OpenAI')
    def test_grade_essay_success(self, mock_openai):
        """Test successful essay grading"""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices[0].message.content = """{
            "scores": {
                "task_achievement": 7.0,
                "coherence_cohesion": 6.5,
                "lexical_resource": 6.0,
                "grammar_accuracy": 6.5,
                "overall_band": 6.5
            },
            "feedback": {
                "strengths": ["Clear structure"],
                "improvements": ["More examples needed"]
            }
        }"""
        mock_response.usage.total_tokens = 500
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Test the service
        service = OpenAIService()
        result = service.grade_essay("This is a test essay", "task2", 50)
        
        assert result["scores"]["overall_band"] == 6.5
        assert "strengths" in result["feedback"]
        assert result["tokens_used"] == 500

    def test_build_essay_grading_prompt(self):
        """Test prompt building"""
        service = OpenAIService()
        prompt = service._build_essay_grading_prompt("Test content", "task2", 100)
        
        assert "task2" in prompt
        assert "Test content" in prompt
        assert "100 words" in prompt
        assert "JSON format" in prompt

# ==========================================
# tests/test_database.py
# ==========================================

@pytest.mark.asyncio
async def test_user_creation(db_session):
    """Test creating user in database"""
    from app.models.models import User
    
    user = User(
        email="dbtest@example.com",
        username="dbtest",
        full_name="DB Test User",
        hashed_password="hashedpw"
    )
    
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    assert user.id is not None
    assert user.email == "dbtest@example.com"

@pytest.mark.asyncio
async def test_essay_user_relationship(db_session):
    """Test relationship between users and essays"""
    from app.models.models import User, Essay
    
    # Create user
    user = User(
        email="author@example.com",
        username="author",
        full_name="Essay Author",
        hashed_password="hashedpw"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    # Create essay
    essay = Essay(
        title="Test Essay",
        content="Essay content",
        author_id=user.id,
        word_count=50
    )
    db_session.add(essay)
    await db_session.commit()
    
    # Test relationship
    assert essay.author_id == user.id