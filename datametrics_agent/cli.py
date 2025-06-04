"""
Command Line Interface for DataMetrics Agent.

This module provides a CLI for interacting with the DataMetrics Agent,
allowing users to create metrics, run queries, and manage the system.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from datametrics_agent import MetricsAgent
from datametrics_agent.core.config import load_config
from datametrics_agent.core.exceptions import DataMetricsError


console = Console()


@click.group()
@click.option(
    '--config', 
    '-c', 
    type=click.Path(exists=True), 
    help='Configuration file path'
)
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.pass_context
def cli(ctx: click.Context, config: Optional[str], debug: bool) -> None:
    """DataMetrics Agent CLI - Intelligent data metrics development assistant."""
    ctx.ensure_object(dict)
    
    try:
        # Load configuration
        if config:
            ctx.obj['config'] = load_config(Path(config))
        else:
            ctx.obj['config'] = load_config()
        
        # Set debug mode
        if debug:
            ctx.obj['config'].app.debug = True
            ctx.obj['config'].app.log_level = "DEBUG"
        
        # Initialize agent
        ctx.obj['agent'] = MetricsAgent(config=ctx.obj['config'])
        
    except Exception as e:
        console.print(f"[red]Error initializing DataMetrics Agent: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.argument('description')
@click.option('--data-source', '-d', help='Data source identifier')
@click.option('--dimensions', '-dim', multiple=True, help='Metric dimensions')
@click.option('--output', '-o', type=click.Choice(['json', 'table']), default='table', help='Output format')
@click.pass_context
def create_metric(
    ctx: click.Context, 
    description: str, 
    data_source: Optional[str],
    dimensions: tuple,
    output: str
) -> None:
    """Create a new metric from natural language description."""
    try:
        agent: MetricsAgent = ctx.obj['agent']
        
        console.print(f"[blue]Creating metric from description:[/blue] {description}")
        
        # Create metric
        metric = agent.create_metric(
            description=description,
            data_source=data_source,
            dimensions=list(dimensions) if dimensions else None
        )
        
        if output == 'json':
            console.print(json.dumps(metric.dict(), indent=2, default=str))
        else:
            _display_metric_table(metric)
        
        console.print(f"[green]✓ Metric created successfully with ID: {metric.id}[/green]")
        
    except DataMetricsError as e:
        console.print(f"[red]Error creating metric: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.argument('metric_id')
@click.option('--start-date', help='Start date (YYYY-MM-DD)')
@click.option('--end-date', help='End date (YYYY-MM-DD)')
@click.option('--limit', type=int, help='Limit number of results')
@click.option('--output', '-o', type=click.Choice(['json', 'table']), default='table', help='Output format')
@click.option('--show-sql', is_flag=True, help='Show generated SQL')
@click.pass_context
def query_metric(
    ctx: click.Context,
    metric_id: str,
    start_date: Optional[str],
    end_date: Optional[str],
    limit: Optional[int],
    output: str,
    show_sql: bool
) -> None:
    """Query a metric and display results."""
    try:
        agent: MetricsAgent = ctx.obj['agent']
        
        # Get metric
        metric = agent.get_metric(metric_id)
        if not metric:
            console.print(f"[red]Metric not found: {metric_id}[/red]")
            raise click.Abort()
        
        console.print(f"[blue]Querying metric:[/blue] {metric.name}")
        
        # Build query request
        from datametrics_agent.core.models import QueryRequest
        from datetime import datetime
        
        query_request = QueryRequest(metric_id=metric_id)
        
        if start_date:
            query_request.start_date = datetime.fromisoformat(start_date)
        if end_date:
            query_request.end_date = datetime.fromisoformat(end_date)
        if limit:
            query_request.limit = limit
        
        # Execute query
        result = agent.execute_metric(metric, query_request)
        
        # Show SQL if requested
        if show_sql:
            sql_syntax = Syntax(result.generated_sql, "sql", theme="monokai", line_numbers=True)
            console.print(Panel(sql_syntax, title="Generated SQL"))
        
        # Display results
        if output == 'json':
            console.print(json.dumps(result.dict(), indent=2, default=str))
        else:
            _display_query_results(result)
        
        console.print(f"[green]✓ Query completed in {result.execution_time_ms:.2f}ms[/green]")
        
    except DataMetricsError as e:
        console.print(f"[red]Error querying metric: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.option('--status', help='Filter by status')
@click.option('--owner', help='Filter by owner')
@click.option('--limit', type=int, default=20, help='Limit number of results')
@click.option('--output', '-o', type=click.Choice(['json', 'table']), default='table', help='Output format')
@click.pass_context
def list_metrics(
    ctx: click.Context,
    status: Optional[str],
    owner: Optional[str],
    limit: int,
    output: str
) -> None:
    """List all metrics with optional filtering."""
    try:
        agent: MetricsAgent = ctx.obj['agent']
        
        # Build filters
        filters = {}
        if status:
            filters['status'] = status
        if owner:
            filters['owner'] = owner
        
        # Get metrics
        metrics = agent.list_metrics(filters=filters, limit=limit)
        
        if output == 'json':
            console.print(json.dumps([m.dict() for m in metrics], indent=2, default=str))
        else:
            _display_metrics_list(metrics)
        
        console.print(f"[green]Found {len(metrics)} metrics[/green]")
        
    except DataMetricsError as e:
        console.print(f"[red]Error listing metrics: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.argument('data_source')
@click.pass_context
def test_connection(ctx: click.Context, data_source: str) -> None:
    """Test connection to a data source."""
    try:
        agent: MetricsAgent = ctx.obj['agent']
        
        console.print(f"[blue]Testing connection to:[/blue] {data_source}")
        
        success = agent.test_connection(data_source)
        
        if success:
            console.print(f"[green]✓ Connection successful[/green]")
        else:
            console.print(f"[red]✗ Connection failed[/red]")
            raise click.Abort()
        
    except DataMetricsError as e:
        console.print(f"[red]Error testing connection: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.argument('data_source')
@click.option('--schema', help='Schema name')
@click.pass_context
def list_tables(ctx: click.Context, data_source: str, schema: Optional[str]) -> None:
    """List tables in a data source."""
    try:
        agent: MetricsAgent = ctx.obj['agent']
        
        console.print(f"[blue]Listing tables in:[/blue] {data_source}")
        
        connector = agent._get_connector(data_source)
        tables = connector.get_table_list(schema)
        
        table = Table(title=f"Tables in {data_source}")
        table.add_column("Table Name", style="cyan")
        
        for table_name in tables:
            table.add_row(table_name)
        
        console.print(table)
        console.print(f"[green]Found {len(tables)} tables[/green]")
        
    except DataMetricsError as e:
        console.print(f"[red]Error listing tables: {e}[/red]")
        raise click.Abort()


@cli.command()
@click.pass_context
def version(ctx: click.Context) -> None:
    """Show version information."""
    from datametrics_agent import __version__
    
    console.print(f"[blue]DataMetrics Agent[/blue] version [green]{__version__}[/green]")


def _display_metric_table(metric) -> None:
    """Display metric information in a table."""
    table = Table(title=f"Metric: {metric.name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("ID", str(metric.id))
    table.add_row("Name", metric.name)
    table.add_row("Description", metric.description)
    table.add_row("Type", metric.metric_type.value)
    table.add_row("Data Source", metric.data_source)
    table.add_row("Table", metric.table_name)
    table.add_row("Status", metric.status.value)
    
    if metric.dimensions:
        dimensions = ", ".join([d.name for d in metric.dimensions])
        table.add_row("Dimensions", dimensions)
    
    console.print(table)


def _display_query_results(result) -> None:
    """Display query results in a table."""
    if not result.data:
        console.print("[yellow]No data returned[/yellow]")
        return
    
    # Create table with columns from first row
    first_row = result.data[0]
    table = Table(title=f"Query Results ({result.total_rows} rows)")
    
    for column in first_row.keys():
        table.add_column(column, style="white")
    
    # Add data rows (limit to first 50 for display)
    for row in result.data[:50]:
        table.add_row(*[str(v) for v in row.values()])
    
    console.print(table)
    
    if len(result.data) > 50:
        console.print(f"[yellow]Showing first 50 of {len(result.data)} rows[/yellow]")


def _display_metrics_list(metrics) -> None:
    """Display list of metrics in a table."""
    if not metrics:
        console.print("[yellow]No metrics found[/yellow]")
        return
    
    table = Table(title="Metrics")
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Type", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("Data Source", style="blue")
    
    for metric in metrics:
        table.add_row(
            str(metric.id),
            metric.name,
            metric.metric_type.value,
            metric.status.value,
            metric.data_source
        )
    
    console.print(table)


def main() -> None:
    """Main CLI entry point."""
    cli()


if __name__ == '__main__':
    main()