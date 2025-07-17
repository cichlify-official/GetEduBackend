import asyncio
import httpx
import json
import sys
from typing import Dict, Any

class DeploymentTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.token = None
        self.user_id = None
    
    async def test_health_check(self) -> bool:
        """Test health endpoint"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    print("✅ Health check passed")
                    print(f"   Status: {data.get('status')}")
                    print(f"   Database: {data.get('database')}")
                    print(f"   Environment: {data.get('environment')}")
                    return True
                else:
                    print(f"❌ Health check failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    async def test_user_registration(self) -> bool:
        """Test user registration"""
        try:
            test_user = {
                "email": "test@example.com",
                "username": "testuser",
                "full_name": "Test User",
                "password": "testpassword123"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/auth/register",
                    json=test_user
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.user_id = data.get('user_id')
                    print("✅ User registration passed")
                    print(f"   User ID: {self.user_id}")
                    return True
                else:
                    print(f"❌ User registration failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
        except Exception as e:
            print(f"❌ User registration error: {e}")
            return False
    
    async def test_user_login(self) -> bool:
        """Test user login"""
        try:
            login_data = {
                "email": "test@example.com",
                "password": "testpassword123"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/auth/login",
                    json=login_data
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get('access_token')
                    print("✅ User login passed")
                    print(f"   Token: {self.token[:20]}...")
                    return True
                else:
                    print(f"❌ User login failed: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return False
        except Exception as e:
            print(f"❌ User login error: {e}")
            return False
    
    async def test_protected_endpoint(self) -> bool:
        """Test protected endpoint with authentication"""
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/auth/me",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print("✅ Protected endpoint passed")
                    print(f"   User: {data.get('username')}")
                    return True
                else:
                    print(f"❌ Protected endpoint failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Protected endpoint error: {e}")
            return False
    
    async def test_essay_submission(self) -> bool:
        """Test essay submission"""
        try:
            essay_data = {
                "title": "Test Essay",
                "content": "This is a test essay for deployment verification. It contains enough content to test the word count and basic functionality of the essay submission system.",
                "task_type": "general"
            }
            
            headers = {"Authorization": f"Bearer {self.token}"}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/essays/submit",
                    json=essay_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print("✅ Essay submission passed")
                    print(f"   Essay ID: {data.get('essay_id')}")
                    print(f"   Word count: {data.get('word_count')}")
                    return True
                else:
                    print(f"❌ Essay submission failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Essay submission error: {e}")
            return False
    
    async def test_free_ai_grading(self) -> bool:
        """Test free AI grading service"""
        try:
            demo_data = {
                "content": "Climate change is one of the most pressing issues of our time. It affects every aspect of our lives and requires immediate action.",
                "task_type": "task2"
            }
            
            headers = {"Authorization": f"Bearer {self.token}"}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/ai/demo-grade",
                    json=demo_data,
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    grading = data.get('grading', {})
                    scores = grading.get('scores', {})
                    print("✅ Free AI grading passed")
                    print(f"   Overall band: {scores.get('overall_band')}")
                    print(f"   Analysis type: {data.get('analysis_type')}")
                    return True
                else:
                    print(f"❌ Free AI grading failed: {response.status_code}")
                    return False
        except Exception as e:
            print(f"❌ Free AI grading error: {e}")
            return False
    
    async def run_all_tests(self) -> Dict[str, bool]:
        """Run all deployment tests"""
        print(f"🚀 Testing deployment at: {self.base_url}\n")
        
        tests = [
            ("Health Check", self.test_health_check),
            ("User Registration", self.test_user_registration),
            ("User Login", self.test_user_login),
            ("Protected Endpoint", self.test_protected_endpoint),
            ("Essay Submission", self.test_essay_submission),
            ("Free AI Grading", self.test_free_ai_grading),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            print(f"\n🧪 Running {test_name}...")
            try:
                result = await test_func()
                results[test_name] = result
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                results[test_name] = False
        
        return results
    
    def print_summary(self, results: Dict[str, bool]):
        """Print test summary"""
        passed = sum(results.values())
        total = len(results)
        
        print(f"\n{'='*50}")
        print(f"🎯 DEPLOYMENT TEST SUMMARY")
        print(f"{'='*50}")
        print(f"Passed: {passed}/{total}")
        print(f"Success rate: {passed/total*100:.1f}%")
        
        if passed == total:
            print("🎉 All tests passed! Deployment is successful.")
        else:
            print("⚠️  Some tests failed. Check the issues above.")
            
        print(f"{'='*50}")

async def main():
    """Main test function"""
    if len(sys.argv) != 2:
        print("Usage: python test_deployment.py <base_url>")
        print("Example: python test_deployment.py https://your-app.onrender.com")
        sys.exit(1)
    
    base_url = sys.argv[1]
    tester = DeploymentTester(base_url)
    
    results = await tester.run_all_tests()
    tester.print_summary(results)
    
    # Exit with error code if any tests failed
    if not all(results.values()):
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
