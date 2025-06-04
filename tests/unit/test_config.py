"""
Unit tests for configuration management.

Tests the configuration loading, validation, and management functionality.
"""

import pytest
import yaml
from pathlib import Path

from datametrics_agent.core.config import Config, DatabaseConfig, load_config
from datametrics_agent.core.exceptions import ConfigurationError


class TestDatabaseConfig:
    """Test DatabaseConfig model."""
    
    def test_valid_database_config(self):
        """Test creating a valid database configuration."""
        config = DatabaseConfig(
            type="mysql",
            host="localhost",
            port=3306,
            database="test_db",
            username="user",
            password="password"
        )
        
        assert config.type == "mysql"
        assert config.host == "localhost"
        assert config.port == 3306
        assert config.database == "test_db"
        assert config.username == "user"
        assert config.password == "password"
        assert config.pool_size == 10  # default
        assert config.max_overflow == 20  # default
    
    def test_invalid_database_type(self):
        """Test validation of database type."""
        with pytest.raises(ValueError, match="Unsupported database type"):
            DatabaseConfig(
                type="invalid_db",
                host="localhost",
                port=3306,
                database="test_db",
                username="user",
                password="password"
            )
    
    def test_database_type_case_insensitive(self):
        """Test that database type validation is case insensitive."""
        config = DatabaseConfig(
            type="MYSQL",
            host="localhost",
            port=3306,
            database="test_db",
            username="user",
            password="password"
        )
        
        assert config.type == "mysql"


class TestConfig:
    """Test main Config class."""
    
    def test_default_config(self):
        """Test creating a default configuration."""
        config = Config()
        
        assert config.app.name == "DataMetrics Agent"
        assert config.app.version == "0.1.0"
        assert config.app.debug is False
        assert config.app.host == "0.0.0.0"
        assert config.app.port == 8000
    
    def test_config_from_yaml(self, temp_config_file: Path):
        """Test loading configuration from YAML file."""
        config = Config.from_yaml(temp_config_file)
        
        assert config.app.debug is True
        assert config.app.log_level == "DEBUG"
    
    def test_config_from_nonexistent_file(self):
        """Test loading configuration from non-existent file."""
        with pytest.raises(ConfigurationError, match="Configuration file not found"):
            Config.from_yaml("nonexistent.yaml")
    
    def test_config_from_invalid_yaml(self, tmp_path: Path):
        """Test loading configuration from invalid YAML file."""
        invalid_file = tmp_path / "invalid.yaml"
        invalid_file.write_text("invalid: yaml: content: [")
        
        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            Config.from_yaml(invalid_file)
    
    def test_config_from_empty_file(self, tmp_path: Path):
        """Test loading configuration from empty file."""
        empty_file = tmp_path / "empty.yaml"
        empty_file.write_text("")
        
        with pytest.raises(ConfigurationError, match="Configuration file is empty"):
            Config.from_yaml(empty_file)
    
    def test_get_database_config(self, test_config: Config):
        """Test getting database configuration."""
        db_config = test_config.get_database_config("metadata")
        
        assert isinstance(db_config, DatabaseConfig)
        assert db_config.type == "sqlite"
        assert db_config.database == ":memory:"
    
    def test_get_nonexistent_database_config(self, test_config: Config):
        """Test getting non-existent database configuration."""
        with pytest.raises(ConfigurationError, match="Database configuration 'nonexistent' not found"):
            test_config.get_database_config("nonexistent")
    
    def test_get_data_source_config(self, test_config: Config):
        """Test getting data source configuration."""
        source_config = test_config.get_data_source_config("test_mysql")
        
        assert isinstance(source_config, DatabaseConfig)
        assert source_config.type == "mysql"
        assert source_config.database == "test_db"
    
    def test_get_nonexistent_data_source_config(self, test_config: Config):
        """Test getting non-existent data source configuration."""
        with pytest.raises(ConfigurationError, match="Data source 'nonexistent' not found"):
            test_config.get_data_source_config("nonexistent")
    
    def test_is_feature_enabled(self, test_config: Config):
        """Test checking if features are enabled."""
        assert test_config.is_feature_enabled("sql_optimization") is True
        assert test_config.is_feature_enabled("nlp_processing") is False
        assert test_config.is_feature_enabled("nonexistent_feature") is False
    
    def test_get_template_path(self, test_config: Config):
        """Test getting template path."""
        template_path = test_config.get_template_path()
        
        assert isinstance(template_path, Path)
        assert str(template_path) == "config/templates"
    
    def test_validate_config(self, test_config: Config):
        """Test configuration validation."""
        issues = test_config.validate_config()
        
        # Should have issue about secret key
        assert any("secret key" in issue.lower() for issue in issues)
    
    def test_validate_config_missing_metadata_db(self):
        """Test validation with missing metadata database."""
        config = Config()
        config.databases = {}  # No metadata database
        
        issues = config.validate_config()
        
        assert any("metadata database" in issue.lower() for issue in issues)


class TestLoadConfig:
    """Test load_config function."""
    
    def test_load_config_with_file(self, temp_config_file: Path):
        """Test loading configuration with file path."""
        config = load_config(temp_config_file)
        
        assert config.app.debug is True
        assert config.app.log_level == "DEBUG"
    
    def test_load_config_without_file(self):
        """Test loading configuration without file path."""
        config = load_config()
        
        # Should return default configuration
        assert config.app.name == "DataMetrics Agent"
        assert config.app.debug is False