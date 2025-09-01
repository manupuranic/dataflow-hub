from dataclasses import dataclass, field
from typing import Dict, Any, List
import yaml
from pathlib import Path

from config.database import DATABASE_CONFIG  # Import database config

@dataclass
class ImporterConfig:
    """Configuration for individual importers."""
    chunk_size: int = 500
    max_retries: int = 3
    timeout_seconds: int = 300
    enable_validation: bool = True
    enable_caching: bool = True
    log_level: str = "INFO"

@dataclass
class FilePathConfig:
    """File path configuration."""
    input_dir: str = "data/input"
    output_dir: str = "data/output"
    log_dir: str = "logs"
    archive_dir: str = "data/archive"

@dataclass
class FieldMappingConfig:
    """Field mapping configuration for different data sources."""
    products: Dict[str, str] = field(default_factory=dict)
    invoices: Dict[str, str] = field(default_factory=dict)
    purchases: Dict[str, str] = field(default_factory=dict)
    suppliers: Dict[str, str] = field(default_factory=dict)

@dataclass
class ApplicationConfig:
    """Main application configuration."""
    importer: ImporterConfig = field(default_factory=ImporterConfig)
    file_paths: FilePathConfig = field(default_factory=FilePathConfig)
    field_mappings: FieldMappingConfig = field(default_factory=FieldMappingConfig)
    database: Dict[str, Any] = field(default_factory=dict)  # Add database as dict

def load_config(config_path: str = "config/settings.yaml") -> ApplicationConfig:
    """Load configuration from YAML file and database.py."""
    if not Path(config_path).exists():
        # Return default configuration with database from database.py
        config = ApplicationConfig()
        config.database = DATABASE_CONFIG
        return config

    with open(config_path, 'r') as f:
        config_data = yaml.safe_load(f)

    # Remove any database section if present
    config_data.pop('database', None)

    # Convert to dataclass
    config = ApplicationConfig(**config_data)
    config.database = DATABASE_CONFIG  # Attach database config from database.py
    return config