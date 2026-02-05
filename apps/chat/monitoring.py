"""
Structured logging and monitoring for Gemini API calls
"""
import logging
import time
import functools
from typing import Any, Callable, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class APICallMonitor:
    """Monitor API calls to Gemini with structured logging"""
    
    def __init__(self):
        self.total_calls = 0
        self.failed_calls = 0
        self.total_tokens = 0
    
    def log_api_call(
        self,
        service: str,
        method: str,
        model: str,
        duration_ms: float,
        success: bool,
        error: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        **extra_fields
    ):
        """
        Log an API call with structured data
        
        Args:
            service: Service name (e.g., 'GeminiService', 'RolePlayEngine')
            method: Method name (e.g., 'evaluate_homework', 'generate_content')
            model: Model used (e.g., 'gemini-2.0-flash')
            duration_ms: Call duration in milliseconds
            success: Whether the call succeeded
            error: Error message if failed
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens generated
            **extra_fields: Additional fields to log
        """
        self.total_calls += 1
        self.total_tokens += input_tokens + output_tokens
        
        if not success:
            self.failed_calls += 1
        
        log_data = {
            'event_type': 'api_call',
            'service': service,
            'method': method,
            'model': model,
            'duration_ms': round(duration_ms, 2),
            'success': success,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'total_calls_session': self.total_calls,
            'failed_calls_session': self.failed_calls,
            'cumulative_tokens': self.total_tokens
        }
        
        if error:
            log_data['error'] = error
        
        # Add extra fields
        log_data.update(extra_fields)
        
        # Log with appropriate level
        if success:
            logger.info(
                f"API call: {service}.{method} completed in {duration_ms:.2f}ms",
                extra=log_data
            )
        else:
            logger.error(
                f"API call: {service}.{method} failed after {duration_ms:.2f}ms: {error}",
                extra=log_data
            )
    
    def get_stats(self):
        """Get current monitoring statistics"""
        return {
            'total_calls': self.total_calls,
            'failed_calls': self.failed_calls,
            'success_rate': (self.total_calls - self.failed_calls) / self.total_calls if self.total_calls > 0 else 0,
            'total_tokens': self.total_tokens
        }


# Global monitor instance
_monitor = APICallMonitor()


def get_monitor() -> APICallMonitor:
    """Get the global monitor instance"""
    return _monitor


def monitor_api_call(service: str, method: str, model: str):
    """
    Decorator to monitor API calls
    
    Usage:
        @monitor_api_call('GeminiService', 'evaluate_homework', 'gemini-2.0-flash')
        def evaluate_homework(self, ...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            success = False
            error = None
            result = None
            
            try:
                result = func(*args, **kwargs)
                success = True
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                duration_ms = (time.time() - start_time) * 1000
                
                # Extract token counts if available in result
                input_tokens = 0
                output_tokens = 0
                
                if isinstance(result, dict):
                    # Try to get token info from response
                    usage = result.get('usage', {})
                    input_tokens = usage.get('input_tokens', 0) or usage.get('prompt_tokens', 0)
                    output_tokens = usage.get('output_tokens', 0) or usage.get('candidates_tokens', 0)
                
                # Log the call
                _monitor.log_api_call(
                    service=service,
                    method=method,
                    model=model,
                    duration_ms=duration_ms,
                    success=success,
                    error=error,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens
                )
        
        return wrapper
    return decorator


def log_event(event_type: str, **fields):
    """
    Log a custom event with structured data
    
    Args:
        event_type: Type of event (e.g., 'user_action', 'system_error')
        **fields: Additional fields to log
    """
    log_data = {
        'event_type': event_type,
        **fields
    }
    
    logger.info(f"Event: {event_type}", extra=log_data)
