import os
import sys
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

print("🚀 Starting GetEdu Backend...")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")

# Simple in-memory storage for demo
users_db = {}
essays_db = {}

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ GetEdu Backend started successfully!")
    yield
    print("👋 Shutting down GetEdu Backend")

# Create FastAPI app
app = FastAPI(
    title="GetEdu - AI Language Learning Backend",
    version="1.0.0",
    description="AI-powered language learning platform with comprehensive evaluation",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- BASIC ROUTES ---
@app.get("/")
async def root():
    return {
        "message": "Welcome to GetEdu - AI Language Learning Backend",
        "version": "1.0.0",
        "status": "running",
        "features": [
            "✅ User Authentication",
            "✅ Essay Evaluation", 
            "✅ Speaking Analysis",
            "✅ AI Feedback",
            "✅ Progress Tracking"
        ],
        "ai_service": "Enhanced Free AI Service",
        "cost": "100% Free",
        "database": "In-Memory (Demo Mode)",
        "endpoints": {
            "auth": "/api/auth/",
            "essays": "/api/essays/", 
            "ai_evaluation": "/api/ai/",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "ai_service": "available",
        "version": "1.0.0",
        "timestamp": "2025-07-18T16:30:00Z"
    }

# --- AUTHENTICATION ROUTES ---
@app.post("/api/auth/register")
async def register(user_data: dict):
    """Register a new user"""
    email = user_data.get("email")
    username = user_data.get("username")
    password = user_data.get("password")
    full_name = user_data.get("full_name")
    
    if not all([email, username, password, full_name]):
        raise HTTPException(status_code=400, detail="All fields are required")
    
    if email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Store user (in production, hash the password)
    users_db[email] = {
        "email": email,
        "username": username,
        "full_name": full_name,
        "password": password,  # In production, this should be hashed
        "user_id": len(users_db) + 1
    }
    
    return {
        "message": "User created successfully",
        "user_id": users_db[email]["user_id"],
        "email": email,
        "username": username
    }

@app.post("/api/auth/login")
async def login(login_data: dict):
    """Login user and return token"""
    email = login_data.get("email")
    password = login_data.get("password")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")
    
    user = users_db.get(email)
    if not user or user["password"] != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # In production, return a proper JWT token
    token = f"demo_token_{user['user_id']}"
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["user_id"],
            "email": user["email"],
            "username": user["username"],
            "full_name": user["full_name"]
        }
    }

@app.get("/api/auth/me")
async def get_me():
    """Get current user info"""
    # In production, extract user from JWT token
    return {
        "id": 1,
        "email": "demo@example.com",
        "username": "demo_user",
        "full_name": "Demo User",
        "user_type": "student"
    }

# --- ESSAY ROUTES ---
@app.post("/api/essays/submit")
async def submit_essay(essay_data: dict):
    """Submit an essay"""
    title = essay_data.get("title")
    content = essay_data.get("content")
    task_type = essay_data.get("task_type", "general")
    
    if not title or not content:
        raise HTTPException(status_code=400, detail="Title and content are required")
    
    essay_id = len(essays_db) + 1
    word_count = len(content.split())
    
    essays_db[essay_id] = {
        "id": essay_id,
        "title": title,
        "content": content,
        "task_type": task_type,
        "word_count": word_count,
        "submitted_at": "2025-07-18T16:30:00Z",
        "is_graded": False
    }
    
    return {
        "message": "Essay submitted successfully",
        "essay_id": essay_id,
        "word_count": word_count,
        "status": "submitted"
    }

@app.get("/api/essays/my-essays")
async def get_my_essays():
    """Get user's essays"""
    return {
        "essays": [
            {
                "id": essay["id"],
                "title": essay["title"],
                "task_type": essay["task_type"],
                "word_count": essay["word_count"],
                "is_graded": essay["is_graded"],
                "submitted_at": essay["submitted_at"]
            }
            for essay in essays_db.values()
        ]
    }

