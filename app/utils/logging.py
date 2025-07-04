import logging
import sys
from typing import Any, Dict
from datetime import datetime
import json

class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    Makes logs easier to search and analyze
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields if they exist
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'duration'):
            log_entry['duration'] = record.duration
            
        return json.dumps(log_entry)

def setup_logging():
    """
    Configure application logging
    """
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Console handler with JSON formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(console_handler)
    
    # Specific loggers
    loggers = {
        "uvicorn.access": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,
        "celery": logging.INFO,
        "app": logging.INFO
    }
    
    for logger_name, level in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)

# ==========================================
# app/utils/monitoring.py
# ==========================================

import time
import logging
from functools import wraps
from typing import Callable, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor API requests
    Tracks response times, status codes, and errors
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Generate request ID for tracing
        request_id = f"req_{int(time.time() * 1000)}"
        request.state.request_id = request_id
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Log successful requests
            logger.info(
                f"API Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "duration": round(duration * 1000, 2),  # milliseconds
                    "user_agent": request.headers.get("user-agent", "")
                }
            )
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Log errors
            logger.error(
                f"API Request failed: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "duration": round(duration * 1000, 2),
                    "error": str(e)
                },
                exc_info=True
            )
            
            raise

def monitor_function(func_name: str = None):
    """
    Decorator to monitor function execution
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            name = func_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"Function executed successfully: {name}",
                    extra={"duration": round(duration * 1000, 2)}
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    f"Function failed: {name} - {str(e)}",
                    extra={"duration": round(duration * 1000, 2)},
                    exc_info=True
                )
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            name = func_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                logger.info(
                    f"Function executed successfully: {name}",
                    extra={"duration": round(duration * 1000, 2)}
                )
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                
                logger.error(
                    f"Function failed: {name} - {str(e)}",
                    extra={"duration": round(duration * 1000, 2)},
                    exc_info=True
                )
                
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator

# ==========================================
# app/utils/metrics.py
# ==========================================

import asyncio
from typing import Dict, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import redis

@dataclass
class APIMetrics:
    """Data class for API metrics"""
    total_requests: int
    success_rate: float
    avg_response_time: float
    error_count: int
    active_users: int

class MetricsCollector:
    """
    Collect and store application metrics
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
    
    async def record_api_request(self, endpoint: str, method: str, 
                                status_code: int, duration: float):
        """Record API request metrics"""
        timestamp = datetime.utcnow()
        day_key = timestamp.strftime("%Y-%m-%d")
        hour_key = timestamp.strftime("%Y-%m-%d:%H")
        
        # Store in Redis with expiration
        pipe = self.redis.pipeline()
        
        # Daily metrics
        pipe.hincrby(f"api:daily:{day_key}", "total_requests", 1)
        pipe.hincrby(f"api:daily:{day_key}", f"status_{status_code}", 1)
        pipe.hincrbyfloat(f"api:daily:{day_key}", "total_duration", duration)
        pipe.expire(f"api:daily:{day_key}", 86400 * 30)  # 30 days
        
        # Hourly metrics
        pipe.hincrby(f"api:hourly:{hour_key}", "requests", 1)
        pipe.hincrbyfloat(f"api:hourly:{hour_key}", "duration", duration)
        pipe.expire(f"api:hourly:{hour_key}", 86400 * 7)  # 7 days
        
        # Endpoint-specific metrics
        pipe.hincrby(f"api:endpoint:{endpoint}", "requests", 1)
        pipe.hincrbyfloat(f"api:endpoint:{endpoint}", "total_duration", duration)
        
        await pipe.execute()
    
    async def record_user_activity(self, user_id: int, activity_type: str):
        """Record user activity for analytics"""
        timestamp = datetime.utcnow()
        day_key = timestamp.strftime("%Y-%m-%d")
        
        pipe = self.redis.pipeline()
        
        # Daily active users
        pipe.sadd(f"users:active:{day_key}", user_id)
        pipe.expire(f"users:active:{day_key}", 86400 * 30)
        
        # Activity tracking
        pipe.hincrby(f"activity:{day_key}", activity_type, 1)
        pipe.expire(f"activity:{day_key}", 86400 * 30)
        
        await pipe.execute()
    
    async def get_api_metrics(self, days: int = 7) -> List[APIMetrics]:
        """Get API metrics for the last N days"""
        metrics = []
        
        for i in range(days):
            date = datetime.utcnow() - timedelta(days=i)
            day_key = date.strftime("%Y-%m-%d")
            
            daily_data = await self.redis.hgetall(f"api:daily:{day_key}")
            active_users = await self.redis.scard(f"users:active:{day_key}")
            
            if daily_data:
                total_requests = int(daily_data.get(b'total_requests', 0))
                total_duration = float(daily_data.get(b'total_duration', 0))
                
                # Calculate success rate
                success_count = sum(
                    int(daily_data.get(f'status_{code}'.encode(), 0))
                    for code in [200, 201, 204]
                )
                success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
                
                # Calculate average response time
                avg_response_time = (total_duration / total_requests) if total_requests > 0 else 0
                
                # Count errors
                error_count = sum(
                    int(daily_data.get(f'status_{code}'.encode(), 0))
                    for code in [400, 401, 403, 404, 500, 502, 503]
                )
                
                metrics.append(APIMetrics(
                    total_requests=total_requests,
                    success_rate=round(success_rate, 2),
                    avg_response_time=round(avg_response_time * 1000, 2),  # Convert to ms
                    error_count=error_count,
                    active_users=active_users
                ))
        
        return metrics

# ==========================================
# app/api/routes/admin.py - Monitoring Endpoints
# ==========================================

from fastapi import APIRouter, Depends
from app.api.auth.auth import get_current_admin
from app.utils.metrics import MetricsCollector

router = APIRouter()

@router.get("/api/admin/metrics")
async def get_system_metrics(
    days: int = 7,
    current_user = Depends(get_current_admin)
):
    """Get system performance metrics (admin only)"""
    # This would connect to your Redis instance
    # metrics_collector = MetricsCollector(redis_client)
    # metrics = await metrics_collector.get_api_metrics(days)
    
    # For now, return mock data
    return {
        "metrics": [
            {
                "date": "2024-01-15",
                "total_requests": 1250,
                "success_rate": 98.5,
                "avg_response_time": 145,
                "error_count": 19,
                "active_users": 87
            }
        ],
        "summary": {
            "total_users": 1500,
            "total_essays": 3200,
            "total_speaking_tasks": 890,
            "ai_requests_today": 245,
            "system_health": "healthy"
        }
    }

@router.get("/api/admin/logs")
async def get_recent_logs(
    level: str = "ERROR",
    limit: int = 100,
    current_user = Depends(get_current_admin)
):
    """Get recent application logs (admin only)"""
    # In production, this would query your log storage system
    # For now, return mock data
    return {
        "logs": [
            {
                "timestamp": "2024-01-15T10:30:00Z",
                "level": "ERROR",
                "message": "OpenAI API rate limit exceeded",
                "module": "ai_service",
                "user_id": 123,
                "request_id": "req_1705315800"
            }
        ],
        "total": 15
    }