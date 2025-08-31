import logging
import logging.config
import sys
from pathlib import Path
from typing import Optional
import yaml

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green  
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

def setup_logging(
    config_path: Optional[str] = None,
    log_level: str = "INFO",
    log_dir: str = "logs"
) -> None:
    """Setup comprehensive logging configuration."""
    
    # Create log directory
    Path(log_dir).mkdir(exist_ok=True)
    
    if config_path and Path(config_path).exists():
        # Load from YAML config
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        logging.config.dictConfig(config)
    else:
        # Default configuration
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s | %(name)20s | %(levelname)8s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(f'{log_dir}/import.log'),
                logging.FileHandler(f'{log_dir}/error.log', level=logging.ERROR)
            ]
        )
    
    # Add colored formatter to console handler
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            handler.setFormatter(ColoredFormatter(
                '%(asctime)s | %(name)20s | %(levelname)8s | %(funcName)s:%(lineno)d | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))

def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    return logging.getLogger(name)