#!/usr/bin/env python3
"""
Advanced usage example for DataMetrics Agent.

This example demonstrates advanced features including custom metrics,
data quality checks, and monitoring capabilities.
"""

from datetime import datetime, timedelta
from typing import List

from datametrics_agent import MetricsAgent
from datametrics_agent.core.config import Config, DatabaseConfig
from datametrics_agent.core.models import (
    DataQualityCheck,
    DataQualityRule,
    Dimension,
    Filter,
    MetricDefinition,
    MetricType,
    QueryRequest,
)


def create_advanced_config() -> Config:
    """Create an advanced configuration with multiple data sources."""
    config = Config()
    
    # Configure multiple data sources
    config.databases["sources"] = {
        "analytics_db": DatabaseConfig(
            type="clickhouse",
            host="localhost",
            port=9000,
            database="analytics",
            username="analytics_user",
            password="analytics_password"
        ),
        "transactional_db": DatabaseConfig(
            type="postgresql",
            host="localhost",
            port=5432,
            database="transactions",
            username="trans_user",
            password="trans_password"
        ),
        "warehouse_db": DatabaseConfig(
            type="mysql",
            host="localhost",
            port=3306,
            database="data_warehouse",
            username="warehouse_user",
            password="warehouse_password"
        )
    }
    
    # Enable all features
    config.features.update({
        "nlp_processing": True,
        "sql_optimization": True,
        "data_lineage": True,
        "real_time_monitoring": True,
        "auto_documentation": True
    })
    
    return config


def create_custom_metrics(agent: MetricsAgent) -> List[MetricDefinition]:
    """Create custom metrics with complex definitions."""
    metrics = []
    
    # 1. Custom cohort retention metric
    cohort_retention = MetricDefinition(
        name="7-Day User Retention",
        description="Percentage of users who return within 7 days of first visit",
        metric_type=MetricType.CUSTOM,
        data_source="analytics_db",
        table_name="user_events",
        custom_expression="""
        (COUNT(DISTINCT CASE 
            WHEN event_date BETWEEN first_visit_date AND first_visit_date + INTERVAL 7 DAY 
            AND event_date > first_visit_date 
            THEN user_id 
        END) * 100.0) / COUNT(DISTINCT user_id)
        """,
        dimensions=[
            Dimension(
                name="cohort_week",
                column="DATE_TRUNC('week', first_visit_date)",
                data_type="date",
                description="Week of first visit"
            )
        ],
        filters=[
            Filter(
                column="event_type",
                operator="=",
                value="page_view"
            )
        ],
        tags=["retention", "cohort", "user_behavior"]
    )
    metrics.append(cohort_retention)
    
    # 2. Revenue per customer segment
    revenue_per_segment = MetricDefinition(
        name="Revenue per Customer Segment",
        description="Average revenue per customer by segment",
        metric_type=MetricType.CUSTOM,
        data_source="transactional_db",
        table_name="orders o JOIN customers c ON o.customer_id = c.id",
        custom_expression="SUM(o.total_amount) / COUNT(DISTINCT o.customer_id)",
        dimensions=[
            Dimension(
                name="customer_segment",
                column="c.segment",
                data_type="string",
                description="Customer segment"
            ),
            Dimension(
                name="month",
                column="DATE_TRUNC('month', o.created_at)",
                data_type="date",
                description="Order month"
            )
        ],
        filters=[
            Filter(
                column="o.status",
                operator="=",
                value="completed"
            )
        ],
        tags=["revenue", "segmentation", "customer_analysis"]
    )
    metrics.append(revenue_per_segment)
    
    # 3. Product performance metric
    product_performance = MetricDefinition(
        name="Product Performance Score",
        description="Composite score based on sales, reviews, and returns",
        metric_type=MetricType.CUSTOM,
        data_source="warehouse_db",
        table_name="product_metrics",
        custom_expression="""
        (
            (sales_volume / MAX(sales_volume) OVER()) * 0.4 +
            (avg_rating / 5.0) * 0.3 +
            (1 - return_rate) * 0.3
        ) * 100
        """,
        dimensions=[
            Dimension(
                name="product_category",
                column="category",
                data_type="string",
                description="Product category"
            ),
            Dimension(
                name="brand",
                column="brand",
                data_type="string",
                description="Product brand"
            )
        ],
        tags=["product", "performance", "composite_metric"]
    )
    metrics.append(product_performance)
    
    return metrics


