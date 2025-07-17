import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import init_db

async def main():
    print("🚀 Initializing GET Education Database...")
    await init_db()
    print("✅ Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(main())
