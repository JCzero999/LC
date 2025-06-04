"""
Pytest configuration and fixtures for DataMetrics Agent tests.

This module provides common fixtures and configuration for all tests.
"""

import pytest
from pathlib import Path
from typing import Dict, Any

from datametrics_agent import MetricsAgent
from datametrics_agent.core.config import Config, DatabaseConfig
from datametrics_agent.core.models import MetricDefinition, MetricType, Dimension


@pytest.fixture
def test_config() -> Config:
    """Create a test configuration."""
    config = Config()
    
    # Override with test settings
    config.app.debug = True
    config.app.log_level = "DEBUG"
    
    # Test database configuration
    config.databases = {
        "metadata": DatabaseConfig(
            type="sqlite",
            host="localhost",
            port=0,
            database=":memory:",
            username="test",
            password="test"
        ),
        "sources": {
            "test_mysql": DatabaseConfig(
                type="mysql",
                host="localhost",
                port=3306,
                database="test_db",
                username="test_user",
                password="test_password"
            )
        }
    }
    
    # Disable AI features for testing
    config.features = {
        "nlp_processing": False,
        "sql_optimization": True,
        "data_lineage": False,
        "real_time_monitoring": False,
        "auto_documentation": False
    }
    
    return config


@pytest.fixture
def agent(test_config: Config) -> MetricsAgent:
    """Create a test MetricsAgent instance."""
    return MetricsAgent(config=test_config)


@pytest.fixture
def sample_metric() -> MetricDefinition:
    """Create a sample metric definition for testing."""
    return MetricDefinition(
        id="test_metric_001",
        name="Daily Active Users",
        description="Count of unique users per day",
        metric_type=MetricType.DISTINCT_COUNT,
        data_source="test_mysql",
        table_name="user_events",
        count_distinct_column="user_id",
        time_column="created_at",
        dimensions=[
            Dimension(
                name="date",
                column="created_at",
                data_type="timestamp",
                description="Event date"
            ),
            Dimension(
                name="platform",
                column="platform",
                data_type="string",
                description="User platform"
            )
        ],
        tags=["user", "activity", "daily"],
        owner="test_user"
    )


@pytest.fixture
def sample_metrics() -> list[MetricDefinition]:
    """Create multiple sample metrics for testing."""
    return [
        MetricDefinition(
            id="metric_001",
            name="Daily Active Users",
            description="Count of unique users per day",
            metric_type=MetricType.DISTINCT_COUNT,
            data_source="test_mysql",
            table_name="user_events",
            count_distinct_column="user_id"
        ),
        MetricDefinition(
            id="metric_002",
            name="Total Revenue",
            description="Sum of all revenue",
            metric_type=MetricType.SUM,
            data_source="test_mysql",
            table_name="orders",
            measure_column="amount"
        ),
        MetricDefinition(
            id="metric_003",
            name="Average Order Value",
            description="Average value of orders",
            metric_type=MetricType.AVERAGE,
            data_source="test_mysql",
            table_name="orders",
            measure_column="amount"
        )
    ]


@pytest.fixture
def mock_database_data() -> Dict[str, Any]:
    """Mock database data for testing."""
    return {
        "user_events": [
            {"user_id": 1, "event_type": "login", "platform": "web", "created_at": "2024-01-01 10:00:00"},
            {"user_id": 2, "event_type": "login", "platform": "mobile", "created_at": "2024-01-01 11:00:00"},
            {"user_id": 1, "event_type": "view", "platform": "web", "created_at": "2024-01-01 12:00:00"},
            {"user_id": 3, "event_type": "login", "platform": "web", "created_at": "2024-01-02 09:00:00"},
        ],
        "orders": [
            {"order_id": 1, "user_id": 1, "amount": 100.0, "created_at": "2024-01-01 15:00:00"},
            {"order_id": 2, "user_id": 2, "amount": 250.0, "created_at": "2024-01-01 16:00:00"},
            {"order_id": 3, "user_id": 3, "amount": 75.0, "created_at": "2024-01-02 10:00:00"},
        ]
    }


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Get test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def temp_config_file(tmp_path: Path, test_config: Config) -> Path:
    """Create a temporary configuration file."""
    import yaml
    
    config_file = tmp_path / "test_config.yaml"
    
    # Convert config to dict for YAML serialization
    config_dict = {
        "app": {
            "name": test_config.app.name,
            "debug": test_config.app.debug,
            "log_level": test_config.app.log_level
        },
        "databases": {
            "metadata": {
                "type": "sqlite",
                "host": "localhost",
                "port": 0,
                "database": ":memory:",
                "username": "test",
                "password": "test"
            }
        },
        "features": test_config.features
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config_dict, f)
    
    return config_file