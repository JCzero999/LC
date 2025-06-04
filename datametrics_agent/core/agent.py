"""
Main MetricsAgent class - the core of DataMetrics Agent.

This module contains the primary agent class that orchestrates all functionality
including metric creation, SQL generation, data quality checks, and monitoring.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from datametrics_agent.core.config import Config, load_config
from datametrics_agent.core.exceptions import (
    ConfigurationError,
    DataMetricsError,
    MetricDefinitionError,
)
from datametrics_agent.core.logging import get_logger, setup_logging
from datametrics_agent.core.models import (
    DataQualityCheck,
    DataQualityResult,
    MetricDefinition,
    QueryRequest,
    QueryResult,
)


class MetricsAgent:
    """
    Main agent class for DataMetrics Agent.
    
    This class provides the primary interface for all data metrics operations
    including metric creation, SQL generation, data quality checks, and monitoring.
    """
    
    def __init__(
        self, 
        config_path: Optional[Union[str, Path]] = None,
        config: Optional[Config] = None
    ) -> None:
        """
        Initialize the MetricsAgent.
        
        Args:
            config_path: Path to configuration file
            config: Pre-loaded configuration object
            
        Raises:
            ConfigurationError: If configuration is invalid
        """
        self.logger = get_logger(__name__)
        
        # Load configuration
        if config is not None:
            self.config = config
        else:
            self.config = load_config(config_path)
        
        # Setup logging
        setup_logging(self.config.logging)
        
        # Validate configuration
        config_issues = self.config.validate_config()
        if config_issues:
            raise ConfigurationError(f"Configuration validation failed: {config_issues}")
        
        # Initialize components
        self._nlp_processor = None
        self._sql_generator = None
        self._metric_manager = None
        self._quality_checker = None
        self._monitoring = None
        self._connectors = {}
        
        self.logger.info("MetricsAgent initialized successfully")
    
    @property
    def nlp_processor(self):
        """Lazy-load NLP processor."""
        if self._nlp_processor is None:
            from datametrics_agent.core.nlp_processor import NLPProcessor
            self._nlp_processor = NLPProcessor(self.config)
        return self._nlp_processor
    
    @property
    def sql_generator(self):
        """Lazy-load SQL generator."""
        if self._sql_generator is None:
            from datametrics_agent.core.sql_generator import SQLGenerator
            self._sql_generator = SQLGenerator(self.config)
        return self._sql_generator
    
    @property
    def metric_manager(self):
        """Lazy-load metric manager."""
        if self._metric_manager is None:
            from datametrics_agent.core.metric_manager import MetricManager
            self._metric_manager = MetricManager(self.config)
        return self._metric_manager
    
    @property
    def quality_checker(self):
        """Lazy-load quality checker."""
        if self._quality_checker is None:
            from datametrics_agent.core.quality_checker import QualityChecker
            self._quality_checker = QualityChecker(self.config)
        return self._quality_checker
    
    def create_metric(
        self,
        description: str,
        dimensions: Optional[List[str]] = None,
        data_source: Optional[str] = None,
        **kwargs: Any
    ) -> MetricDefinition:
        """
        Create a new metric from natural language description.
        
        Args:
            description: Natural language description of the metric
            dimensions: List of dimension names
            data_source: Data source identifier
            **kwargs: Additional metric parameters
            
        Returns:
            MetricDefinition: Created metric definition
            
        Raises:
            MetricDefinitionError: If metric creation fails
        """
        try:
            self.logger.info(f"Creating metric from description: {description}")
            
            # Use NLP processor to understand the description
            if self.config.is_feature_enabled('nlp_processing'):
                parsed_info = self.nlp_processor.parse_metric_description(description)
                
                # Merge parsed information with provided parameters
                metric_params = {
                    'description': description,
                    'dimensions': dimensions or [],
                    'data_source': data_source,
                    **parsed_info,
                    **kwargs
                }
            else:
                # Fallback to manual specification
                metric_params = {
                    'description': description,
                    'dimensions': dimensions or [],
                    'data_source': data_source,
                    **kwargs
                }
            
            # Create metric definition
            metric = self.metric_manager.create_metric(metric_params)
            
            self.logger.info(f"Metric created successfully: {metric.id}")
            return metric
            
        except Exception as e:
            self.logger.error(f"Failed to create metric: {e}")
            raise MetricDefinitionError(f"Failed to create metric: {e}")
    
    def generate_sql(
        self, 
        metric: MetricDefinition,
        query_request: Optional[QueryRequest] = None
    ) -> str:
        """
        Generate SQL query for a metric.
        
        Args:
            metric: Metric definition
            query_request: Optional query parameters
            
        Returns:
            str: Generated SQL query
            
        Raises:
            SQLGenerationError: If SQL generation fails
        """
        try:
            self.logger.info(f"Generating SQL for metric: {metric.id}")
            
            sql = self.sql_generator.generate_sql(metric, query_request)
            
            self.logger.debug(f"Generated SQL: {sql}")
            return sql
            
        except Exception as e:
            self.logger.error(f"Failed to generate SQL: {e}")
            raise
    
    def execute_metric(
        self,
        metric: MetricDefinition,
        query_request: Optional[QueryRequest] = None,
        **kwargs: Any
    ) -> QueryResult:
        """
        Execute a metric query and return results.
        
        Args:
            metric: Metric definition
            query_request: Query parameters
            **kwargs: Additional execution parameters
            
        Returns:
            QueryResult: Query execution results
            
        Raises:
            DataMetricsError: If execution fails
        """
        try:
            self.logger.info(f"Executing metric: {metric.id}")
            
            # Create query request if not provided
            if query_request is None:
                query_request = QueryRequest(metric_id=metric.id or "unknown")
            
            # Generate SQL
            sql = self.generate_sql(metric, query_request)
            
            # Get database connector
            connector = self._get_connector(metric.data_source)
            
            # Execute query
            result = connector.execute_query(sql, query_request)
            
            self.logger.info(f"Metric executed successfully: {metric.id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to execute metric: {e}")
            raise
    
    def check_data_quality(
        self,
        checks: List[DataQualityCheck],
        data_source: Optional[str] = None
    ) -> List[DataQualityResult]:
        """
        Run data quality checks.
        
        Args:
            checks: List of quality checks to run
            data_source: Data source to check (if not specified in checks)
            
        Returns:
            List[DataQualityResult]: Results of quality checks
        """
        try:
            self.logger.info(f"Running {len(checks)} data quality checks")
            
            results = self.quality_checker.run_checks(checks, data_source)
            
            failed_checks = [r for r in results if not r.passed]
            if failed_checks:
                self.logger.warning(f"{len(failed_checks)} quality checks failed")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to run quality checks: {e}")
            raise
    
    def get_metric(self, metric_id: str) -> Optional[MetricDefinition]:
        """
        Retrieve a metric by ID.
        
        Args:
            metric_id: Metric identifier
            
        Returns:
            MetricDefinition: Metric definition or None if not found
        """
        return self.metric_manager.get_metric(metric_id)
    
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
        return self.metric_manager.list_metrics(filters, limit)
    
    def update_metric(
        self, 
        metric_id: str, 
        updates: Dict[str, Any]
    ) -> MetricDefinition:
        """
        Update an existing metric.
        
        Args:
            metric_id: Metric identifier
            updates: Dictionary of updates to apply
            
        Returns:
            MetricDefinition: Updated metric definition
        """
        return self.metric_manager.update_metric(metric_id, updates)
    
    def delete_metric(self, metric_id: str) -> bool:
        """
        Delete a metric.
        
        Args:
            metric_id: Metric identifier
            
        Returns:
            bool: True if deleted successfully
        """
        return self.metric_manager.delete_metric(metric_id)
    
    def test_connection(self, data_source: str) -> bool:
        """
        Test connection to a data source.
        
        Args:
            data_source: Data source identifier
            
        Returns:
            bool: True if connection successful
        """
        try:
            connector = self._get_connector(data_source)
            return connector.test_connection()
        except Exception as e:
            self.logger.error(f"Connection test failed for {data_source}: {e}")
            return False
    
    def get_table_metadata(self, data_source: str, table_name: str) -> Dict[str, Any]:
        """
        Get metadata for a table.
        
        Args:
            data_source: Data source identifier
            table_name: Table name
            
        Returns:
            Dict[str, Any]: Table metadata
        """
        connector = self._get_connector(data_source)
        return connector.get_table_metadata(table_name)
    
    def _get_connector(self, data_source: str):
        """Get or create a database connector."""
        if data_source not in self._connectors:
            from datametrics_agent.connectors.factory import ConnectorFactory
            
            config = self.config.get_data_source_config(data_source)
            self._connectors[data_source] = ConnectorFactory.create_connector(config)
        
        return self._connectors[data_source]
    
    def close(self) -> None:
        """Clean up resources."""
        self.logger.info("Closing MetricsAgent")
        
        # Close all connectors
        for connector in self._connectors.values():
            try:
                connector.close()
            except Exception as e:
                self.logger.warning(f"Error closing connector: {e}")
        
        self._connectors.clear()
        self.logger.info("MetricsAgent closed successfully")