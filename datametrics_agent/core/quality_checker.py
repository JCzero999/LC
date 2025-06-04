"""
Data quality checking module for DataMetrics Agent.

This module provides comprehensive data quality validation and monitoring
capabilities for ensuring data integrity and reliability.
"""

import time
from datetime import datetime
from typing import List, Optional

from datametrics_agent.core.config import Config
from datametrics_agent.core.exceptions import DataQualityError
from datametrics_agent.core.logging import get_logger
from datametrics_agent.core.models import (
    DataQualityCheck,
    DataQualityResult,
    DataQualityRule,
    DataQualityStatus,
)


class QualityChecker:
    """Handles data quality checks and validation."""
    
    def __init__(self, config: Config) -> None:
        """
        Initialize quality checker.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        self.logger.info("QualityChecker initialized")
    
    def run_checks(
        self,
        checks: List[DataQualityCheck],
        data_source: Optional[str] = None
    ) -> List[DataQualityResult]:
        """
        Run data quality checks.
        
        Args:
            checks: List of quality checks to run
            data_source: Override data source for all checks
            
        Returns:
            List[DataQualityResult]: Results of quality checks
        """
        results = []
        
        for check in checks:
            self.logger.info(f"Running quality check: {check.name}")
            
            try:
                check_results = self._run_single_check(check, data_source)
                results.extend(check_results)
                
            except Exception as e:
                self.logger.error(f"Quality check failed: {check.name} - {e}")
                
                # Create error result for each rule
                for rule in check.rules:
                    error_result = DataQualityResult(
                        check_name=check.name,
                        rule_name=rule.name,
                        status=DataQualityStatus.ERROR,
                        passed=False,
                        actual_value=None,
                        expected_threshold=rule.threshold,
                        message=f"Check execution failed: {e}",
                        execution_time_ms=0,
                        checked_at=datetime.now()
                    )
                    results.append(error_result)
        
        return results
    
    def _run_single_check(
        self,
        check: DataQualityCheck,
        data_source_override: Optional[str] = None
    ) -> List[DataQualityResult]:
        """Run a single data quality check."""
        results = []
        data_source = data_source_override or check.data_source
        
        # Get database connector
        from datametrics_agent.connectors.factory import ConnectorFactory
        
        db_config = self.config.get_data_source_config(data_source)
        connector = ConnectorFactory.create_connector(db_config)
        
        try:
            with connector:
                for rule in check.rules:
                    start_time = time.time()
                    
                    try:
                        result = self._run_rule(connector, check, rule)
                        execution_time = (time.time() - start_time) * 1000
                        result.execution_time_ms = execution_time
                        results.append(result)
                        
                    except Exception as e:
                        execution_time = (time.time() - start_time) * 1000
                        
                        error_result = DataQualityResult(
                            check_name=check.name,
                            rule_name=rule.name,
                            status=DataQualityStatus.ERROR,
                            passed=False,
                            actual_value=None,
                            expected_threshold=rule.threshold,
                            message=f"Rule execution failed: {e}",
                            execution_time_ms=execution_time,
                            checked_at=datetime.now()
                        )
                        results.append(error_result)
        
        finally:
            connector.close()
        
        return results
    
    def _run_rule(
        self,
        connector,
        check: DataQualityCheck,
        rule: DataQualityRule
    ) -> DataQualityResult:
        """Run a single data quality rule."""
        
        if rule.rule_type == "not_null":
            return self._check_not_null(connector, check, rule)
        elif rule.rule_type == "unique":
            return self._check_unique(connector, check, rule)
        elif rule.rule_type == "range":
            return self._check_range(connector, check, rule)
        elif rule.rule_type == "pattern":
            return self._check_pattern(connector, check, rule)
        elif rule.rule_type == "custom":
            return self._check_custom(connector, check, rule)
        else:
            raise DataQualityError(f"Unsupported rule type: {rule.rule_type}")
    
    def _check_not_null(
        self,
        connector,
        check: DataQualityCheck,
        rule: DataQualityRule
    ) -> DataQualityResult:
        """Check for null values in a column."""
        
        sql = f"""
        SELECT 
            COUNT(*) as total_rows,
            COUNT({rule.column}) as non_null_rows,
            (COUNT({rule.column}) * 1.0 / COUNT(*)) as completeness_ratio
        FROM {check.table_name}
        """
        
        if check.where_clause:
            sql += f" WHERE {check.where_clause}"
        
        result = connector.execute_query(sql)
        data = result.data[0] if result.data else {}
        
        total_rows = data.get('total_rows', 0)
        completeness_ratio = data.get('completeness_ratio', 0.0)
        
        passed = completeness_ratio >= rule.threshold
        status = DataQualityStatus.PASSED if passed else DataQualityStatus.FAILED
        
        message = (
            f"Completeness: {completeness_ratio:.2%} "
            f"({'✓' if passed else '✗'} threshold: {rule.threshold:.2%})"
        )
        
        return DataQualityResult(
            check_name=check.name,
            rule_name=rule.name,
            status=status,
            passed=passed,
            actual_value=completeness_ratio,
            expected_threshold=rule.threshold,
            message=message,
            execution_time_ms=0,  # Will be set by caller
            checked_at=datetime.now(),
            details={
                'total_rows': total_rows,
                'non_null_rows': data.get('non_null_rows', 0),
                'null_rows': total_rows - data.get('non_null_rows', 0)
            }
        )
    
    def _check_unique(
        self,
        connector,
        check: DataQualityCheck,
        rule: DataQualityRule
    ) -> DataQualityResult:
        """Check for unique values in a column."""
        
        sql = f"""
        SELECT 
            COUNT(*) as total_rows,
            COUNT(DISTINCT {rule.column}) as unique_values,
            (COUNT(DISTINCT {rule.column}) * 1.0 / COUNT(*)) as uniqueness_ratio
        FROM {check.table_name}
        """
        
        if check.where_clause:
            sql += f" WHERE {check.where_clause}"
        
        result = connector.execute_query(sql)
        data = result.data[0] if result.data else {}
        
        uniqueness_ratio = data.get('uniqueness_ratio', 0.0)
        passed = uniqueness_ratio >= rule.threshold
        status = DataQualityStatus.PASSED if passed else DataQualityStatus.FAILED
        
        message = (
            f"Uniqueness: {uniqueness_ratio:.2%} "
            f"({'✓' if passed else '✗'} threshold: {rule.threshold:.2%})"
        )
        
        return DataQualityResult(
            check_name=check.name,
            rule_name=rule.name,
            status=status,
            passed=passed,
            actual_value=uniqueness_ratio,
            expected_threshold=rule.threshold,
            message=message,
            execution_time_ms=0,
            checked_at=datetime.now(),
            details={
                'total_rows': data.get('total_rows', 0),
                'unique_values': data.get('unique_values', 0),
                'duplicate_rows': data.get('total_rows', 0) - data.get('unique_values', 0)
            }
        )
    
    def _check_range(
        self,
        connector,
        check: DataQualityCheck,
        rule: DataQualityRule
    ) -> DataQualityResult:
        """Check if values are within expected range."""
        
        min_value = rule.min_value
        max_value = rule.max_value
        
        conditions = []
        if min_value is not None:
            conditions.append(f"{rule.column} >= {min_value}")
        if max_value is not None:
            conditions.append(f"{rule.column} <= {max_value}")
        
        range_condition = " AND ".join(conditions)
        
        sql = f"""
        SELECT 
            COUNT(*) as total_rows,
            COUNT(CASE WHEN {range_condition} THEN 1 END) as in_range_rows,
            (COUNT(CASE WHEN {range_condition} THEN 1 END) * 1.0 / COUNT(*)) as in_range_ratio
        FROM {check.table_name}
        WHERE {rule.column} IS NOT NULL
        """
        
        if check.where_clause:
            sql += f" AND {check.where_clause}"
        
        result = connector.execute_query(sql)
        data = result.data[0] if result.data else {}
        
        in_range_ratio = data.get('in_range_ratio', 0.0)
        passed = in_range_ratio >= rule.threshold
        status = DataQualityStatus.PASSED if passed else DataQualityStatus.FAILED
        
        range_desc = f"[{min_value}, {max_value}]"
        message = (
            f"Values in range {range_desc}: {in_range_ratio:.2%} "
            f"({'✓' if passed else '✗'} threshold: {rule.threshold:.2%})"
        )
        
        return DataQualityResult(
            check_name=check.name,
            rule_name=rule.name,
            status=status,
            passed=passed,
            actual_value=in_range_ratio,
            expected_threshold=rule.threshold,
            message=message,
            execution_time_ms=0,
            checked_at=datetime.now(),
            details={
                'total_rows': data.get('total_rows', 0),
                'in_range_rows': data.get('in_range_rows', 0),
                'out_of_range_rows': data.get('total_rows', 0) - data.get('in_range_rows', 0),
                'min_value': min_value,
                'max_value': max_value
            }
        )
    
    def _check_pattern(
        self,
        connector,
        check: DataQualityCheck,
        rule: DataQualityRule
    ) -> DataQualityResult:
        """Check if values match expected pattern."""
        
        pattern = rule.pattern
        if not pattern:
            raise DataQualityError("Pattern is required for pattern rule")
        
        # Use database-specific pattern matching
        sql = f"""
        SELECT 
            COUNT(*) as total_rows,
            COUNT(CASE WHEN {rule.column} REGEXP '{pattern}' THEN 1 END) as matching_rows,
            (COUNT(CASE WHEN {rule.column} REGEXP '{pattern}' THEN 1 END) * 1.0 / COUNT(*)) as match_ratio
        FROM {check.table_name}
        WHERE {rule.column} IS NOT NULL
        """
        
        if check.where_clause:
            sql += f" AND {check.where_clause}"
        
        result = connector.execute_query(sql)
        data = result.data[0] if result.data else {}
        
        match_ratio = data.get('match_ratio', 0.0)
        passed = match_ratio >= rule.threshold
        status = DataQualityStatus.PASSED if passed else DataQualityStatus.FAILED
        
        message = (
            f"Pattern match '{pattern}': {match_ratio:.2%} "
            f"({'✓' if passed else '✗'} threshold: {rule.threshold:.2%})"
        )
        
        return DataQualityResult(
            check_name=check.name,
            rule_name=rule.name,
            status=status,
            passed=passed,
            actual_value=match_ratio,
            expected_threshold=rule.threshold,
            message=message,
            execution_time_ms=0,
            checked_at=datetime.now(),
            details={
                'total_rows': data.get('total_rows', 0),
                'matching_rows': data.get('matching_rows', 0),
                'non_matching_rows': data.get('total_rows', 0) - data.get('matching_rows', 0),
                'pattern': pattern
            }
        )
    
    def _check_custom(
        self,
        connector,
        check: DataQualityCheck,
        rule: DataQualityRule
    ) -> DataQualityResult:
        """Run custom SQL-based quality check."""
        
        if not rule.custom_sql:
            raise DataQualityError("Custom SQL is required for custom rule")
        
        result = connector.execute_query(rule.custom_sql)
        
        # Expect the custom SQL to return a single numeric value
        if not result.data:
            raise DataQualityError("Custom SQL returned no results")
        
        actual_value = list(result.data[0].values())[0]
        
        # Compare with threshold based on comparison operator
        comparison_op = rule.comparison_operator or "="
        
        if comparison_op == "=":
            passed = actual_value == rule.threshold
        elif comparison_op == "!=":
            passed = actual_value != rule.threshold
        elif comparison_op == "<":
            passed = actual_value < rule.threshold
        elif comparison_op == "<=":
            passed = actual_value <= rule.threshold
        elif comparison_op == ">":
            passed = actual_value > rule.threshold
        elif comparison_op == ">=":
            passed = actual_value >= rule.threshold
        else:
            raise DataQualityError(f"Unsupported comparison operator: {comparison_op}")
        
        status = DataQualityStatus.PASSED if passed else DataQualityStatus.FAILED
        
        message = (
            f"Custom check: {actual_value} {comparison_op} {rule.threshold} "
            f"({'✓' if passed else '✗'})"
        )
        
        return DataQualityResult(
            check_name=check.name,
            rule_name=rule.name,
            status=status,
            passed=passed,
            actual_value=actual_value,
            expected_threshold=rule.threshold,
            message=message,
            execution_time_ms=0,
            checked_at=datetime.now(),
            details={
                'custom_sql': rule.custom_sql,
                'comparison_operator': comparison_op
            }
        )