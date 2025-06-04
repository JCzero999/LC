"""
DataMetrics Agent - 数据指标开发智能助手

A comprehensive AI-powered agent for data metrics development, management, and monitoring.
"""

__version__ = "0.1.0"
__author__ = "JCzero999"
__email__ = "jczero999@example.com"

from datametrics_agent.core.agent import MetricsAgent
from datametrics_agent.core.config import Config, load_config
from datametrics_agent.core.exceptions import (
    DataMetricsError,
    ConfigurationError,
    DatabaseConnectionError,
    MetricDefinitionError,
    SQLGenerationError,
)
from datametrics_agent.core.models import (
    MetricDefinition,
    MetricType,
    QueryRequest,
    QueryResult,
    DataQualityCheck,
    DataQualityResult,
)

__all__ = [
    "MetricsAgent",
    "Config",
    "load_config",
    "DataMetricsError",
    "ConfigurationError", 
    "DatabaseConnectionError",
    "MetricDefinitionError",
    "SQLGenerationError",
    "MetricDefinition",
    "MetricType",
    "QueryRequest",
    "QueryResult",
    "DataQualityCheck",
    "DataQualityResult",
]