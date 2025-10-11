"""
Enhanced logging configuration for production deployment.
Provides structured logging with performance metrics and parsing decisions.
"""

import json
import logging
import logging.config
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Base log entry
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add request ID if available
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        
        # Add component information if available
        if hasattr(record, 'component'):
            log_entry['component'] = record.component
        
        # Add performance metrics if available
        if hasattr(record, 'duration_ms'):
            log_entry['duration_ms'] = record.duration_ms
        
        # Add parsing metadata if available
        if hasattr(record, 'parsing_metadata'):
            log_entry['parsing_metadata'] = record.parsing_metadata
        
        # Add confidence score if available
        if hasattr(record, 'confidence_score'):
            log_entry['confidence_score'] = record.confidence_score
        
        # Add error information for exceptions
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                          'filename', 'module', 'lineno', 'funcName', 'created',
                          'msecs', 'relativeCreated', 'thread', 'threadName',
                          'processName', 'process', 'getMessage', 'exc_info',
                          'exc_text', 'stack_info', 'request_id', 'component',
                          'duration_ms', 'parsing_metadata', 'confidence_score']:
                if not key.startswith('_'):
                    log_entry[key] = value
        
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class ParsingDecisionLogger:
    """Specialized logger for parsing decisions and performance metrics."""
    
    def __init__(self, logger_name: str = 'parsing_decisions'):
        self.logger = logging.getLogger(logger_name)
    
    def log_parsing_decision(self, request_id: str, text_length: int, 
                           routing_decisions: Dict[str, str],
                           confidence_breakdown: Dict[str, float],
                           processing_times: Dict[str, float],
                           final_confidence: float):
        """Log parsing routing decisions and performance metrics."""
        self.logger.info(
            "Parsing decision completed",
            extra={
                'request_id': request_id,
                'component': 'parsing_router',
                'text_length': text_length,
                'routing_decisions': routing_decisions,
                'confidence_breakdown': confidence_breakdown,
                'processing_times': processing_times,
                'final_confidence': final_confidence,
                'duration_ms': sum(processing_times.values())
            }
        )
    
    def log_component_performance(self, request_id: str, component: str,
                                duration_ms: float, success: bool,
                                metadata: Optional[Dict[str, Any]] = None):
        """Log individual component performance."""
        self.logger.info(
            f"Component {component} {'completed' if success else 'failed'}",
            extra={
                'request_id': request_id,
                'component': component,
                'duration_ms': duration_ms,
                'success': success,
                'parsing_metadata': metadata or {}
            }
        )
    
    def log_cache_operation(self, request_id: str, operation: str,
                          hit: bool, cache_key: str, duration_ms: float):
        """Log cache operations."""
        self.logger.info(
            f"Cache {operation} {'hit' if hit else 'miss'}",
            extra={
                'request_id': request_id,
                'component': 'cache_manager',
                'operation': operation,
                'cache_hit': hit,
                'cache_key': cache_key[:16] + '...' if len(cache_key) > 16 else cache_key,
                'duration_ms': duration_ms
            }
        )
    
    def log_llm_enhancement(self, request_id: str, fields_enhanced: list,
                          duration_ms: float, success: bool,
                          confidence_improvement: float):
        """Log LLM enhancement operations."""
        self.logger.info(
            f"LLM enhancement {'completed' if success else 'failed'}",
            extra={
                'request_id': request_id,
                'component': 'llm_enhancer',
                'fields_enhanced': fields_enhanced,
                'duration_ms': duration_ms,
                'success': success,
                'confidence_improvement': confidence_improvement
            }
        )
    
    def log_accuracy_evaluation(self, test_case_id: str, accuracy_score: float,
                              field_accuracies: Dict[str, float],
                              processing_time_ms: float):
        """Log accuracy evaluation results."""
        self.logger.info(
            "Accuracy evaluation completed",
            extra={
                'component': 'accuracy_evaluator',
                'test_case_id': test_case_id,
                'accuracy_score': accuracy_score,
                'field_accuracies': field_accuracies,
                'duration_ms': processing_time_ms
            }
        )


