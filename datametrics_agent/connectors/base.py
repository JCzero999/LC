"""
Base database connector interface.

This module defines the abstract base class for all database connectors,
ensuring consistent interface across different database types.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from datametrics_agent.core.config import DatabaseConfig
from datametrics_agent.core.logging import get_logger
from datametrics_agent.core.models import QueryRequest, QueryResult


class BaseConnector(ABC):
    """Abstract base class for database connectors."""
    
    def __init__(self, config: DatabaseConfig) -> None:
        """
        Initialize the connector.
        
        Args:
            config: Database configuration
        """
        self.config = config
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self._connection = None
        self._connection_pool = None
    
    @abstractmethod
    def connect(self) -> None:
        """Establish database connection."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection."""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test database connection.
        
        Returns:
            bool: True if connection successful
        """
        pass
    
    @abstractmethod
    def execute_query(
        self, 
        sql: str, 
        query_request: Optional[QueryRequest] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """
        Execute a SQL query.
        
        Args:
            sql: SQL query to execute
            query_request: Original query request
            parameters: Query parameters
            
        Returns:
            QueryResult: Query execution results
        """
        pass
    
    @abstractmethod
    def get_table_metadata(self, table_name: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Get metadata for a table.
        
        Args:
            table_name: Table name
            schema: Schema name (optional)
            
        Returns:
            Dict[str, Any]: Table metadata including columns, types, etc.
        """
        pass
    
    @abstractmethod
    def get_table_list(self, schema: Optional[str] = None) -> List[str]:
        """
        Get list of tables in the database.
        
        Args:
            schema: Schema name (optional)
            
        Returns:
            List[str]: List of table names
        """
        pass
    
    @abstractmethod
    def get_column_info(self, table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get column information for a table.
        
        Args:
            table_name: Table name
            schema: Schema name (optional)
            
        Returns:
            List[Dict[str, Any]]: List of column information
        """
        pass
    
    def get_connection_string(self) -> str:
        """
        Get database connection string (without password).
        
        Returns:
            str: Connection string for logging
        """
        return f"{self.config.type}://{self.config.username}@{self.config.host}:{self.config.port}/{self.config.database}"
    
    def close(self) -> None:
        """Close the connector and clean up resources."""
        try:
            self.disconnect()
            self.logger.info(f"Connector closed: {self.get_connection_string()}")
        except Exception as e:
            self.logger.error(f"Error closing connector: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()