def create_data_quality_checks() -> List[DataQualityCheck]:
    """Create comprehensive data quality checks."""
    checks = []
    
    # 1. Completeness checks
    completeness_check = DataQualityCheck(
        name="User Events Completeness",
        description="Check for missing required fields in user events",
        data_source="analytics_db",
        table_name="user_events",
        rules=[
            DataQualityRule(
                name="user_id_not_null",
                description="User ID should not be null",
                rule_type="not_null",
                column="user_id",
                threshold=0.99
            ),
            DataQualityRule(
                name="event_timestamp_not_null",
                description="Event timestamp should not be null",
                rule_type="not_null",
                column="event_timestamp",
                threshold=1.0
            )
        ]
    )
    checks.append(completeness_check)
    
    # 2. Validity checks
    validity_check = DataQualityCheck(
        name="Order Data Validity",
        description="Check for valid order data",
        data_source="transactional_db",
        table_name="orders",
        rules=[
            DataQualityRule(
                name="positive_amount",
                description="Order amount should be positive",
                rule_type="custom",
                custom_sql="SELECT COUNT(*) FROM orders WHERE total_amount <= 0",
                threshold=0
            ),
            DataQualityRule(
                name="valid_status",
                description="Order status should be valid",
                rule_type="custom",
                custom_sql="""
                SELECT COUNT(*) FROM orders 
                WHERE status NOT IN ('pending', 'processing', 'completed', 'cancelled')
                """,
                threshold=0
            )
        ]
    )
    checks.append(validity_check)
    
    # 3. Consistency checks
    consistency_check = DataQualityCheck(
        name="Cross-Table Consistency",
        description="Check consistency between related tables",
        data_source="warehouse_db",
        table_name="fact_sales",
        rules=[
            DataQualityRule(
                name="customer_exists",
                description="All customer IDs should exist in customer table",
                rule_type="custom",
                custom_sql="""
                SELECT COUNT(*) FROM fact_sales fs
                LEFT JOIN dim_customers dc ON fs.customer_id = dc.customer_id
                WHERE dc.customer_id IS NULL
                """,
                threshold=0
            )
        ]
    )
    checks.append(consistency_check)
    
    return checks


