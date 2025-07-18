# app/utils/__init__.py
"""
Utilities package for the Language Learning AI Backend

This package contains utility modules for:
- Logging and monitoring
- Performance metrics
- Error handling
- Data processing helpers
"""

# app/utils/logging.py - Complete Logging and Monitoring System
import logging
import sys
import json
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from functools import wraps
import asyncio
from contextlib import asynccontextmanager

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

class JSONFormatter(logging.Formatter):
    """
    Custom JSON formatter for structured logging
    Makes logs easier to search and analyze in production
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "thread": record.thread,
            "process": record.process
        }
        
        # Add extra fields if they exist
        extra_fields = [
            'user_id', 'request_id', 'duration', 'status_code',
            'method', 'url', 'ip_address', 'user_agent',
            'ai_model', 'cost', 'tokens_used', 'task_id'
        ]
        
        for field in extra_fields:
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add stack info if present
        if record.stack_info:
            log_entry['stack_info'] = record.stack_info
        
        return json.dumps(log_entry, ensure_ascii=False)

class ColoredFormatter(logging.Formatter):
    """
    Colored formatter for development console output
    """
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """Format with colors for console output"""
        
        # Get color for log level
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Build colored message
        message = (
            f"{color}[{timestamp}] "
            f"{record.levelname:8} "
            f"{record.name}:{record.lineno} "
            f"- {record.getMessage()}{reset}"
        )
        
        # Add exception info if present
        if record.exc_info:
            message += f"\n{self.formatException(record.exc_info)}"
        
        return message

class RequestLogger:
    """Helper class for request-specific logging"""
    
    def __init__(self, request_id: str, logger: logging.Logger):
        self.request_id = request_id
        self.logger = logger
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log with request context"""
        extra = {'request_id': self.request_id, **kwargs}
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log_with_context(logging.CRITICAL, message, **kwargs)

def setup_logging(
    level: str = "INFO",
    use_json: bool = False,
    log_file: Optional[str] = None
) -> None:
    """
    Configure application logging
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Whether to use JSON formatting
        log_file: Optional file to write logs to
    """
    
    # Convert level string to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    if use_json:
        console_formatter = JSONFormatter()
    else:
        console_formatter = ColoredFormatter()
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(JSONFormatter())  # Always use JSON for files
        root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    loggers_config = {
        "uvicorn": logging.WARNING,
        "uvicorn.access": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,
        "celery": logging.INFO,
        "celery.worker": logging.INFO,
        "celery.task": logging.INFO,
        "app": logging.INFO,
        "workers": logging.INFO,
        "httpx": logging.WARNING,
        "openai": logging.WARNING
    }
    
    for logger_name, logger_level in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(logger_level)
        logger.propagate = True  # Ensure logs propagate to root logger
    
    # Log initial setup
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {level}, JSON: {use_json}, File: {log_file}")

class MonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor API requests and responses
    Tracks performance, errors, and usage patterns
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.logger = logging.getLogger("app.monitoring")
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with monitoring"""
        
        # Generate request ID for tracing
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Get client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        # Start timing
        start_time = time.time()
        
        # Create request logger
        request_logger = RequestLogger(request_id, self.logger)
        request.state.logger = request_logger
        
        try:
            # Log request start
            request_logger.info(
                "Request started",
                method=request.method,
                url=str(request.url),
                ip_address=client_ip,
                user_agent=user_agent
            )
            
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            
            # Log successful request
            request_logger.info(
                "Request completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                duration=round(duration * 1000, 2),  # milliseconds
                ip_address=client_ip
            )
            
            # Add custom headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"
            
            return response
            
        except Exception as e:
            # Calculate duration for failed requests
            duration = time.time() - start_time
            
            # Log error
            request_logger.error(
                "Request failed",
                method=request.method,
                url=str(request.url),
                duration=round(duration * 1000, 2),
                error=str(e),
                error_type=type(e).__name__,
                ip_address=client_ip,
                exc_info=True
            )
            
            # Re-raise the exception
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        
        # Check for forwarded headers (for reverse proxy setups)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"

def monitor_function(
    func_name: Optional[str] = None,
    log_args: bool = False,
    log_result: bool = False
):
    """
    Decorator to monitor function execution
    
    Args:
        func_name: Custom name for the function (defaults to actual function name)
        log_args: Whether to log function arguments
        log_result: Whether to log function result
    """
    
    def decorator(func):
        name = func_name or f"{func.__module__}.{func.__name__}"
        logger = logging.getLogger("app.functions")
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                
                log_data = {"function": name}
                if log_args:
                    log_data.update({
                        "args": str(args)[:200],  # Truncate long args
                        "kwargs": str(kwargs)[:200]
                    })
                
                try:
                    logger.debug(f"Function started: {name}", extra=log_data)
                    
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    log_data["duration"] = round(duration * 1000, 2)
                    if log_result:
                        log_data["result"] = str(result)[:200]
                    
                    logger.info(f"Function completed: {name}", extra=log_data)
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    log_data.update({
                        "duration": round(duration * 1000, 2),
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                    
                    logger.error(f"Function failed: {name}", extra=log_data, exc_info=True)
                    raise
            
            return async_wrapper
        
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                
                log_data = {"function": name}
                if log_args:
                    log_data.update({
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200]
                    })
                
                try:
                    logger.debug(f"Function started: {name}", extra=log_data)
                    
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    
                    log_data["duration"] = round(duration * 1000, 2)
                    if log_result:
                        log_data["result"] = str(result)[:200]
                    
                    logger.info(f"Function completed: {name}", extra=log_data)
                    return result
                    
                except Exception as e:
                    duration = time.time() - start_time
                    log_data.update({
                        "duration": round(duration * 1000, 2),
                        "error": str(e),
                        "error_type": type(e).__name__
                    })
                    
                    logger.error(f"Function failed: {name}", extra=log_data, exc_info=True)
                    raise
            
            return sync_wrapper
    
    return decorator

def log_ai_request(
    model: str,
    request_type: str,
    user_id: Optional[int] = None,
    cost: float = 0.0,
    tokens_used: int = 0
):
    """
    Log AI service requests for monitoring and cost tracking
    
    Args:
        model: AI model used (e.g., "gpt-4", "whisper")
        request_type: Type of request (e.g., "essay_grading", "speaking_analysis")
        user_id: ID of the user making the request
        cost: Cost of the API request
        tokens_used: Number of tokens consumed
    """
    
    logger = logging.getLogger("app.ai_requests")
    
    logger.info(
        f"AI request: {request_type}",
        extra={
            "ai_model": model,
            "request_type": request_type,
            "user_id": user_id,
            "cost": cost,
            "tokens_used": tokens_used
        }
    )

@asynccontextmanager
async def log_async_operation(operation_name: str, logger: Optional[logging.Logger] = None):
    """
    Context manager for logging async operations
    
    Usage:
        async with log_async_operation("database_query"):
            result = await db.execute(query)
    """
    
    if logger is None:
        logger = logging.getLogger("app.operations")
    
    start_time = time.time()
    
    try:
        logger.debug(f"Starting operation: {operation_name}")
        yield
        
        duration = time.time() - start_time
        logger.info(
            f"Operation completed: {operation_name}",
            extra={"operation": operation_name, "duration": round(duration * 1000, 2)}
        )
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Operation failed: {operation_name}",
            extra={
                "operation": operation_name,
                "duration": round(duration * 1000, 2),
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise

class PerformanceLogger:
    """Helper class for performance monitoring"""
    
    def __init__(self, logger_name: str = "app.performance"):
        self.logger = logging.getLogger(logger_name)
        self.start_times = {}
    
    def start_timer(self, operation: str) -> str:
        """Start timing an operation"""
        timer_id = f"{operation}_{uuid.uuid4().hex[:8]}"
        self.start_times[timer_id] = time.time()
        return timer_id
    
    def end_timer(self, timer_id: str, operation: str, **extra_data):
        """End timing and log performance"""
        if timer_id not in self.start_times:
            self.logger.warning(f"Timer {timer_id} not found for operation {operation}")
            return
        
        duration = time.time() - self.start_times.pop(timer_id)
        
        log_data = {
            "operation": operation,
            "duration": round(duration * 1000, 2),
            **extra_data
        }
        
        self.logger.info(f"Performance: {operation}", extra=log_data)
    
    def log_memory_usage(self, operation: str):
        """Log memory usage for an operation"""
        try:
            import psutil
            process = psutil.Process()
            memory_info = process.memory_info()
            
            self.logger.info(
                f"Memory usage: {operation}",
                extra={
                    "operation": operation,
                    "memory_rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                    "memory_vms_mb": round(memory_info.vms / 1024 / 1024, 2)
                }
            )
        except ImportError:
            self.logger.warning("psutil not available for memory monitoring")

# Global performance logger instance
perf_logger = PerformanceLogger()

def setup_production_logging():
    """Setup logging for production environment"""
    setup_logging(
        level="INFO",
        use_json=True,
        log_file="/app/logs/application.log"
    )

def setup_development_logging():
    """Setup logging for development environment"""
    setup_logging(
        level="DEBUG",
        use_json=False,
        log_file=None
    )

# Export main components
__all__ = [
    'setup_logging',
    'MonitoringMiddleware',
    'monitor_function',
    'log_ai_request',
    'log_async_operation',
    'PerformanceLogger',
    'perf_logger',
    'RequestLogger',
    'setup_production_logging',
    'setup_development_logging'
]