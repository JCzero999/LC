"""
SQL generation module for DataMetrics Agent.

This module generates optimized SQL queries based on metric definitions
and query parameters.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from datametrics_agent.core.config import Config
from datametrics_agent.core.exceptions import SQLGenerationError
from datametrics_agent.core.logging import get_logger
from datametrics_agent.core.models import (
    AggregationPeriod,
    MetricDefinition,
    MetricType,
    QueryRequest,
)


class SQLGenerator:
    """Generates SQL queries for metrics."""
    
    def __init__(self, config: Config) -> None:
        """
        Initialize SQL generator.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
    
    def generate_sql(
        self, 
        metric: MetricDefinition, 
        query_request: Optional[QueryRequest] = None
    ) -> str:
        """
        Generate SQL query for a metric.
        
        Args:
            metric: Metric definition
            query_request: Query parameters
            
        Returns:
            str: Generated SQL query
            
        Raises:
            SQLGenerationError: If SQL generation fails
        """
        try:
            self.logger.info(f"Generating SQL for metric: {metric.name}")
            
            # Build SQL components
            select_clause = self._build_select_clause(metric, query_request)
            from_clause = self._build_from_clause(metric)
            where_clause = self._build_where_clause(metric, query_request)
            group_by_clause = self._build_group_by_clause(metric, query_request)
            having_clause = self._build_having_clause(metric, query_request)
            order_by_clause = self._build_order_by_clause(metric, query_request)
            limit_clause = self._build_limit_clause(query_request)
            
            # Combine clauses
            sql_parts = [select_clause, from_clause]
            
            if where_clause:
                sql_parts.append(where_clause)
            
            if group_by_clause:
                sql_parts.append(group_by_clause)
            
            if having_clause:
                sql_parts.append(having_clause)
            
            if order_by_clause:
                sql_parts.append(order_by_clause)
            
            if limit_clause:
                sql_parts.append(limit_clause)
            
            sql = '\n'.join(sql_parts)
            
            self.logger.debug(f"Generated SQL: {sql}")
            return sql
            
        except Exception as e:
            self.logger.error(f"SQL generation failed: {e}")
            raise SQLGenerationError(f"Failed to generate SQL: {e}")
    
    def _build_select_clause(
        self, 
        metric: MetricDefinition, 
        query_request: Optional[QueryRequest] = None
    ) -> str:
        """Build SELECT clause."""
        select_parts = []
        
        # Add dimensions
        for dimension in metric.dimensions:
            if metric.time_column and dimension.column == metric.time_column:
                # Handle time dimension with aggregation
                period = self._get_aggregation_period(metric, query_request)
                time_expr = self._build_time_expression(dimension.column, period)
                select_parts.append(f"{time_expr} AS {dimension.name}")
            else:
                select_parts.append(f"{dimension.column} AS {dimension.name}")
        
        # Add metric calculation
        metric_expr = self._build_metric_expression(metric)
        metric_name = metric.name.lower().replace(' ', '_')
        select_parts.append(f"{metric_expr} AS {metric_name}")
        
        return f"SELECT {', '.join(select_parts)}"
    
    def _build_metric_expression(self, metric: MetricDefinition) -> str:
        """Build metric calculation expression."""
        if metric.metric_type == MetricType.COUNT:
            return "COUNT(*)"
        
        elif metric.metric_type == MetricType.DISTINCT_COUNT:
            if not metric.count_distinct_column:
                raise SQLGenerationError("count_distinct_column required for DISTINCT_COUNT metric")
            return f"COUNT(DISTINCT {metric.count_distinct_column})"
        
        elif metric.metric_type == MetricType.SUM:
            if not metric.measure_column:
                raise SQLGenerationError("measure_column required for SUM metric")
            return f"SUM({metric.measure_column})"
        
        elif metric.metric_type == MetricType.AVERAGE:
            if not metric.measure_column:
                raise SQLGenerationError("measure_column required for AVERAGE metric")
            return f"AVG({metric.measure_column})"
        
        elif metric.metric_type == MetricType.MEDIAN:
            if not metric.measure_column:
                raise SQLGenerationError("measure_column required for MEDIAN metric")
            # Use database-specific median function
            return f"PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY {metric.measure_column})"
        
        elif metric.metric_type == MetricType.CUSTOM:
            if not metric.custom_expression:
                raise SQLGenerationError("custom_expression required for CUSTOM metric")
            return metric.custom_expression
        
        else:
            raise SQLGenerationError(f"Unsupported metric type: {metric.metric_type}")
    
    def _build_from_clause(self, metric: MetricDefinition) -> str:
        """Build FROM clause."""
        return f"FROM {metric.table_name}"
    
    def _build_where_clause(
        self, 
        metric: MetricDefinition, 
        query_request: Optional[QueryRequest] = None
    ) -> Optional[str]:
        """Build WHERE clause."""
        conditions = []
        
        # Add metric filters
        for filter_obj in metric.filters:
            condition = self._build_filter_condition(filter_obj.column, filter_obj.operator, filter_obj.value)
            conditions.append(condition)
        
        # Add query request filters
        if query_request:
            # Time range filters
            if query_request.start_date and metric.time_column:
                conditions.append(f"{metric.time_column} >= '{query_request.start_date}'")
            
            if query_request.end_date and metric.time_column:
                conditions.append(f"{metric.time_column} <= '{query_request.end_date}'")
            
            # Dimension filters
            for dim_name, dim_value in query_request.dimension_filters.items():
                # Find dimension by name
                dimension = next((d for d in metric.dimensions if d.name == dim_name), None)
                if dimension:
                    condition = self._build_filter_condition(dimension.column, '=', dim_value)
                    conditions.append(condition)
            
            # Additional filters
            for filter_obj in query_request.additional_filters:
                condition = self._build_filter_condition(filter_obj.column, filter_obj.operator, filter_obj.value)
                conditions.append(condition)
        
        if conditions:
            return f"WHERE {' AND '.join(conditions)}"
        
        return None
    
    def _build_filter_condition(self, column: str, operator: str, value: Any) -> str:
        """Build a filter condition."""
        if operator == '=':
            return f"{column} = '{value}'"
        elif operator == '!=':
            return f"{column} != '{value}'"
        elif operator in ['>', '<', '>=', '<=']:
            return f"{column} {operator} '{value}'"
        elif operator == 'IN':
            if isinstance(value, list):
                values = "', '".join(str(v) for v in value)
                return f"{column} IN ('{values}')"
            else:
                return f"{column} IN ({value})"
        elif operator == 'NOT IN':
            if isinstance(value, list):
                values = "', '".join(str(v) for v in value)
                return f"{column} NOT IN ('{values}')"
            else:
                return f"{column} NOT IN ({value})"
        elif operator == 'LIKE':
            return f"{column} LIKE '{value}'"
        elif operator == 'NOT LIKE':
            return f"{column} NOT LIKE '{value}'"
        elif operator == 'IS NULL':
            return f"{column} IS NULL"
        elif operator == 'IS NOT NULL':
            return f"{column} IS NOT NULL"
        else:
            raise SQLGenerationError(f"Unsupported operator: {operator}")
    
    def _build_group_by_clause(
        self, 
        metric: MetricDefinition, 
        query_request: Optional[QueryRequest] = None
    ) -> Optional[str]:
        """Build GROUP BY clause."""
        if not metric.dimensions:
            return None
        
        group_columns = []
        for i, dimension in enumerate(metric.dimensions, 1):
            if metric.time_column and dimension.column == metric.time_column:
                # Use the same time expression as in SELECT
                period = self._get_aggregation_period(metric, query_request)
                time_expr = self._build_time_expression(dimension.column, period)
                group_columns.append(time_expr)
            else:
                group_columns.append(dimension.column)
        
        return f"GROUP BY {', '.join(group_columns)}"
    
    def _build_having_clause(
        self, 
        metric: MetricDefinition, 
        query_request: Optional[QueryRequest] = None
    ) -> Optional[str]:
        """Build HAVING clause."""
        # For now, no HAVING clause logic
        return None
    
    def _build_order_by_clause(
        self, 
        metric: MetricDefinition, 
        query_request: Optional[QueryRequest] = None
    ) -> Optional[str]:
        """Build ORDER BY clause."""
        if query_request and query_request.order_by:
            return f"ORDER BY {query_request.order_by} {query_request.order_direction}"
        
        # Default ordering
        if metric.time_column:
            return f"ORDER BY {metric.time_column} DESC"
        
        return None
    
    def _build_limit_clause(self, query_request: Optional[QueryRequest] = None) -> Optional[str]:
        """Build LIMIT clause."""
        if query_request and query_request.limit:
            return f"LIMIT {query_request.limit}"
        
        return None
    
    def _get_aggregation_period(
        self, 
        metric: MetricDefinition, 
        query_request: Optional[QueryRequest] = None
    ) -> AggregationPeriod:
        """Get aggregation period for time-based metrics."""
        if query_request and query_request.aggregation_period:
            return query_request.aggregation_period
        
        if metric.aggregation_period:
            return metric.aggregation_period
        
        return AggregationPeriod.DAY  # Default
    
    def _build_time_expression(self, time_column: str, period: AggregationPeriod) -> str:
        """Build time aggregation expression."""
        # This is database-specific and should be customized per connector
        if period == AggregationPeriod.HOUR:
            return f"DATE_TRUNC('hour', {time_column})"
        elif period == AggregationPeriod.DAY:
            return f"DATE_TRUNC('day', {time_column})"
        elif period == AggregationPeriod.WEEK:
            return f"DATE_TRUNC('week', {time_column})"
        elif period == AggregationPeriod.MONTH:
            return f"DATE_TRUNC('month', {time_column})"
        elif period == AggregationPeriod.QUARTER:
            return f"DATE_TRUNC('quarter', {time_column})"
        elif period == AggregationPeriod.YEAR:
            return f"DATE_TRUNC('year', {time_column})"
        else:
            return time_column