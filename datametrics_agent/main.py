"""
Main entry point for DataMetrics Agent.

This module provides the main entry point for running the DataMetrics Agent
as a web service or standalone application.
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from datametrics_agent import MetricsAgent
from datametrics_agent.core.config import load_config
from datametrics_agent.core.exceptions import DataMetricsError
from datametrics_agent.core.logging import get_logger, setup_logging


# Global agent instance
agent: Optional[MetricsAgent] = None
logger = get_logger(__name__)


def create_app(config_path: Optional[Path] = None) -> FastAPI:
    """
    Create FastAPI application.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        FastAPI: Configured FastAPI application
    """
    global agent
    
    # Load configuration
    config = load_config(config_path)
    
    # Setup logging
    setup_logging(config.logging)
    
    # Initialize agent
    agent = MetricsAgent(config=config)
    
    # Create FastAPI app
    app = FastAPI(
        title="DataMetrics Agent API",
        description="Intelligent data metrics development assistant",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add routes
    _add_routes(app)
    
    # Add startup and shutdown events
    @app.on_event("startup")
    async def startup_event():
        logger.info("DataMetrics Agent API starting up")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        logger.info("DataMetrics Agent API shutting down")
        if agent:
            agent.close()
    
    return app


def _add_routes(app: FastAPI) -> None:
    """Add API routes to the FastAPI application."""
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "DataMetrics Agent API",
            "version": "0.1.0",
            "status": "running"
        }
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}
    
    @app.post("/metrics")
    async def create_metric(request: dict):
        """Create a new metric."""
        try:
            if not agent:
                raise HTTPException(status_code=500, detail="Agent not initialized")
            
            description = request.get("description")
            if not description:
                raise HTTPException(status_code=400, detail="Description is required")
            
            metric = agent.create_metric(
                description=description,
                data_source=request.get("data_source"),
                dimensions=request.get("dimensions", [])
            )
            
            return metric.dict()
            
        except DataMetricsError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error creating metric: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.get("/metrics")
    async def list_metrics(
        status: Optional[str] = None,
        owner: Optional[str] = None,
        limit: int = 20
    ):
        """List metrics with optional filtering."""
        try:
            if not agent:
                raise HTTPException(status_code=500, detail="Agent not initialized")
            
            filters = {}
            if status:
                filters["status"] = status
            if owner:
                filters["owner"] = owner
            
            metrics = agent.list_metrics(filters=filters, limit=limit)
            return [metric.dict() for metric in metrics]
            
        except DataMetricsError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error listing metrics: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.get("/metrics/{metric_id}")
    async def get_metric(metric_id: str):
        """Get a specific metric."""
        try:
            if not agent:
                raise HTTPException(status_code=500, detail="Agent not initialized")
            
            metric = agent.get_metric(metric_id)
            if not metric:
                raise HTTPException(status_code=404, detail="Metric not found")
            
            return metric.dict()
            
        except DataMetricsError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error getting metric: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.post("/metrics/{metric_id}/query")
    async def query_metric(metric_id: str, request: dict):
        """Query a metric."""
        try:
            if not agent:
                raise HTTPException(status_code=500, detail="Agent not initialized")
            
            metric = agent.get_metric(metric_id)
            if not metric:
                raise HTTPException(status_code=404, detail="Metric not found")
            
            # Build query request
            from datametrics_agent.core.models import QueryRequest
            from datetime import datetime
            
            query_request = QueryRequest(metric_id=metric_id)
            
            if request.get("start_date"):
                query_request.start_date = datetime.fromisoformat(request["start_date"])
            if request.get("end_date"):
                query_request.end_date = datetime.fromisoformat(request["end_date"])
            if request.get("limit"):
                query_request.limit = request["limit"]
            if request.get("dimension_filters"):
                query_request.dimension_filters = request["dimension_filters"]
            
            result = agent.execute_metric(metric, query_request)
            return result.dict()
            
        except DataMetricsError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error querying metric: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.post("/data-sources/{data_source}/test")
    async def test_data_source(data_source: str):
        """Test connection to a data source."""
        try:
            if not agent:
                raise HTTPException(status_code=500, detail="Agent not initialized")
            
            success = agent.test_connection(data_source)
            return {"success": success}
            
        except DataMetricsError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Error testing data source: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


def run_server(
    host: str = "0.0.0.0",
    port: int = 8000,
    config_path: Optional[Path] = None,
    reload: bool = False
) -> None:
    """
    Run the DataMetrics Agent web server.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        config_path: Path to configuration file
        reload: Enable auto-reload for development
    """
    app = create_app(config_path)
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


def run_cli() -> None:
    """Run the CLI interface."""
    from datametrics_agent.cli import main
    main()


def main() -> None:
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="DataMetrics Agent")
    parser.add_argument(
        "--mode", 
        choices=["server", "cli"], 
        default="server",
        help="Run mode (default: server)"
    )
    parser.add_argument(
        "--config", 
        "-c", 
        type=Path,
        help="Configuration file path"
    )
    parser.add_argument(
        "--host", 
        default="0.0.0.0",
        help="Host to bind to (server mode only)"
    )
    parser.add_argument(
        "--port", 
        type=int, 
        default=8000,
        help="Port to bind to (server mode only)"
    )
    parser.add_argument(
        "--reload", 
        action="store_true",
        help="Enable auto-reload (development mode)"
    )
    
    args = parser.parse_args()
    
    if args.mode == "server":
        run_server(
            host=args.host,
            port=args.port,
            config_path=args.config,
            reload=args.reload
        )
    elif args.mode == "cli":
        run_cli()


if __name__ == "__main__":
    main()