async def advanced_example():
    """Run advanced usage examples."""
    print("🚀 DataMetrics Agent - Advanced Usage Example")
    print("=" * 55)
    
    # Initialize agent with advanced configuration
    config = create_advanced_config()
    agent = MetricsAgent(config=config)
    
    try:
        # Example 1: Create custom metrics
        print("\n📊 Example 1: Creating Custom Metrics")
        print("-" * 45)
        
        custom_metrics = create_custom_metrics(agent)
        
        for metric in custom_metrics:
            print(f"✅ Custom metric: {metric.name}")
            print(f"   Type: {metric.metric_type.value}")
            print(f"   Expression: {metric.custom_expression[:100]}...")
            
            # Generate SQL for the custom metric
            sql = agent.generate_sql(metric)
            print(f"   Generated SQL length: {len(sql)} characters")
            print()
        
        # Example 2: Data Quality Monitoring
        print("\n🔍 Example 2: Data Quality Checks")
        print("-" * 40)
        
        quality_checks = create_data_quality_checks()
        
        # Run quality checks (simulation)
        print("Running data quality checks...")
        for check in quality_checks:
            print(f"📋 Check: {check.name}")
            print(f"   Rules: {len(check.rules)}")
            print(f"   Target: {check.table_name}")
            
            # In a real scenario, you would run:
            # results = agent.check_data_quality([check])
            # for result in results:
            #     status = "✅ PASSED" if result.passed else "❌ FAILED"
            #     print(f"   {result.rule_name}: {status}")
        
        # Example 3: Complex Query with Multiple Dimensions
        print("\n📈 Example 3: Complex Multi-Dimensional Query")
        print("-" * 50)
        
        # Use the revenue per segment metric
        revenue_metric = custom_metrics[1]
        
        # Create a complex query request
        complex_query = QueryRequest(
            metric_id=revenue_metric.id or "revenue_per_segment",
            start_date=datetime.now() - timedelta(days=90),
            end_date=datetime.now(),
            dimension_filters={
                "customer_segment": "premium"
            },
            order_by="month",
            order_direction="DESC",
            limit=12
        )
        
        sql = agent.generate_sql(revenue_metric, complex_query)
        print("Generated complex query SQL:")
        print(sql)
        
        # Example 4: Metric Comparison and Analysis
        print("\n📊 Example 4: Metric Analysis")
        print("-" * 35)
        
        # Compare metrics across different time periods
        current_period = QueryRequest(
            metric_id="dau_metric",
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now()
        )
        
        previous_period = QueryRequest(
            metric_id="dau_metric",
            start_date=datetime.now() - timedelta(days=60),
            end_date=datetime.now() - timedelta(days=30)
        )
        
        print("Period comparison setup:")
        print(f"Current: {current_period.start_date.date()} to {current_period.end_date.date()}")
        print(f"Previous: {previous_period.start_date.date()} to {previous_period.end_date.date()}")
        
        # Example 5: Automated Alerting Setup
        print("\n🚨 Example 5: Automated Alerting")
        print("-" * 40)
        
        # Define alert conditions
        alert_conditions = [
            {
                "metric_id": "dau_metric",
                "condition": "value < 1000",
                "severity": "high",
                "notification_channels": ["email", "slack"]
            },
            {
                "metric_id": "revenue_per_segment",
                "condition": "change_percent < -10",
                "severity": "medium",
                "notification_channels": ["email"]
            }
        ]
        
        print("Alert conditions configured:")
        for alert in alert_conditions:
            print(f"  • {alert['metric_id']}: {alert['condition']} ({alert['severity']})")
        
        # Example 6: Metric Lineage and Dependencies
        print("\n🔗 Example 6: Metric Lineage")
        print("-" * 35)
        
        # Show metric dependencies
        for metric in custom_metrics:
            print(f"📊 {metric.name}")
            print(f"   Data Source: {metric.data_source}")
            print(f"   Tables: {metric.table_name}")
            print(f"   Dependencies: {len(metric.dimensions)} dimensions, {len(metric.filters)} filters")
            print()
        
        # Example 7: Performance Optimization
        print("\n⚡ Example 7: Performance Optimization")
        print("-" * 45)
        
        optimization_tips = [
            "✅ Use appropriate indexes on dimension columns",
            "✅ Partition large tables by time",
            "✅ Use materialized views for complex metrics",
            "✅ Cache frequently accessed metric results",
            "✅ Optimize SQL queries with EXPLAIN PLAN"
        ]
        
        for tip in optimization_tips:
            print(f"  {tip}")
        
    except Exception as e:
        print(f"❌ Error in advanced example: {e}")
    
    finally:
        agent.close()
        print("\n🏁 Advanced example completed!")


def monitoring_example():
    """Example of monitoring and observability features."""
    print("\n📊 Monitoring and Observability")
    print("=" * 40)
    
    monitoring_features = [
        "📈 Real-time metric computation",
        "🔔 Automated alerting on anomalies",
        "📊 Performance dashboards",
        "🔍 Query performance tracking",
        "📝 Audit logs for all operations",
        "🎯 SLA monitoring and reporting",
        "🔄 Data freshness monitoring",
        "⚠️  Error rate and failure tracking"
    ]
    
    for feature in monitoring_features:
        print(f"  {feature}")


def best_practices():
    """Show best practices for using DataMetrics Agent."""
    print("\n💡 Best Practices")
    print("=" * 25)
    
    practices = [
        "🏗️  Design metrics with clear business context",
        "📝 Use descriptive names and documentation",
        "🔍 Implement comprehensive data quality checks",
        "⚡ Optimize queries for performance",
        "🔒 Implement proper access controls",
        "📊 Monitor metric computation performance",
        "🔄 Version control metric definitions",
        "🧪 Test metrics thoroughly before production",
        "📈 Set up alerting for critical metrics",
        "🎯 Regular review and cleanup of unused metrics"
    ]
    
    for practice in practices:
        print(f"  {practice}")


if __name__ == "__main__":
    import asyncio
    
    # Run advanced examples
    asyncio.run(advanced_example())
    
    # Show monitoring features
    monitoring_example()
    
    # Show best practices
    best_practices()