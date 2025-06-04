"""
Metric management module for DataMetrics Agent.

This module handles the creation, storage, retrieval, and management
of metric definitions.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from datametrics_agent.core.config import Config
from datametrics_agent.core.exceptions import MetricDefinitionError
from datametrics_agent.core.logging import get_logger
from datametrics_agent.core.models import (
    Dimension,
    Filter,
    MetricDefinition,
    MetricStatus,
    MetricType,
)


class MetricManager:
    """Manages metric definitions and operations."""
    
    def __init__(self, config: Config) -> None:
        """
        Initialize metric manager.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # In-memory storage for now (should be replaced with database)
        self._metrics: Dict[str, MetricDefinition] = {}
        
        self.logger.info("MetricManager initialized")
    
    def create_metric(self, metric_params: Dict[str, Any]) -> MetricDefinition:
        """
        Create a new metric definition.
        
        Args:
            metric_params: Parameters for metric creation
            
        Returns:
            MetricDefinition: Created metric definition
            
        Raises:
            MetricDefinitionError: If metric creation fails
        """
        try:
            # Generate unique ID
            metric_id = str(uuid.uuid4())
            
            # Extract and validate parameters
            name = metric_params.get('name', 'Unnamed Metric')
            description = metric_params.get('description', '')
            metric_type = self._parse_metric_type(metric_params.get('metric_type', MetricType.COUNT))
            
            # Build dimensions
            dimensions = self._build_dimensions(metric_params.get('dimensions', []))
            
            # Build filters
            filters = self._build_filters(metric_params.get('filters', []))
            
            # Create metric definition
            metric = MetricDefinition(
                id=metric_id,
                name=name,
                description=description,
                metric_type=metric_type,
                data_source=metric_params.get('data_source', ''),
                table_name=metric_params.get('table_name', ''),
                measure_column=metric_params.get('measure_column'),
                count_distinct_column=metric_params.get('count_distinct_column'),
                time_column=metric_params.get('time_column'),
                custom_expression=metric_params.get('custom_expression'),
                dimensions=dimensions,
                filters=filters,
                tags=metric_params.get('tags', []),
                owner=metric_params.get('owner', 'system'),
                status=MetricStatus.ACTIVE,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Validate metric
            self._validate_metric(metric)
            
            # Store metric
            self._metrics[metric_id] = metric
            
            self.logger.info(f"Created metric: {name} ({metric_id})")
            return metric
            
        except Exception as e:
            self.logger.error(f"Failed to create metric: {e}")
            raise MetricDefinitionError(f"Failed to create metric: {e}")
    
    def get_metric(self, metric_id: str) -> Optional[MetricDefinition]:
        """
        Retrieve a metric by ID.
        
        Args:
            metric_id: Metric identifier
            
        Returns:
            MetricDefinition: Metric definition or None if not found
        """
        return self._metrics.get(metric_id)
    
    def list_metrics(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None
    ) -> List[MetricDefinition]:
        """
        List metrics with optional filtering.
        
        Args:
            filters: Optional filters to apply
            limit: Maximum number of metrics to return
            
        Returns:
            List[MetricDefinition]: List of metrics
        """
        metrics = list(self._metrics.values())
        
        # Apply filters
        if filters:
            metrics = self._apply_filters(metrics, filters)
        
        # Sort by creation date (newest first)
        metrics.sort(key=lambda m: m.created_at, reverse=True)
        
        # Apply limit
        if limit:
            metrics = metrics[:limit]
        
        return metrics
    
    def update_metric(self, metric_id: str, updates: Dict[str, Any]) -> MetricDefinition:
        """
        Update an existing metric.
        
        Args:
            metric_id: Metric identifier
            updates: Dictionary of updates to apply
            
        Returns:
            MetricDefinition: Updated metric definition
            
        Raises:
            MetricDefinitionError: If metric not found or update fails
        """
        metric = self._metrics.get(metric_id)
        if not metric:
            raise MetricDefinitionError(f"Metric not found: {metric_id}")
        
        try:
            # Create updated metric
            metric_dict = metric.dict()
            metric_dict.update(updates)
            metric_dict['updated_at'] = datetime.now()
            
            # Parse updated fields
            if 'metric_type' in updates:
                metric_dict['metric_type'] = self._parse_metric_type(updates['metric_type'])
            
            if 'dimensions' in updates:
                metric_dict['dimensions'] = self._build_dimensions(updates['dimensions'])
            
            if 'filters' in updates:
                metric_dict['filters'] = self._build_filters(updates['filters'])
            
            # Create new metric instance
            updated_metric = MetricDefinition(**metric_dict)
            
            # Validate updated metric
            self._validate_metric(updated_metric)
            
            # Store updated metric
            self._metrics[metric_id] = updated_metric
            
            self.logger.info(f"Updated metric: {metric_id}")
            return updated_metric
            
        except Exception as e:
            self.logger.error(f"Failed to update metric {metric_id}: {e}")
            raise MetricDefinitionError(f"Failed to update metric: {e}")
    
    def delete_metric(self, metric_id: str) -> bool:
        """
        Delete a metric.
        
        Args:
            metric_id: Metric identifier
            
        Returns:
            bool: True if deleted successfully
        """
        if metric_id in self._metrics:
            del self._metrics[metric_id]
            self.logger.info(f"Deleted metric: {metric_id}")
            return True
        
        return False
    
    def _parse_metric_type(self, metric_type: Any) -> MetricType:
        """Parse metric type from various input formats."""
        if isinstance(metric_type, MetricType):
            return metric_type
        
        if isinstance(metric_type, str):
            try:
                return MetricType(metric_type.lower())
            except ValueError:
                # Try to map common variations
                type_mapping = {
                    'count': MetricType.COUNT,
                    'sum': MetricType.SUM,
                    'avg': MetricType.AVERAGE,
                    'average': MetricType.AVERAGE,
                    'distinct': MetricType.DISTINCT_COUNT,
                    'distinct_count': MetricType.DISTINCT_COUNT,
                    'unique': MetricType.DISTINCT_COUNT,
                    'ratio': MetricType.RATIO,
                    'percentage': MetricType.PERCENTAGE,
                    'median': MetricType.MEDIAN,
                    'custom': MetricType.CUSTOM
                }
                
                return type_mapping.get(metric_type.lower(), MetricType.COUNT)
        
        return MetricType.COUNT  # Default
    
    def _build_dimensions(self, dimensions_data: List[Any]) -> List[Dimension]:
        """Build dimension objects from input data."""
        dimensions = []
        
        for dim_data in dimensions_data:
            if isinstance(dim_data, Dimension):
                dimensions.append(dim_data)
            elif isinstance(dim_data, dict):
                dimensions.append(Dimension(**dim_data))
            elif isinstance(dim_data, str):
                # Simple string dimension
                dimensions.append(Dimension(
                    name=dim_data,
                    column=dim_data,
                    data_type="string",
                    description=f"Dimension: {dim_data}"
                ))
        
        return dimensions
    
    def _build_filters(self, filters_data: List[Any]) -> List[Filter]:
        """Build filter objects from input data."""
        filters = []
        
        for filter_data in filters_data:
            if isinstance(filter_data, Filter):
                filters.append(filter_data)
            elif isinstance(filter_data, dict):
                filters.append(Filter(**filter_data))
        
        return filters
    
    def _validate_metric(self, metric: MetricDefinition) -> None:
        """
        Validate a metric definition.
        
        Args:
            metric: Metric to validate
            
        Raises:
            MetricDefinitionError: If validation fails
        """
        # Check required fields
        if not metric.name:
            raise MetricDefinitionError("Metric name is required")
        
        if not metric.data_source:
            raise MetricDefinitionError("Data source is required")
        
        if not metric.table_name:
            raise MetricDefinitionError("Table name is required")
        
        # Validate metric type specific requirements
        if metric.metric_type == MetricType.SUM and not metric.measure_column:
            raise MetricDefinitionError("measure_column required for SUM metric")
        
        if metric.metric_type == MetricType.AVERAGE and not metric.measure_column:
            raise MetricDefinitionError("measure_column required for AVERAGE metric")
        
        if metric.metric_type == MetricType.DISTINCT_COUNT and not metric.count_distinct_column:
            raise MetricDefinitionError("count_distinct_column required for DISTINCT_COUNT metric")
        
        if metric.metric_type == MetricType.CUSTOM and not metric.custom_expression:
            raise MetricDefinitionError("custom_expression required for CUSTOM metric")
        
        # Validate data source exists in configuration
        try:
            self.config.get_data_source_config(metric.data_source)
        except Exception:
            raise MetricDefinitionError(f"Invalid data source: {metric.data_source}")
    
    def _apply_filters(
        self, 
        metrics: List[MetricDefinition], 
        filters: Dict[str, Any]
    ) -> List[MetricDefinition]:
        """Apply filters to metric list."""
        filtered_metrics = []
        
        for metric in metrics:
            include = True
            
            # Filter by status
            if 'status' in filters:
                if metric.status.value != filters['status']:
                    include = False
            
            # Filter by owner
            if 'owner' in filters:
                if metric.owner != filters['owner']:
                    include = False
            
            # Filter by metric type
            if 'metric_type' in filters:
                if metric.metric_type.value != filters['metric_type']:
                    include = False
            
            # Filter by data source
            if 'data_source' in filters:
                if metric.data_source != filters['data_source']:
                    include = False
            
            # Filter by tags
            if 'tags' in filters:
                filter_tags = filters['tags']
                if isinstance(filter_tags, str):
                    filter_tags = [filter_tags]
                
                if not any(tag in metric.tags for tag in filter_tags):
                    include = False
            
            if include:
                filtered_metrics.append(metric)
        
        return filtered_metrics