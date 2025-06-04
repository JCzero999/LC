"""
MySQL database connector.

This module provides MySQL connectivity using SQLAlchemy and PyMySQL.
"""

import time
from typing import Any, Dict, List, Optional

import pymysql
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from datametrics_agent.core.config import DatabaseConfig
from datametrics_agent.core.exceptions import DatabaseConnectionError
from datametrics_agent.core.models import QueryRequest, QueryResult
from datametrics_agent.connectors.base import BaseConnector


class MySQLConnector(BaseConnector):
    """MySQL database connector."""
    
    def __init__(self, config: DatabaseConfig) -> None:
        """Initialize MySQL connector."""
        super().__init__(config)
        self.engine = None
    
    def connect(self) -> None:
        """Establish MySQL connection."""
        try:
            connection_string = self._build_connection_string()
            
            self.engine = create_engine(
                connection_string,
                poolclass=QueuePool,
                pool_size=self.config.pool_size,
                max_overflow=self.config.max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
            
            # Test the connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            self.logger.info(f"Connected to MySQL: {self.get_connection_string()}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MySQL: {e}")
            raise DatabaseConnectionError(f"MySQL connection failed: {e}")
    
    def disconnect(self) -> None:
        """Close MySQL connection."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.logger.info("MySQL connection closed")
    
    def test_connection(self) -> bool:
        """Test MySQL connection."""
        try:
            if not self.engine:
                self.connect()
            
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test"))
                return result.fetchone()[0] == 1
                
        except Exception as e:
            self.logger.error(f"MySQL connection test failed: {e}")
            return False
    
    def execute_query(
        self, 
        sql: str, 
        query_request: Optional[QueryRequest] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Execute SQL query on MySQL."""
        if not self.engine:
            self.connect()
        
        start_time = time.time()
        
        try:
            with self.engine.connect() as conn:
                if parameters:
                    result = conn.execute(text(sql), parameters)
                else:
                    result = conn.execute(text(sql))
                
                # Fetch all results
                rows = result.fetchall()
                columns = result.keys()
                
                # Convert to list of dictionaries
                data = [dict(zip(columns, row)) for row in rows]
                
                execution_time_ms = (time.time() - start_time) * 1000
                
                return QueryResult(
                    metric_id=query_request.metric_id if query_request else "unknown",
                    query_request=query_request or QueryRequest(metric_id="unknown"),
                    data=data,
                    total_rows=len(data),
                    execution_time_ms=execution_time_ms,
                    generated_sql=sql
                )
                
        except SQLAlchemyError as e:
            self.logger.error(f"MySQL query execution failed: {e}")
            raise DatabaseConnectionError(f"Query execution failed: {e}")
    
    def get_table_metadata(self, table_name: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """Get MySQL table metadata."""
        if not self.engine:
            self.connect()
        
        try:
            with self.engine.connect() as conn:
                # Get table information
                table_info_sql = """
                SELECT 
                    TABLE_SCHEMA,
                    TABLE_NAME,
                    TABLE_ROWS,
                    DATA_LENGTH,
                    INDEX_LENGTH,
                    CREATE_TIME,
                    UPDATE_TIME
                FROM information_schema.TABLES 
                WHERE TABLE_NAME = :table_name
                AND TABLE_SCHEMA = :schema
                """
                
                schema = schema or self.config.database
                result = conn.execute(
                    text(table_info_sql), 
                    {"table_name": table_name, "schema": schema}
                )
                table_info = result.fetchone()
                
                if not table_info:
                    raise ValueError(f"Table {table_name} not found in schema {schema}")
                
                # Get column information
                columns = self.get_column_info(table_name, schema)
                
                return {
                    "table_name": table_name,
                    "schema_name": schema,
                    "columns": columns,
                    "row_count": table_info[2] if table_info[2] else 0,
                    "size_bytes": (table_info[3] or 0) + (table_info[4] or 0),
                    "created_at": table_info[5],
                    "updated_at": table_info[6]
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get table metadata: {e}")
            raise
    
    def get_table_list(self, schema: Optional[str] = None) -> List[str]:
        """Get list of tables in MySQL database."""
        if not self.engine:
            self.connect()
        
        try:
            with self.engine.connect() as conn:
                sql = """
                SELECT TABLE_NAME 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = :schema
                AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
                """
                
                schema = schema or self.config.database
                result = conn.execute(text(sql), {"schema": schema})
                
                return [row[0] for row in result.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to get table list: {e}")
            raise
    
    def get_column_info(self, table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get column information for MySQL table."""
        if not self.engine:
            self.connect()
        
        try:
            with self.engine.connect() as conn:
                sql = """
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION,
                    NUMERIC_SCALE,
                    COLUMN_KEY,
                    EXTRA,
                    COLUMN_COMMENT
                FROM information_schema.COLUMNS 
                WHERE TABLE_NAME = :table_name
                AND TABLE_SCHEMA = :schema
                ORDER BY ORDINAL_POSITION
                """
                
                schema = schema or self.config.database
                result = conn.execute(
                    text(sql), 
                    {"table_name": table_name, "schema": schema}
                )
                
                columns = []
                for row in result.fetchall():
                    columns.append({
                        "name": row[0],
                        "data_type": row[1],
                        "nullable": row[2] == "YES",
                        "default": row[3],
                        "max_length": row[4],
                        "precision": row[5],
                        "scale": row[6],
                        "is_primary_key": row[7] == "PRI",
                        "is_auto_increment": "auto_increment" in (row[8] or "").lower(),
                        "comment": row[9]
                    })
                
                return columns
                
        except Exception as e:
            self.logger.error(f"Failed to get column info: {e}")
            raise
    
    def _build_connection_string(self) -> str:
        """Build MySQL connection string."""
        return (
            f"mysql+pymysql://{self.config.username}:{self.config.password}"
            f"@{self.config.host}:{self.config.port}/{self.config.database}"
            f"?charset=utf8mb4"
        )