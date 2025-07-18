#!/usr/bin/env python3
"""
System Check and Verification Script
Verifies all components are properly configured and can connect
"""

import sys
import os
import asyncio
import importlib
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class SystemChecker:
    def __init__(self):
        self.results = {
            "overall_status": "✅ PASS",
            "checks": {},
            "warnings": [],
            "errors": []
        }
    
    def check_imports(self) -> bool:
        """Check if all required modules can be imported"""
        print("🔍 Checking imports...")
        
        required_modules = [
            ("fastapi", "FastAPI framework"),
            ("sqlalchemy", "Database ORM"),
            ("celery", "Background tasks"),
            ("redis", "Redis client"),
            ("pydantic", "Data validation"),
            ("jose", "JWT tokens"),
            ("passlib", "Password hashing"),
            ("openai", "OpenAI API (optional)"),
            ("torch", "PyTorch (for fallback AI)"),
            ("transformers", "Hugging Face transformers"),
        ]
        
        failed_imports = []
        
        for module_name, description in required_modules:
            try:
                importlib.import_module(module_name)
                print(f"  ✅ {module_name} - {description}")
            except ImportError as e:
                if module_name in ["openai", "torch", "transformers"]:
                    print(f"  ⚠️ {module_name} - {description} (optional)")
                    self.results["warnings"].append(f"Optional module {module_name} not available")
                else:
                    print(f"  ❌ {module_name} - {description}")
                    failed_imports.append(f"{module_name}: {str(e)}")
        
        if failed_imports:
            self.results["errors"].extend(failed_imports)
            self.results["checks"]["imports"] = "❌ FAIL"
            return False
        
        self.results["checks"]["imports"] = "✅ PASS"
        return True
    
    def check_project_structure(self) -> bool:
        """Check if project structure is correct"""
        print("\n📁 Checking project structure...")
        
        required_files = [
            "app/__init__.py",
            "app/main.py",
            "app/database.py",
            "app/models/models.py",
            "app/api/auth/auth.py",
            "app/utils/logging.py",
            "workers/__init__.py",
            "workers/celery_app.py",
            "workers/ai_tasks.py",
            "config/settings.py",
            "requirements.txt",
            ".env.example"
        ]
        
        missing_files = []
        
        for file_path in required_files:
            if os.path.exists(file_path):
                print(f"  ✅ {file_path}")
            else:
                print(f"  ❌ {file_path}")
                missing_files.append(file_path)
        
        required_dirs = ["uploads", "logs", "models"]
        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                print(f"  📁 Creating {dir_path}/")
                os.makedirs(dir_path, exist_ok=True)
            else:
                print(f"  ✅ {dir_path}/")
        
        if missing_files:
            self.results["errors"].extend([f"Missing file: {f}" for f in missing_files])
            self.results["checks"]["structure"] = "❌ FAIL"
            return False
        
        self.results["checks"]["structure"] = "✅ PASS"
        return True
    
    def check_configuration(self) -> bool:
        """Check configuration files"""
        print("\n⚙️ Checking configuration...")
        
        try:
            from config.settings import settings
            
            # Check critical settings
            checks = [
                (settings.app_name, "App name configured"),
                (settings.secret_key != "change-this-in-production", "Secret key is set"),
                (settings.database_url, "Database URL configured"),
                (settings.redis_url, "Redis URL configured"),
            ]
            
            for check_value, description in checks:
                if check_value:
                    print(f"  ✅ {description}")
                else:
                    print(f"  ⚠️ {description}")
                    self.results["warnings"].append(description)
            
            # Check optional settings
            if settings.openai_api_key:
                print(f"  ✅ OpenAI API key configured")
            else:
                print(f"  ⚠️ OpenAI API key not set (will use fallback AI)")
                self.results["warnings"].append("OpenAI API key not configured")
            
            self.results["checks"]["configuration"] = "✅ PASS"
            return True
            
        except Exception as e:
            print(f"  ❌ Configuration error: {str(e)}")
            self.results["errors"].append(f"Configuration error: {str(e)}")
            self.results["checks"]["configuration"] = "❌ FAIL"
            return False
    
    def check_celery_setup(self) -> bool:
        """Check Celery configuration"""
        print("\n👷 Checking Celery setup...")
        
        try:
            from workers.celery_app import celery_app
            
            # Check Celery app creation
            print(f"  ✅ Celery app created")
            print(f"  ✅ Broker: {celery_app.conf.broker_url}")
            print(f"  ✅ Backend: {celery_app.conf.result_backend}")
            
            # Check task registration
            registered_tasks = list(celery_app.tasks.keys())
            expected_tasks = [
                "workers.ai_tasks.grade_essay",
                "workers.ai_tasks.analyze_speaking",
                "workers.ai_tasks.generate_curriculum"
            ]
            
            for task in expected_tasks:
                if task in registered_tasks:
                    print(f"  ✅ Task registered: {task}")
                else:
                    print(f"  ⚠️ Task not found: {task}")
                    self.results["warnings"].append(f"Celery task not registered: {task}")
            
            self.results["checks"]["celery"] = "✅ PASS"
            return True
            
        except Exception as e:
            print(f"  ❌ Celery setup error: {str(e)}")
            self.results["errors"].append(f"Celery setup error: {str(e)}")
            self.results["checks"]["celery"] = "❌ FAIL"
            return False
    
    async def check_database_connection(self) -> bool:
        """Check database connectivity"""
        print("\n🗃️ Checking database connection...")
        
        try:
            from app.database import async_engine
            from sqlalchemy import text
            
            async with async_engine.begin() as conn:
                result = await conn.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                
                if test_value == 1:
                    print(f"  ✅ Database connection successful")
                    print(f"  ✅ Database URL: {str(async_engine.url).split('@')[1] if '@' in str(async_engine.url) else 'Local'}")
                    self.results["checks"]["database"] = "✅ PASS"
                    return True
                else:
                    print(f"  ❌ Database test query failed")
                    self.results["errors"].append("Database test query returned unexpected result")
                    self.results["checks"]["database"] = "❌ FAIL"
                    return False
                    
        except Exception as e:
            print(f"  ❌ Database connection failed: {str(e)}")
            self.results["errors"].append(f"Database connection error: {str(e)}")
            self.results["checks"]["database"] = "❌ FAIL"
            return False
    
    def check_redis_connection(self) -> bool:
        """Check Redis connectivity"""
        print("\n🔴 Checking Redis connection...")
        
        try:
            import redis
            from config.settings import settings
            
            r = redis.from_url(settings.redis_url)
            
            # Test ping
            result = r.ping()
            if result:
                print(f"  ✅ Redis connection successful")
                print(f"  ✅ Redis URL: {settings.redis_url}")
                
                # Test basic operations
                r.set("test_key", "test_value", ex=10)
                value = r.get("test_key")
                if value == b"test_value":
                    print(f"  ✅ Redis read/write operations working")
                
                self.results["checks"]["redis"] = "✅ PASS"
                return True
            else:
                print(f"  ❌ Redis ping failed")
                self.results["errors"].append("Redis ping failed")
                self.results["checks"]["redis"] = "❌ FAIL"
                return False
                
        except Exception as e:
            print(f"  ❌ Redis connection failed: {str(e)}")
            self.results["errors"].append(f"Redis connection error: {str(e)}")
            self.results["checks"]["redis"] = "❌ FAIL"
            return False
    
    def check_ai_services(self) -> bool:
        """Check AI services availability"""
        print("\n🧠 Checking AI services...")
        
        try:
            from app.services.enhanced_ai_services import ai_service_manager
            
            # Check primary AI service
            if ai_service_manager.primary_service:
                print(f"  ✅ Primary AI service (OpenAI) available")
            else:
                print(f"  ⚠️ Primary AI service (OpenAI) not available")
                self.results["warnings"].append("OpenAI service not configured")
            
            # Check fallback AI service
            if ai_service_manager.fallback_service:
                print(f"  ✅ Fallback AI service available")
            else:
                print(f"  ❌ Fallback AI service not available")
                self.results["errors"].append("Fallback AI service failed to initialize")
                self.results["checks"]["ai_services"] = "❌ FAIL"
                return False
            
            self.results["checks"]["ai_services"] = "✅ PASS"
            return True
            
        except Exception as e:
            print(f"  ❌ AI services check failed: {str(e)}")
            self.results["errors"].append(f"AI services error: {str(e)}")
            self.results["checks"]["ai_services"] = "❌ FAIL"
            return False
    
    def check_environment_file(self) -> bool:
        """Check environment configuration"""
        print("\n📄 Checking environment file...")
        
        if os.path.exists(".env"):
            print(f"  ✅ .env file exists")
            
            # Check for critical variables
            required_vars = [
                "SECRET_KEY",
                "DATABASE_URL",
                "REDIS_URL"
            ]
            
            missing_vars = []
            for var in required_vars:
                if os.getenv(var):
                    print(f"  ✅ {var} is set")
                else:
                    print(f"  ⚠️ {var} not set")
                    missing_vars.append(var)
            
            if missing_vars:
                self.results["warnings"].extend([f"Environment variable {var} not set" for var in missing_vars])
            
            self.results["checks"]["environment"] = "✅ PASS"
            return True
        else:
            print(f"  ⚠️ .env file not found - using defaults")
            self.results["warnings"].append(".env file not found")
            self.results["checks"]["environment"] = "⚠️ WARNING"
            return True
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all system checks"""
        print("🔧 Language Learning AI Backend - System Check")
        print("=" * 50)
        
        checks = [
            self.check_imports(),
            self.check_project_structure(),
            self.check_environment_file(),
            self.check_configuration(),
            self.check_celery_setup(),
            await self.check_database_connection(),
            self.check_redis_connection(),
            self.check_ai_services()
        ]
        
        # Determine overall status
        if any(not check for check in checks):
            self.results["overall_status"] = "❌ FAIL"
        elif self.results["warnings"]:
            self.results["overall_status"] = "⚠️ WARNING"
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 SYSTEM CHECK SUMMARY")
        print("=" * 50)
        
        print(f"Overall Status: {self.results['overall_status']}")
        print("\nComponent Status:")
        for component, status in self.results["checks"].items():
            print(f"  {component.title()}: {status}")
        
        if self.results["warnings"]:
            print(f"\n⚠️ Warnings ({len(self.results['warnings'])}):")
            for warning in self.results["warnings"]:
                print(f"  - {warning}")
        
        if self.results["errors"]:
            print(f"\n❌ Errors ({len(self.results['errors'])}):")
            for error in self.results["errors"]:
                print(f"  - {error}")
        
        # Provide next steps
        print("\n🚀 Next Steps:")
        if not self.results["errors"]:
            print("  ✅ System is ready!")
            print("  Run 'make dev' to start the development environment")
            print("  Or run 'uvicorn app.main:app --reload' to start the API server")
        else:
            print("  ❌ Fix the errors above before starting the system")
            print("  Check the documentation for setup instructions")
        
        return self.results

async def main():
    """Main function to run system checks"""
    checker = SystemChecker()
    results = await checker.run_all_checks()
    
    # Exit with appropriate code
    if results["overall_status"] == "❌ FAIL":
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 System check cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 System check failed with unexpected error: {str(e)}")
        sys.exit(1)

# scripts/quick_start.py - Quick Start Development Setup
#!/usr/bin/env python3
"""
Quick start script to set up the development environment
"""

import os
import sys
import subprocess
import time

def run_command(cmd, description, check=True):
    """Run a command with description"""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✅ {description} completed")
            return True
        else:
            print(f"  ❌ {description} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ❌ {description} failed: {str(e)}")
        return False

def check_prerequisites():
    """Check if required tools are installed"""
    print("🔍 Checking prerequisites...")
    
    requirements = [
        ("python", "python --version"),
        ("pip", "pip --version"),
        ("docker", "docker --version"),
        ("docker-compose", "docker-compose --version")
    ]
    
    missing = []
    for tool, cmd in requirements:
        if run_command(cmd, f"Checking {tool}", check=False):
            pass  # Already printed success
        else:
            missing.append(tool)
    
    if missing:
        print(f"\n❌ Missing required tools: {', '.join(missing)}")
        print("Please install them before continuing.")
        return False
    
    print("✅ All prerequisites are installed")
    return True

def setup_python_environment():
    """Set up Python virtual environment and install dependencies"""
    print("\n📦 Setting up Python environment...")
    
    # Create virtual environment if it doesn't exist
    if not os.path.exists("venv"):
        if not run_command("python -m venv venv", "Creating virtual environment"):
            return False
    
    # Activate virtual environment and install dependencies
    if os.name == 'nt':  # Windows
        activate_cmd = "venv\\Scripts\\activate"
    else:  # Unix/Linux/macOS
        activate_cmd = "source venv/bin/activate"
    
    install_cmd = f"{activate_cmd} && pip install --upgrade pip && pip install -r requirements.txt"
    
    if not run_command(install_cmd, "Installing Python dependencies"):
        return False
    
    return True

def setup_environment_file():
    """Set up environment configuration"""
    print("\n⚙️ Setting up environment configuration...")
    
    if not os.path.exists(".env"):
        if os.path.exists(".env.example"):
            run_command("cp .env.example .env", "Creating .env file from template")
            print("  📝 Please edit .env file with your configuration")
        else:
            # Create basic .env file
            env_content = """# Language Learning AI Backend Configuration
