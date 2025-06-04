"""
Data models for DataMetrics Agent.

This module defines Pydantic models for all data structures used throughout
the application, including metrics, data sources, and analysis results.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class MetricType(str, Enum):
    """Types of metrics that can be created."""
    
    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    RATIO = "ratio"
    PERCENTAGE = "percentage"
    DISTINCT_COUNT = "distinct_count"
    MEDIAN = "median"
    PERCENTILE = "percentile"
    CUSTOM = "custom"


class AggregationPeriod(str, Enum):
    """Time periods for metric aggregation."""
    
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class DataSourceType(str, Enum):
    """Supported data source types."""
    
    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    CLICKHOUSE = "clickhouse"
    SQLITE = "sqlite"
    MONGODB = "mongodb"
    HIVE = "hive"
    SPARK = "spark"


class MetricStatus(str, Enum):
    """Status of a metric."""
    
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class Dimension(BaseModel):
    """Represents a dimension for metric analysis."""
    
    name: str = Field(..., description="Dimension name")
    column: str = Field(..., description="Database column name")
    data_type: str = Field(..., description="Data type of the dimension")
    description: Optional[str] = Field(None, description="Dimension description")
    
    @validator('name')
    def validate_name(cls, v: str) -> str:
        """Validate dimension name."""
        if not v.replace('_', '').isalnum():
            raise ValueError("Dimension name must be alphanumeric with underscores")
        return v


class Filter(BaseModel):
    """Represents a filter condition."""
    
    column: str = Field(..., description="Column to filter on")
    operator: str = Field(..., description="Filter operator (=, !=, >, <, IN, etc.)")
    value: Union[str, int, float, List[Any]] = Field(..., description="Filter value")
    
    @validator('operator')
    def validate_operator(cls, v: str) -> str:
        """Validate filter operator."""
        valid_operators = ['=', '!=', '>', '<', '>=', '<=', 'IN', 'NOT IN', 'LIKE', 'NOT LIKE', 'IS NULL', 'IS NOT NULL']
        if v.upper() not in valid_operators:
            raise ValueError(f"Invalid operator: {v}. Valid operators: {valid_operators}")
        return v.upper()


class MetricDefinition(BaseModel):
    """Defines a data metric."""
    
    id: Optional[str] = Field(None, description="Unique metric identifier")
    name: str = Field(..., description="Metric name")
    description: str = Field(..., description="Metric description")
    metric_type: MetricType = Field(..., description="Type of metric")
    
    # Data source information
    data_source: str = Field(..., description="Data source identifier")
    table_name: str = Field(..., description="Primary table name")
    
    # Metric calculation
    measure_column: Optional[str] = Field(None, description="Column to measure (for SUM, AVG, etc.)")
    count_distinct_column: Optional[str] = Field(None, description="Column for distinct count")
    custom_expression: Optional[str] = Field(None, description="Custom SQL expression")
    
    # Dimensions and filters
    dimensions: List[Dimension] = Field(default_factory=list, description="Metric dimensions")
    filters: List[Filter] = Field(default_factory=list, description="Default filters")
    
    # Time configuration
    time_column: Optional[str] = Field(None, description="Time column for temporal analysis")
    aggregation_period: Optional[AggregationPeriod] = Field(None, description="Default aggregation period")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Metric tags")
    owner: Optional[str] = Field(None, description="Metric owner")
    status: MetricStatus = Field(default=MetricStatus.DRAFT, description="Metric status")
    
    # Timestamps
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    @validator('name')
    def validate_name(cls, v: str) -> str:
        """Validate metric name."""
        if not v.replace('_', '').replace(' ', '').isalnum():
            raise ValueError("Metric name must be alphanumeric with spaces and underscores")
        return v
    
    @validator('custom_expression')
    def validate_custom_expression(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """Validate custom expression is provided for custom metric type."""
        if values.get('metric_type') == MetricType.CUSTOM and not v:
            raise ValueError("Custom expression is required for custom metric type")
        return v


class QueryRequest(BaseModel):
    """Request for querying a metric."""
    
    metric_id: str = Field(..., description="Metric identifier")
    
    # Time range
    start_date: Optional[datetime] = Field(None, description="Start date for query")
    end_date: Optional[datetime] = Field(None, description="End date for query")
    
    # Dimension filters
    dimension_filters: Dict[str, Any] = Field(default_factory=dict, description="Dimension-specific filters")
    
    # Additional filters
    additional_filters: List[Filter] = Field(default_factory=list, description="Additional filters")
    
    # Aggregation
    aggregation_period: Optional[AggregationPeriod] = Field(None, description="Aggregation period override")
    
    # Limits and sorting
    limit: Optional[int] = Field(None, description="Result limit")
    order_by: Optional[str] = Field(None, description="Order by column")
    order_direction: str = Field(default="DESC", description="Order direction")
    
    @validator('order_direction')
    def validate_order_direction(cls, v: str) -> str:
        """Validate order direction."""
        if v.upper() not in ['ASC', 'DESC']:
            raise ValueError("Order direction must be ASC or DESC")
        return v.upper()


class QueryResult(BaseModel):
    """Result of a metric query."""
    
    metric_id: str = Field(..., description="Metric identifier")
    query_request: QueryRequest = Field(..., description="Original query request")
    
    # Results
    data: List[Dict[str, Any]] = Field(..., description="Query result data")
    total_rows: int = Field(..., description="Total number of rows")
    
    # Execution metadata
    execution_time_ms: float = Field(..., description="Query execution time in milliseconds")
    generated_sql: str = Field(..., description="Generated SQL query")
    
    # Timestamps
    executed_at: datetime = Field(default_factory=datetime.utcnow, description="Execution timestamp")


class DataSource(BaseModel):
    """Represents a data source configuration."""
    
    id: str = Field(..., description="Data source identifier")
    name: str = Field(..., description="Data source name")
    type: DataSourceType = Field(..., description="Data source type")
    
    # Connection details
    connection_config: Dict[str, Any] = Field(..., description="Connection configuration")
    
    # Metadata
    description: Optional[str] = Field(None, description="Data source description")
    tags: List[str] = Field(default_factory=list, description="Data source tags")
    
    # Status
    is_active: bool = Field(default=True, description="Whether data source is active")
    last_tested: Optional[datetime] = Field(None, description="Last connection test timestamp")
    
    # Timestamps
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class TableMetadata(BaseModel):
    """Metadata about a database table."""
    
    table_name: str = Field(..., description="Table name")
    schema_name: Optional[str] = Field(None, description="Schema name")
    data_source_id: str = Field(..., description="Data source identifier")
    
    # Column information
    columns: List[Dict[str, Any]] = Field(..., description="Column metadata")
    
    # Statistics
    row_count: Optional[int] = Field(None, description="Approximate row count")
    size_bytes: Optional[int] = Field(None, description="Table size in bytes")
    
    # Timestamps
    last_analyzed: Optional[datetime] = Field(None, description="Last analysis timestamp")


class DataQualityCheck(BaseModel):
    """Represents a data quality check."""
    
    id: Optional[str] = Field(None, description="Check identifier")
    name: str = Field(..., description="Check name")
    description: str = Field(..., description="Check description")
    
    # Check configuration
    table_name: str = Field(..., description="Table to check")
    column_name: Optional[str] = Field(None, description="Column to check (if applicable)")
    check_type: str = Field(..., description="Type of check (null_count, duplicate_count, etc.)")
    threshold: Optional[float] = Field(None, description="Threshold for check")
    
    # Status
    is_active: bool = Field(default=True, description="Whether check is active")
    
    # Timestamps
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class DataQualityResult(BaseModel):
    """Result of a data quality check."""
    
    check_id: str = Field(..., description="Check identifier")
    
    # Results
    passed: bool = Field(..., description="Whether check passed")
    value: float = Field(..., description="Actual value measured")
    threshold: Optional[float] = Field(None, description="Threshold used")
    
    # Details
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")
    
    # Timestamps
    executed_at: datetime = Field(default_factory=datetime.utcnow, description="Execution timestamp")