"""
Configuration management for DataMetrics Agent.

This module handles loading, validation, and management of application configuration
from YAML files, environment variables, and other sources.
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings

from datametrics_agent.core.exceptions import ConfigurationError


class DatabaseConfig(BaseModel):
    """Database connection configuration."""
    
    type: str = Field(..., description="Database type (mysql, postgresql, clickhouse, etc.)")
    host: str = Field(..., description="Database host")
    port: int = Field(..., description="Database port")
    database: str = Field(..., description="Database name")
    username: str = Field(..., description="Database username")
    password: str = Field(..., description="Database password")
    pool_size: int = Field(default=10, description="Connection pool size")
    max_overflow: int = Field(default=20, description="Maximum pool overflow")
    
    @validator('type')
    def validate_db_type(cls, v: str) -> str:
        """Validate database type."""
        supported_types = ['mysql', 'postgresql', 'clickhouse', 'sqlite', 'mongodb']
        if v.lower() not in supported_types:
            raise ValueError(f"Unsupported database type: {v}. Supported: {supported_types}")
        return v.lower()


class AIConfig(BaseModel):
    """AI service configuration."""
    
    openai: Dict[str, Any] = Field(default_factory=dict)
    local_models: Dict[str, Any] = Field(default_factory=dict)


class MonitoringConfig(BaseModel):
    """Monitoring and alerting configuration."""
    
    enabled: bool = Field(default=True)
    prometheus: Dict[str, Any] = Field(default_factory=dict)
    alerts: Dict[str, Any] = Field(default_factory=dict)


class CacheConfig(BaseModel):
    """Cache configuration."""
    
    type: str = Field(default="memory", description="Cache type (redis, memory, disabled)")
    redis: Dict[str, Any] = Field(default_factory=dict)
    ttl: int = Field(default=3600, description="Default TTL in seconds")


class SecurityConfig(BaseModel):
    """Security configuration."""
    
    secret_key: str = Field(..., description="Secret key for JWT tokens")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    rate_limit: Dict[str, Any] = Field(default_factory=dict)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = Field(default="INFO")
    format: str = Field(default="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}")
    rotation: str = Field(default="1 day")
    retention: str = Field(default="30 days")
    compression: str = Field(default="gz")
    file: Dict[str, Any] = Field(default_factory=dict)
    console: Dict[str, Any] = Field(default_factory=dict)


class AppConfig(BaseModel):
    """Application configuration."""
    
    name: str = Field(default="DataMetrics Agent")
    version: str = Field(default="0.1.0")
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)


class Config(BaseSettings):
    """Main configuration class."""
    
    app: AppConfig = Field(default_factory=AppConfig)
    databases: Dict[str, Union[DatabaseConfig, Dict[str, DatabaseConfig]]] = Field(default_factory=dict)
    ai: AIConfig = Field(default_factory=AIConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    security: SecurityConfig = Field(default_factory=lambda: SecurityConfig(secret_key="change-this-secret-key"))
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    features: Dict[str, bool] = Field(default_factory=dict)
    templates: Dict[str, Any] = Field(default_factory=dict)
    development: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
    @classmethod
    def from_yaml(cls, config_path: Union[str, Path]) -> "Config":
        """Load configuration from YAML file."""
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                
            if not config_data:
                raise ConfigurationError("Configuration file is empty")
                
            return cls.parse_obj(config_data)
            
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in configuration file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration: {e}")
    
    def get_database_config(self, name: str) -> DatabaseConfig:
        """Get database configuration by name."""
        if name not in self.databases:
            raise ConfigurationError(f"Database configuration '{name}' not found")
            
        db_config = self.databases[name]
        if isinstance(db_config, dict):
            return DatabaseConfig.parse_obj(db_config)
        return db_config
    
    def get_data_source_config(self, name: str) -> DatabaseConfig:
        """Get data source configuration by name."""
        sources = self.databases.get('sources', {})
        if name not in sources:
            raise ConfigurationError(f"Data source '{name}' not found")
            
        source_config = sources[name]
        if isinstance(source_config, dict):
            return DatabaseConfig.parse_obj(source_config)
        return source_config
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled."""
        return self.features.get(feature_name, False)
    
    def get_template_path(self) -> Path:
        """Get template directory path."""
        template_path = self.templates.get('path', 'config/templates')
        return Path(template_path)
    
    def validate_config(self) -> List[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        # Check required database configurations
        if 'metadata' not in self.databases:
            issues.append("Metadata database configuration is required")
            
        # Check security settings
        if self.security.secret_key == "change-this-secret-key":
            issues.append("Security secret key should be changed from default")
            
        # Check AI configuration if NLP features are enabled
        if self.is_feature_enabled('nlp_processing'):
            if not self.ai.openai and not self.ai.local_models.get('enabled', False):
                issues.append("AI configuration required when NLP processing is enabled")
                
        return issues


def load_config(config_path: Optional[Union[str, Path]] = None) -> Config:
    """Load configuration from file or environment."""
    if config_path is None:
        # Try to find config file in common locations
        possible_paths = [
            Path("config/config.yaml"),
            Path("config.yaml"),
            Path("datametrics_config.yaml"),
        ]
        
        for path in possible_paths:
            if path.exists():
                config_path = path
                break
        else:
            # No config file found, use environment variables only
            return Config()
    
    return Config.from_yaml(config_path)