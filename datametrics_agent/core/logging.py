"""
Logging configuration and utilities for DataMetrics Agent.

This module sets up structured logging with support for file rotation,
console output, and integration with monitoring systems.
"""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

from loguru import logger

from datametrics_agent.core.config import LoggingConfig


class LoggerManager:
    """Manages logging configuration and setup."""
    
    def __init__(self, config: LoggingConfig) -> None:
        self.config = config
        self._configured = False
    
    def setup_logging(self) -> None:
        """Set up logging based on configuration."""
        if self._configured:
            return
            
        # Remove default logger
        logger.remove()
        
        # Configure console logging
        if self.config.console.get('enabled', True):
            logger.add(
                sys.stderr,
                format=self.config.format,
                level=self.config.level,
                colorize=self.config.console.get('colorize', True),
                backtrace=True,
                diagnose=True,
            )
        
        # Configure file logging
        if self.config.file.get('enabled', True):
            log_path = Path(self.config.file.get('path', 'logs/datametrics_agent.log'))
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.add(
                log_path,
                format=self.config.format,
                level=self.config.level,
                rotation=self.config.rotation,
                retention=self.config.retention,
                compression=self.config.compression,
                backtrace=True,
                diagnose=True,
            )
        
        self._configured = True
    
    def get_logger(self, name: str) -> Any:
        """Get a logger instance for a specific module."""
        if not self._configured:
            self.setup_logging()
        return logger.bind(name=name)


# Global logger instance
_logger_manager: Optional[LoggerManager] = None


def setup_logging(config: LoggingConfig) -> None:
    """Set up global logging configuration."""
    global _logger_manager
    _logger_manager = LoggerManager(config)
    _logger_manager.setup_logging()


def get_logger(name: str) -> Any:
    """Get a logger instance for a specific module."""
    if _logger_manager is None:
        # Use default configuration if not set up
        from datametrics_agent.core.config import LoggingConfig
        setup_logging(LoggingConfig())
    
    return _logger_manager.get_logger(name)


def log_function_call(func_name: str, args: Dict[str, Any], result: Any = None, error: Exception = None) -> None:
    """Log function calls for debugging and monitoring."""
    logger_instance = get_logger("function_calls")
    
    if error:
        logger_instance.error(
            f"Function {func_name} failed",
            function=func_name,
            args=args,
            error=str(error),
            error_type=type(error).__name__
        )
    else:
        logger_instance.debug(
            f"Function {func_name} completed",
            function=func_name,
            args=args,
            result_type=type(result).__name__ if result is not None else None
        )