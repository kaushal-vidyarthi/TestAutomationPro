"""
Logging utilities and configuration for the test automation tool
"""

import logging
import logging.handlers
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import traceback

class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Add color to the log level
        if hasattr(record, 'levelname'):
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        
        return super().format(record)

class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for log files"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_entry['extra'] = record.extra_data
        
        return json.dumps(log_entry)

class TestLogger:
    """Enhanced logger for test automation with context tracking"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context = {}
    
    def set_context(self, **kwargs):
        """Set context information for subsequent log messages"""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear context information"""
        self.context.clear()
    
    def _log_with_context(self, level, message, *args, **kwargs):
        """Log message with context information"""
        if self.context:
            extra_data = kwargs.get('extra', {})
            extra_data.update(self.context)
            kwargs['extra'] = {'extra_data': extra_data}
        
        getattr(self.logger, level)(message, *args, **kwargs)
    
    def debug(self, message, *args, **kwargs):
        self._log_with_context('debug', message, *args, **kwargs)
    
    def info(self, message, *args, **kwargs):
        self._log_with_context('info', message, *args, **kwargs)
    
    def warning(self, message, *args, **kwargs):
        self._log_with_context('warning', message, *args, **kwargs)
    
    def error(self, message, *args, **kwargs):
        self._log_with_context('error', message, *args, **kwargs)
    
    def critical(self, message, *args, **kwargs):
        self._log_with_context('critical', message, *args, **kwargs)
    
    def exception(self, message, *args, **kwargs):
        """Log exception with traceback"""
        kwargs['exc_info'] = True
        self._log_with_context('error', message, *args, **kwargs)

def setup_logging(log_level: str = "INFO", 
                 log_file: Optional[Path] = None,
                 console_output: bool = True,
                 structured_logs: bool = True,
                 max_file_size: int = 10 * 1024 * 1024,  # 10MB
                 backup_count: int = 5) -> Dict[str, Any]:
    """
    Setup comprehensive logging configuration
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
        console_output: Whether to output to console
        structured_logs: Whether to use structured JSON logging for files
        max_file_size: Maximum size of log file before rotation
        backup_count: Number of backup files to keep
    
    Returns:
        Dictionary with logging configuration details
    """
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    handlers_info = []
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Use colored formatter for console
        console_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        console_formatter = ColoredFormatter(console_format)
        console_handler.setFormatter(console_formatter)
        
        root_logger.addHandler(console_handler)
        handlers_info.append({
            'type': 'console',
            'level': log_level,
            'formatter': 'colored'
        })
    
    # File handler
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Use rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(log_file),
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        
        # Choose formatter based on structured_logs setting
        if structured_logs:
            file_formatter = StructuredFormatter()
        else:
            file_format = '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
            file_formatter = logging.Formatter(file_format)
        
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        handlers_info.append({
            'type': 'file',
            'path': str(log_file),
            'level': log_level,
            'formatter': 'structured' if structured_logs else 'standard',
            'max_size': max_file_size,
            'backup_count': backup_count
        })
    
    # Configure specific loggers
    configure_specific_loggers()
    
    # Log initial setup message
    logging.info(f"Logging configured - Level: {log_level}, Handlers: {len(handlers_info)}")
    
    return {
        'log_level': log_level,
        'handlers': handlers_info,
        'setup_time': datetime.now().isoformat()
    }

def configure_specific_loggers():
    """Configure specific loggers for different components"""
    
    # Suppress verbose third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('playwright').setLevel(logging.WARNING)
    logging.getLogger('openai').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    # Set appropriate levels for our components
    logging.getLogger('crawler').setLevel(logging.INFO)
    logging.getLogger('ai').setLevel(logging.INFO)
    logging.getLogger('execution').setLevel(logging.INFO)
    logging.getLogger('storage').setLevel(logging.INFO)
    logging.getLogger('gui').setLevel(logging.WARNING)

def get_test_logger(name: str) -> TestLogger:
    """Get a test logger with enhanced functionality"""
    return TestLogger(name)

