#!/usr/bin/env python3
"""
Basic usage example for DataMetrics Agent.

This example demonstrates how to use the DataMetrics Agent to create
and query metrics using natural language descriptions.
"""

import asyncio
from datetime import datetime, timedelta
from pathlib import Path

from datametrics_agent import MetricsAgent
from datametrics_agent.core.config import Config, DatabaseConfig
from datametrics_agent.core.models import QueryRequest


def create_sample_config() -> Config:
    """Create a sample configuration for the example."""
    config = Config()
    
    # Configure a sample MySQL data source
    config.databases["sources"] = {
        "sample_db": DatabaseConfig(
            type="mysql",
            host="localhost",
            port=3306,
            database="sample_ecommerce",
            username="demo_user",
            password="demo_password"
        )
    }
    
    # Enable NLP processing
    config.features["nlp_processing"] = True
    
    return config


async def main():
    """Main example function."""
    print("🚀 DataMetrics Agent - Basic Usage Example")
    print("=" * 50)
    
    # Initialize the agent
    config = create_sample_config()
    agent = MetricsAgent(config=config)
    
    try:
        # Example 1: Create a simple count metric
        print("\n📊 Example 1: Creating a Daily Active Users metric")
        print("-" * 40)
        
        dau_metric = agent.create_metric(
            description="Count unique users per day from user_events table",
            data_source="sample_db",
            dimensions=["date"]
        )
        
        print(f"✅ Created metric: {dau_metric.name}")
        print(f"   ID: {dau_metric.id}")
        print(f"   Type: {dau_metric.metric_type.value}")
        print(f"   Table: {dau_metric.table_name}")
        
        # Example 2: Create a revenue metric
        print("\n💰 Example 2: Creating a Total Revenue metric")
        print("-" * 40)
        
        revenue_metric = agent.create_metric(
            description="Sum of order amounts by day from orders table",
            data_source="sample_db",
            dimensions=["date", "region"]
        )
        
        print(f"✅ Created metric: {revenue_metric.name}")
        print(f"   ID: {revenue_metric.id}")
        print(f"   Type: {revenue_metric.metric_type.value}")
        print(f"   Measure Column: {revenue_metric.measure_column}")
        
        # Example 3: Generate SQL for a metric
        print("\n🔍 Example 3: Generating SQL")
        print("-" * 40)
        
        sql = agent.generate_sql(dau_metric)
        print("Generated SQL:")
        print(sql)
        
        # Example 4: Query a metric (simulation)
        print("\n📈 Example 4: Querying a metric")
        print("-" * 40)
        
        # Create a query request for the last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        query_request = QueryRequest(
            metric_id=dau_metric.id or "unknown",
            start_date=start_date,
            end_date=end_date,
            limit=100
        )
        
        print(f"Query period: {start_date.date()} to {end_date.date()}")
        print(f"Generated SQL for query:")
        query_sql = agent.generate_sql(dau_metric, query_request)
        print(query_sql)
        
        # Note: Actual execution would require a real database connection
        print("\n⚠️  Note: Actual query execution requires a configured database connection")
        
        # Example 5: List all metrics
        print("\n📋 Example 5: Listing all metrics")
        print("-" * 40)
        
        all_metrics = agent.list_metrics(limit=10)
        print(f"Found {len(all_metrics)} metrics:")
        
        for metric in all_metrics:
            print(f"  • {metric.name} ({metric.metric_type.value})")
        
        # Example 6: Advanced metric with filters
        print("\n🎯 Example 6: Creating a metric with filters")
        print("-" * 40)
        
        filtered_metric = agent.create_metric(
            description="Count of paid users who made purchases in the last 30 days",
            data_source="sample_db"
        )
        
        print(f"✅ Created filtered metric: {filtered_metric.name}")
        
        # Example 7: Test data source connection
        print("\n🔌 Example 7: Testing data source connection")
        print("-" * 40)
        
        # This would test the actual connection
        # connection_ok = agent.test_connection("sample_db")
        # print(f"Connection test: {'✅ Success' if connection_ok else '❌ Failed'}")
        print("⚠️  Connection test skipped (requires actual database)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # Clean up
        agent.close()
        print("\n🏁 Example completed!")


def cli_example():
    """Example of using the CLI interface."""
    print("\n🖥️  CLI Usage Examples")
    print("=" * 30)
    
    cli_commands = [
        "# Create a metric",
        "datametrics create-metric 'Daily active users from user_events'",
        "",
        "# Query a metric",
        "datametrics query-metric metric_001 --start-date 2024-01-01 --end-date 2024-01-31",
        "",
        "# List all metrics",
        "datametrics list-metrics --limit 20",
        "",
        "# Test database connection",
        "datametrics test-connection sample_db",
        "",
        "# Show help",
        "datametrics --help"
    ]
    
    for cmd in cli_commands:
        print(cmd)


def api_example():
    """Example of using the REST API."""
    print("\n🌐 REST API Usage Examples")
    print("=" * 35)
    
    api_examples = [
        "# Create a metric",
        "POST /metrics",
        '{"description": "Daily active users", "data_source": "sample_db"}',
        "",
        "# Query a metric",
        "POST /metrics/metric_001/query",
        '{"start_date": "2024-01-01", "end_date": "2024-01-31"}',
        "",
        "# List metrics",
        "GET /metrics?limit=20",
        "",
        "# Get specific metric",
        "GET /metrics/metric_001",
        "",
        "# Test data source",
        "POST /data-sources/sample_db/test"
    ]
    
    for example in api_examples:
        print(example)


if __name__ == "__main__":
    # Run the main example
    asyncio.run(main())
    
    # Show CLI examples
    cli_example()
    
    # Show API examples
    api_example()