def setup_logging(log_level: str = "INFO", log_dir: str = "logs") -> None:
    """
    Setup comprehensive logging configuration for production.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Determine if we're in production
    environment = os.getenv('ENVIRONMENT', 'development')
    use_json_logging = environment == 'production'
    
    # Configure logging
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'structured': {
                '()': StructuredFormatter,
            },
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s:%(lineno)d]',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'simple': {
                'format': '%(levelname)s - %(message)s'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': log_level,
                'formatter': 'structured' if use_json_logging else 'detailed',
                'stream': sys.stdout
            },
            'file_all': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'structured' if use_json_logging else 'detailed',
                'filename': str(log_path / 'calendar-api.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf-8'
            },
            'file_errors': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'structured' if use_json_logging else 'detailed',
                'filename': str(log_path / 'calendar-api-errors.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 10,
                'encoding': 'utf-8'
            },
            'file_parsing': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'structured',
                'filename': str(log_path / 'parsing-decisions.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf-8'
            },
            'file_performance': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'structured',
                'filename': str(log_path / 'performance-metrics.log'),
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5,
                'encoding': 'utf-8'
            }
        },
        'loggers': {
            # Root logger
            '': {
                'level': log_level,
                'handlers': ['console', 'file_all', 'file_errors'],
                'propagate': False
            },
            # Application loggers
            'api': {
                'level': log_level,
                'handlers': ['console', 'file_all', 'file_errors'],
                'propagate': False
            },
            'services': {
                'level': log_level,
                'handlers': ['console', 'file_all', 'file_errors'],
                'propagate': False
            },
            # Specialized loggers
            'parsing_decisions': {
                'level': 'INFO',
                'handlers': ['file_parsing'],
                'propagate': False
            },
            'performance_metrics': {
                'level': 'INFO',
                'handlers': ['file_performance'],
                'propagate': False
            },
            # Third-party loggers (reduce noise)
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console', 'file_all'],
                'propagate': False
            },
            'uvicorn.access': {
                'level': 'INFO',
                'handlers': ['file_all'],
                'propagate': False
            },
            'fastapi': {
                'level': 'INFO',
                'handlers': ['console', 'file_all'],
                'propagate': False
            },
            # Silence noisy third-party loggers
            'urllib3': {
                'level': 'WARNING',
                'handlers': ['file_all'],
                'propagate': False
            },
            'requests': {
                'level': 'WARNING',
                'handlers': ['file_all'],
                'propagate': False
            }
        }
    }
    
    # Apply logging configuration
    logging.config.dictConfig(logging_config)
    
    # Log startup message
    logger = logging.getLogger('api.startup')
    logger.info(
        "Logging system initialized",
        extra={
            'component': 'logging_system',
            'log_level': log_level,
            'log_directory': str(log_path),
            'environment': environment,
            'json_logging': use_json_logging
        }
    )


# Global parsing decision logger instance
parsing_logger = ParsingDecisionLogger()


class LoggingMiddleware:
    """Middleware to add request context to logs."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Add request ID to logging context
            request_id = scope.get("request_id")
            if request_id:
                # This would require a more sophisticated logging context manager
                # For now, we'll rely on the middleware to pass request_id
                pass
        
        await self.app(scope, receive, send)


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: str, message: str,
                    request_id: Optional[str] = None,
                    component: Optional[str] = None,
                    **kwargs):
    """Log a message with additional context."""
    extra = {}
    
    if request_id:
        extra['request_id'] = request_id
    
    if component:
        extra['component'] = component
    
    # Add any additional keyword arguments
    extra.update(kwargs)
    
    # Get the logging method
    log_method = getattr(logger, level.lower())
    log_method(message, extra=extra)