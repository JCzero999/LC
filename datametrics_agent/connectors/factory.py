"""
Connector factory for creating database connectors.

This module provides a factory pattern for creating appropriate database
connectors based on configuration.
"""

from typing import Dict, Type

from datametrics_agent.core.config import DatabaseConfig
from datametrics_agent.core.exceptions import ConfigurationError
from datametrics_agent.connectors.base import BaseConnector


class ConnectorFactory:
    """Factory for creating database connectors."""
    
    _connectors: Dict[str, Type[BaseConnector]] = {}
    
    @classmethod
    def register_connector(cls, db_type: str, connector_class: Type[BaseConnector]) -> None:
        """
        Register a connector class for a database type.
        
        Args:
            db_type: Database type identifier
            connector_class: Connector class to register
        """
        cls._connectors[db_type.lower()] = connector_class
    
    @classmethod
    def create_connector(cls, config: DatabaseConfig) -> BaseConnector:
        """
        Create a connector instance based on configuration.
        
        Args:
            config: Database configuration
            
        Returns:
            BaseConnector: Appropriate connector instance
            
        Raises:
            ConfigurationError: If connector type is not supported
        """
        db_type = config.type.lower()
        
        if db_type not in cls._connectors:
            raise ConfigurationError(
                f"Unsupported database type: {db_type}. "
                f"Supported types: {list(cls._connectors.keys())}"
            )
        
        connector_class = cls._connectors[db_type]
        return connector_class(config)
    
    @classmethod
    def get_supported_types(cls) -> list[str]:
        """
        Get list of supported database types.
        
        Returns:
            List[str]: List of supported database types
        """
        return list(cls._connectors.keys())


# Register built-in connectors
def _register_builtin_connectors() -> None:
    """Register all built-in connectors."""
    
    # MySQL connector
    try:
        from datametrics_agent.connectors.mysql_connector import MySQLConnector
        ConnectorFactory.register_connector("mysql", MySQLConnector)
    except ImportError:
        pass
    
    # PostgreSQL connector
    try:
        from datametrics_agent.connectors.postgres_connector import PostgreSQLConnector
        ConnectorFactory.register_connector("postgresql", PostgreSQLConnector)
    except ImportError:
        pass
    
    # ClickHouse connector
    try:
        from datametrics_agent.connectors.clickhouse_connector import ClickHouseConnector
        ConnectorFactory.register_connector("clickhouse", ClickHouseConnector)
    except ImportError:
        pass
    
    # SQLite connector
    try:
        from datametrics_agent.connectors.sqlite_connector import SQLiteConnector
        ConnectorFactory.register_connector("sqlite", SQLiteConnector)
    except ImportError:
        pass


# Register connectors on module import
_register_builtin_connectors()