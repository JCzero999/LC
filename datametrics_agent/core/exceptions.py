"""
Custom exceptions for DataMetrics Agent.

This module defines all custom exceptions used throughout the application
to provide clear error handling and debugging information.
"""

from typing import Any, Dict, Optional


class DataMetricsError(Exception):
    """Base exception class for all DataMetrics Agent errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ConfigurationError(DataMetricsError):
    """Raised when there's an error in configuration."""
    pass


class DatabaseConnectionError(DataMetricsError):
    """Raised when database connection fails."""
    pass


class MetricDefinitionError(DataMetricsError):
    """Raised when there's an error in metric definition."""
    pass


class SQLGenerationError(DataMetricsError):
    """Raised when SQL generation fails."""
    pass


class DataQualityError(DataMetricsError):
    """Raised when data quality checks fail."""
    pass


class MonitoringError(DataMetricsError):
    """Raised when monitoring operations fail."""
    pass


class AuthenticationError(DataMetricsError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(DataMetricsError):
    """Raised when authorization fails."""
    pass


class ValidationError(DataMetricsError):
    """Raised when data validation fails."""
    pass


class ProcessingError(DataMetricsError):
    """Raised when data processing fails."""
    pass


class TemplateError(DataMetricsError):
    """Raised when template processing fails."""
    pass


class AIServiceError(DataMetricsError):
    """Raised when AI service operations fail."""
    pass