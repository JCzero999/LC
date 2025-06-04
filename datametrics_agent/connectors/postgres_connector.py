"""
PostgreSQL database connector.

This module provides PostgreSQL connectivity using SQLAlchemy and psycopg2.
"""

import time
from typing import Any, Dict, List, Optional

import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

from datametrics_agent.core.config import DatabaseConfig
from datametrics_agent.core.exceptions import DatabaseConnectionError
from datametrics_agent.core.models import QueryRequest, QueryResult
from datametrics_agent.connectors.base import BaseConnector


class PostgreSQLConnector(BaseConnector):
    """PostgreSQL database connector."""
    
    def __init__(self, config: DatabaseConfig) -> None:
        """Initialize PostgreSQL connector."""
        super().__init__(config)
        self.engine = None
    
    def connect(self) -> None:
        """Establish PostgreSQL connection."""
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
            
            self.logger.info(f"Connected to PostgreSQL: {self.get_connection_string()}")
            
        except Exception as e:
            self.logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise DatabaseConnectionError(f"PostgreSQL connection failed: {e}")
    
    def disconnect(self) -> None:
        """Close PostgreSQL connection."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.logger.info("PostgreSQL connection closed")
    
    def test_connection(self) -> bool:
        """Test PostgreSQL connection."""
        try:
            if not self.engine:
                self.connect()
            
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1 as test"))
                return result.fetchone()[0] == 1
                
        except Exception as e:
            self.logger.error(f"PostgreSQL connection test failed: {e}")
            return False
    
    def execute_query(
        self, 
        sql: str, 
        query_request: Optional[QueryRequest] = None,
        parameters: Optional[Dict[str, Any]] = None
    ) -> QueryResult:
        """Execute SQL query on PostgreSQL."""
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
            self.logger.error(f"PostgreSQL query execution failed: {e}")
            raise DatabaseConnectionError(f"Query execution failed: {e}")
    
    def get_table_metadata(self, table_name: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """Get PostgreSQL table metadata."""
        if not self.engine:
            self.connect()
        
        try:
            with self.engine.connect() as conn:
                # Get table information
                table_info_sql = """
                SELECT 
                    schemaname,
                    tablename,
                    tableowner,
                    hasindexes,
                    hasrules,
                    hastriggers
                FROM pg_tables 
                WHERE tablename = :table_name
                AND schemaname = :schema
                """
                
                schema = schema or "public"
                result = conn.execute(
                    text(table_info_sql), 
                    {"table_name": table_name, "schema": schema}
                )
                table_info = result.fetchone()
                
                if not table_info:
                    raise ValueError(f"Table {table_name} not found in schema {schema}")
                
                # Get table size
                size_sql = """
                SELECT pg_total_relation_size(:full_table_name) as size_bytes
                """
                full_table_name = f"{schema}.{table_name}"
                size_result = conn.execute(text(size_sql), {"full_table_name": full_table_name})
                size_info = size_result.fetchone()
                
                # Get row count estimate
                count_sql = """
                SELECT reltuples::BIGINT as estimated_rows
                FROM pg_class 
                WHERE relname = :table_name
                """
                count_result = conn.execute(text(count_sql), {"table_name": table_name})
                count_info = count_result.fetchone()
                
                # Get column information
                columns = self.get_column_info(table_name, schema)
                
                return {
                    "table_name": table_name,
                    "schema_name": schema,
                    "columns": columns,
                    "row_count": count_info[0] if count_info else 0,
                    "size_bytes": size_info[0] if size_info else 0,
                    "owner": table_info[2],
                    "has_indexes": table_info[3],
                    "has_rules": table_info[4],
                    "has_triggers": table_info[5]
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get table metadata: {e}")
            raise
    
    def get_table_list(self, schema: Optional[str] = None) -> List[str]:
        """Get list of tables in PostgreSQL database."""
        if not self.engine:
            self.connect()
        
        try:
            with self.engine.connect() as conn:
                sql = """
                SELECT tablename 
                FROM pg_tables 
                WHERE schemaname = :schema
                ORDER BY tablename
                """
                
                schema = schema or "public"
                result = conn.execute(text(sql), {"schema": schema})
                
                return [row[0] for row in result.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to get table list: {e}")
            raise
    
    def get_column_info(self, table_name: str, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get column information for PostgreSQL table."""
        if not self.engine:
            self.connect()
        
        try:
            with self.engine.connect() as conn:
                sql = """
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale,
                    ordinal_position
                FROM information_schema.columns 
                WHERE table_name = :table_name
                AND table_schema = :schema
                ORDER BY ordinal_position
                """
                
                schema = schema or "public"
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
                        "position": row[7]
                    })
                
                # Get primary key information
                pk_sql = """
                SELECT column_name
                FROM information_schema.key_column_usage
                WHERE table_name = :table_name
                AND table_schema = :schema
                AND constraint_name IN (
                    SELECT constraint_name
                    FROM information_schema.table_constraints
                    WHERE table_name = :table_name
                    AND table_schema = :schema
                    AND constraint_type = 'PRIMARY KEY'
                )
                """
                
                pk_result = conn.execute(
                    text(pk_sql),
                    {"table_name": table_name, "schema": schema}
                )
                pk_columns = {row[0] for row in pk_result.fetchall()}
                
                # Add primary key information to columns
                for column in columns:
                    column["is_primary_key"] = column["name"] in pk_columns
                
                return columns
                
        except Exception as e:
            self.logger.error(f"Failed to get column info: {e}")
            raise
    
    def _build_connection_string(self) -> str:
        """Build PostgreSQL connection string."""
        return (
            f"postgresql+psycopg2://{self.config.username}:{self.config.password}"
            f"@{self.config.host}:{self.config.port}/{self.config.database}"
        )