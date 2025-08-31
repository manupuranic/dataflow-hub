import pandas as pd
import numpy as np
from datetime import datetime, date
from typing import Any, Optional, List
import re

class FieldNormalizer:
    """Utility class for normalizing various field types."""
    
    DATE_FORMATS = [
        "%d-%m-%Y", "%Y/%m/%d", "%Y-%m-%d", "%d/%m/%Y",
        "%m/%d/%Y", "%d.%m.%Y", "%Y.%m.%d"
    ]
    
    @staticmethod
    def normalize_string(val: Any) -> str:
        """Normalize string fields for consistency."""
        if pd.isna(val) or str(val).strip() in ["", "0", "nan", "null"]:
            return ""
        return str(val).strip()
    
    @staticmethod
    def normalize_barcode(val: Any) -> Optional[str]:
        """Normalize barcode with validation."""
        if pd.isna(val):
            return None
        
        barcode = str(val).strip()
        # Remove any non-alphanumeric characters except hyphens
        barcode = re.sub(r'[^a-zA-Z0-9\-]', '', barcode)
        
        return barcode if barcode else None
    
    @classmethod
    def parse_date(cls, val: Any, default_date: Optional[date] = None) -> Optional[date]:
        """Parse date with multiple format support."""
        if pd.isna(val):
            return default_date
            
        val_str = str(val).strip()
        
        for fmt in cls.DATE_FORMATS:
            try:
                return datetime.strptime(val_str, fmt).date()
            except (ValueError, TypeError):
                continue
        
        # Fallback to pandas flexible parsing
        try:
            parsed_date = pd.to_datetime(val_str, errors='coerce')
            return parsed_date.date() if not pd.isna(parsed_date) else default_date
        except Exception:
            return default_date
    
    @staticmethod
    def parse_numeric(val: Any, default: float = 0.0) -> float:
        """Parse numeric value with fallback."""
        try:
            if pd.isna(val):
                return default
            return float(val)
        except (ValueError, TypeError):
            return default
    
    @staticmethod
    def parse_integer(val: Any, default: int = 0) -> int:
        """Parse integer value with fallback."""
        try:
            if pd.isna(val):
                return default
            return int(float(val))  # Handle float strings
        except (ValueError, TypeError):
            return default