# --- AI EVALUATION ROUTES ---
@app.post("/api/ai/evaluate-essay")
async def evaluate_essay(request: dict):
    """Evaluate an essay with AI"""
    essay_id = request.get("essay_id")
    
    if not essay_id or essay_id not in essays_db:
        raise HTTPException(status_code=404, detail="Essay not found")
    
    essay = essays_db[essay_id]
    
    # Simple rule-based evaluation
    word_count = essay["word_count"]
    content = essay["content"]
    
    # Calculate basic scores
    task_score = 6.0 if word_count > 150 else 5.5
    coherence_score = 6.5 if len(content.split('.')) > 3 else 6.0
    lexical_score = 6.0 if len(set(content.lower().split())) / len(content.split()) > 0.5 else 5.5
    grammar_score = 6.0
    overall_band = round((task_score + coherence_score + lexical_score + grammar_score) / 4, 1)
    
    # Mark as graded
    essay["is_graded"] = True
    
    return {
        "message": "Essay evaluated successfully",
        "essay_id": essay_id,
        "overall_band": overall_band,
        "cost": 0.0,
        "scores": {
            "task_achievement": task_score,
            "coherence_cohesion": coherence_score,
            "lexical_resource": lexical_score,
            "grammar_accuracy": grammar_score,
            "overall_band": overall_band
        },
        "evaluation": {
            "strengths": [
                "Clear attempt at addressing the task",
                "Reasonable essay structure",
                "Good word count for the task type"
            ],
            "weaknesses": [
                "Could develop ideas more fully",
                "More varied vocabulary would improve the score",
                "Consider using more complex sentence structures"
            ],
            "focus_areas": ["lexical_resource", "grammar_accuracy"]
        },
        "improvement_course": {
            "title": "Personalized 4-Week Improvement Plan",
            "current_level": overall_band,
            "target_level": overall_band + 0.5,
            "estimated_duration": "4 weeks",
            "primary_focus": "Vocabulary and Grammar",
            "weekly_plan": [
                {
                    "week": 1,
                    "focus": "Vocabulary Building",
                    "activities": ["Learn 10 new academic words daily", "Practice using synonyms"]
                },
                {
                    "week": 2,
                    "focus": "Grammar Structures",
                    "activities": ["Practice complex sentences", "Use conditional structures"]
                },
                {
                    "week": 3,
                    "focus": "Essay Organization",
                    "activities": ["Practice paragraph development", "Use linking words"]
                },
                {
                    "week": 4,
                    "focus": "Practice and Review",
                    "activities": ["Write practice essays", "Review and improve"]
                }
            ],
            "daily_activities": [
                "Read academic articles (15 mins)",
                "Practice writing paragraphs (20 mins)",
                "Learn new vocabulary (10 mins)"
            ]
        }
    }

@app.post("/api/ai/quick-evaluate")
async def quick_evaluate(request: dict):
    """Quick essay evaluation"""
    content = request.get("content")
    work_type = request.get("work_type", "essay")
    
    if not content:
        raise HTTPException(status_code=400, detail="Content is required")
    
    # Simple evaluation
    word_count = len(content.split())
    sentences = len(content.split('.'))
    
    # Calculate scores
    overall_score = 6.0 if word_count > 100 else 5.5
    
    return {
        "message": "Quick evaluation completed",
        "overall_band": overall_score,
        "cost": 0.0,
        "scores": {
            "overall_band": overall_score,
            "word_count": word_count,
            "sentences": sentences
        },
        "evaluation": {
            "strengths": ["Good attempt at the task"],
            "weaknesses": ["Could be more detailed"],
            "focus_areas": ["development", "vocabulary"]
        },
        "improvement_course": {
            "title": "Quick Improvement Tips",
            "suggestions": [
                "Write longer responses",
                "Use more varied vocabulary",
                "Practice daily writing"
            ]
        }
    }