DEBUG=true
SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///./language_ai.db
DATABASE_URL_ASYNC=sqlite+aiosqlite:///./language_ai.db
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=your-openai-key-here
"""
            with open(".env", "w") as f:
                f.write(env_content)
            print("  ✅ Created basic .env file")
    else:
        print("  ✅ .env file already exists")
    
    return True

def setup_directories():
    """Create necessary directories"""
    print("\n📁 Creating directories...")
    
    directories = ["uploads", "logs", "models", "backups"]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  ✅ Created {directory}/")
    
    return True

def start_services():
    """Start Docker services"""
    print("\n🐳 Starting Docker services...")
    
    if not run_command("docker-compose up -d postgres redis", "Starting PostgreSQL and Redis"):
        print("  ⚠️ Docker services failed to start - you can run them manually later")
        return False
    
    print("  ⏳ Waiting for services to be ready...")
    time.sleep(10)
    
    return True

def setup_database():
    """Set up database and run migrations"""
    print("\n🗃️ Setting up database...")
    
    # Run database migrations
    if os.name == 'nt':  # Windows
        activate_cmd = "venv\\Scripts\\activate"
    else:  # Unix/Linux/macOS
        activate_cmd = "source venv/bin/activate"
    
    migration_cmd = f"{activate_cmd} && alembic upgrade head"
    
    if not run_command(migration_cmd, "Running database migrations"):
        print("  ⚠️ Database setup failed - you may need to run migrations manually")
        return False
    
    # Initialize demo data
    init_cmd = f"{activate_cmd} && python scripts/init_data.py"
    if not run_command(init_cmd, "Initializing demo data", check=False):
        print("  ⚠️ Demo data initialization failed - not critical")
    
    return True

def main():
    """Main setup function"""
    print("🚀 Language Learning AI Backend - Quick Start Setup")
    print("=" * 55)
    
    steps = [
        ("Prerequisites", check_prerequisites),
        ("Python Environment", setup_python_environment),
        ("Environment Configuration", setup_environment_file),
        ("Directories", setup_directories),
        ("Docker Services", start_services),
        ("Database", setup_database)
    ]
    
    failed_steps = []
    
    for step_name, step_func in steps:
        try:
            if not step_func():
                failed_steps.append(step_name)
        except Exception as e:
            print(f"❌ {step_name} failed with error: {str(e)}")
            failed_steps.append(step_name)
    
    # Summary
    print("\n" + "=" * 55)
    print("📊 SETUP SUMMARY")
    print("=" * 55)
    
    if not failed_steps:
        print("🎉 Setup completed successfully!")
        print("\n🚀 Next steps:")
        print("  1. Edit .env file with your OpenAI API key (optional)")
        print("  2. Run 'python scripts/system_check.py' to verify setup")
        print("  3. Run 'make dev' or 'uvicorn app.main:app --reload' to start")
        print("  4. Visit http://localhost:8000/docs for API documentation")
        print("\n📚 Demo credentials:")
        print("  Admin: admin@languageai.com / admin123!")
        print("  Student: student@demo.com / student123")
        print("  Teacher: teacher@demo.com / teacher123")
    else:
        print(f"⚠️ Setup completed with {len(failed_steps)} issues:")
        for step in failed_steps:
            print(f"  - {step}")
        print("\nYou may need to complete these steps manually.")
    
    print("\n📖 For more information, check the README.md file")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Setup failed with unexpected error: {str(e)}")
        sys.exit(1)