class LogCapture:
    """Context manager for capturing logs"""
    
    def __init__(self, logger_name: str = None, level: str = "INFO"):
        self.logger_name = logger_name
        self.level = getattr(logging, level.upper())
        self.logs = []
        self.handler = None
        self.original_level = None
    
    def __enter__(self):
        # Create custom handler that captures logs
        self.handler = LogCaptureHandler(self.logs)
        self.handler.setLevel(self.level)
        
        # Add handler to logger
        if self.logger_name:
            logger = logging.getLogger(self.logger_name)
        else:
            logger = logging.getLogger()
        
        self.original_level = logger.level
        logger.addHandler(self.handler)
        
        return self.logs
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Remove handler and restore original level
        if self.logger_name:
            logger = logging.getLogger(self.logger_name)
        else:
            logger = logging.getLogger()
        
        logger.removeHandler(self.handler)
        if self.original_level is not None:
            logger.setLevel(self.original_level)

class LogCaptureHandler(logging.Handler):
    """Handler that captures log records in a list"""
    
    def __init__(self, log_list):
        super().__init__()
        self.log_list = log_list
    
    def emit(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if record.exc_info:
            log_entry['exception'] = traceback.format_exception(*record.exc_info)
        
        self.log_list.append(log_entry)

def log_execution_time(func):
    """Decorator to log function execution time"""
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        start_time = datetime.now()
        
        try:
            logger.debug(f"Starting {func.__name__}")
            result = func(*args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.debug(f"Completed {func.__name__} in {duration:.3f}s")
            return result
        
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            logger.error(f"Failed {func.__name__} after {duration:.3f}s: {e}")
            raise
    
    return wrapper

def log_method_calls(cls):
    """Class decorator to log all method calls"""
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if callable(attr) and not attr_name.startswith('_'):
            setattr(cls, attr_name, log_execution_time(attr))
    return cls

class PerformanceLogger:
    """Logger for performance metrics and monitoring"""
    
    def __init__(self, name: str):
        self.logger = get_test_logger(f"performance.{name}")
        self.metrics = {}
        self.start_times = {}
    
    def start_timer(self, operation: str):
        """Start timing an operation"""
        self.start_times[operation] = datetime.now()
        self.logger.debug(f"Started timing: {operation}")
    
    def end_timer(self, operation: str) -> float:
        """End timing an operation and return duration"""
        if operation not in self.start_times:
            self.logger.warning(f"No start time found for operation: {operation}")
            return 0.0
        
        start_time = self.start_times.pop(operation)
        duration = (datetime.now() - start_time).total_seconds()
        
        self.metrics[operation] = self.metrics.get(operation, [])
        self.metrics[operation].append(duration)
        
        self.logger.info(f"Operation '{operation}' completed in {duration:.3f}s")
        return duration
    
    def log_metric(self, name: str, value: float, unit: str = ""):
        """Log a performance metric"""
        self.logger.info(f"Metric {name}: {value} {unit}")
        self.metrics[name] = self.metrics.get(name, [])
        self.metrics[name].append(value)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get performance statistics"""
        stats = {}
        
        for operation, values in self.metrics.items():
            if values:
                stats[operation] = {
                    'count': len(values),
                    'avg': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values),
                    'total': sum(values)
                }
        
        return stats
    
    def reset_metrics(self):
        """Reset all metrics"""
        self.metrics.clear()
        self.start_times.clear()
        self.logger.info("Performance metrics reset")

def setup_file_logging(log_file: Path, 
                      level: str = "INFO",
                      max_size: int = 10 * 1024 * 1024,
                      backup_count: int = 5) -> logging.Handler:
    """Setup file logging with rotation"""
    
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    handler = logging.handlers.RotatingFileHandler(
        filename=str(log_file),
        maxBytes=max_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    
    handler.setLevel(getattr(logging, level.upper()))
    
    # Use structured formatter
    formatter = StructuredFormatter()
    handler.setFormatter(formatter)
    
    return handler

def create_audit_logger(audit_file: Path) -> logging.Logger:
    """Create audit logger for security and compliance"""
    
    audit_logger = logging.getLogger('audit')
    audit_logger.setLevel(logging.INFO)
    
    # Ensure audit logs are never lost
    handler = logging.handlers.RotatingFileHandler(
        filename=str(audit_file),
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=10,
        encoding='utf-8'
    )
    
    # Use structured format for audit logs
    formatter = StructuredFormatter()
    handler.setFormatter(formatter)
    
    audit_logger.addHandler(handler)
    
    return audit_logger

# Global performance logger instance
perf_logger = None

def get_performance_logger(name: str = "default") -> PerformanceLogger:
    """Get global performance logger instance"""
    global perf_logger
    if perf_logger is None:
        perf_logger = PerformanceLogger(name)
    return perf_logger