@app.post("/api/ai/evaluate-speaking")
async def evaluate_speaking(request: dict):
    """Evaluate speaking performance"""
    transcription = request.get("transcription")
    speaking_duration = request.get("speaking_duration", 30)
    
    if not transcription:
        raise HTTPException(status_code=400, detail="Transcription is required")
    
    # Simple speaking evaluation
    word_count = len(transcription.split())
    words_per_minute = (word_count / speaking_duration) * 60 if speaking_duration > 0 else 0
    
    # Calculate scores
    fluency_score = 6.0 if words_per_minute > 120 else 5.5
    lexical_score = 6.0 if len(set(transcription.lower().split())) / len(transcription.split()) > 0.5 else 5.5
    grammar_score = 6.0
    pronunciation_score = 6.0  # Demo score
    overall_band = round((fluency_score + lexical_score + grammar_score + pronunciation_score) / 4, 1)
    
    return {
        "message": "Speaking evaluation completed",
        "overall_band": overall_band,
        "cost": 0.0,
        "scores": {
            "fluency_coherence": fluency_score,
            "lexical_resource": lexical_score,
            "grammatical_range": grammar_score,
            "pronunciation": pronunciation_score,
            "overall_band": overall_band
        },
        "evaluation": {
            "strengths": ["Clear speech attempt", "Good speaking duration"],
            "weaknesses": ["Could speak more fluently", "More vocabulary variety needed"],
            "speaking_metrics": {
                "words_per_minute": round(words_per_minute, 1),
                "speaking_time": speaking_duration,
                "word_count": word_count
            }
        },
        "improvement_course": {
            "title": "Speaking Improvement Plan",
            "focus": "Fluency and Vocabulary",
            "daily_practice": [
                "Speak for 5 minutes daily",
                "Record yourself speaking",
                "Practice with new vocabulary"
            ]
        }
    }

@app.get("/api/ai/my-progress")
async def get_progress():
    """Get user progress"""
    return {
        "progress": {
            "total_essays": len(essays_db),
            "current_level": 6.0,
            "improvement_trend": "Improving",
            "skill_breakdown": {
                "task_achievement": {"current": 6.0, "trend": 0.5},
                "coherence_cohesion": {"current": 6.5, "trend": 0.3},
                "lexical_resource": {"current": 5.5, "trend": 0.2},
                "grammar_accuracy": {"current": 6.0, "trend": 0.4}
            }
        },
        "recommendations": {
            "focus_area": "Vocabulary Development",
            "next_goal": "Reach 6.5 overall band",
            "estimated_time": "3-4 weeks with practice"
        }
    }

# --- DEMO ROUTES ---
@app.get("/api/demo/features")
async def demo_features():
    """Show platform features"""
    return {
        "platform_features": {
            "writing_evaluation": {
                "description": "Comprehensive essay analysis with detailed feedback",
                "available": True
            },
            "speaking_analysis": {
                "description": "AI-powered speaking evaluation",
                "available": True
            },
            "progress_tracking": {
                "description": "Monitor improvement over time",
                "available": True
            },
            "improvement_courses": {
                "description": "Personalized learning plans",
                "available": True
            }
        },
        "cost": "100% Free",
        "ai_technology": "Enhanced Rule-Based Analysis"
    }

@app.get("/api/quick-start")
async def quick_start():
    """Quick start guide"""
    return {
        "welcome": "Welcome to GetEdu!",
        "steps": [
            "1. Register your account",
            "2. Submit your first essay",
            "3. Get AI evaluation and feedback",
            "4. Follow your improvement plan",
            "5. Track your progress"
        ],
        "sample_topics": [
            "Environmental protection",
            "Technology in education",
            "Social media impact",
            "Future of work"
        ]
    }

# --- SYSTEM INFO ---
@app.get("/api/system/info")
async def system_info():
    return {
        "application": {
            "name": "GetEdu Backend",
            "version": "1.0.0",
            "mode": "Demo"
        },
        "features": {
            "ai_service": "Enhanced Free AI Service",
            "database": "In-Memory (Demo)",
            "authentication": "Simple Token",
            "cost": "100% Free"
        },
        "status": "Running successfully on Render"
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)