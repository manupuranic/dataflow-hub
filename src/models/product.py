from dataclasses import dataclass
from datetime import date
from typing import Optional, Dict, Any
from decimal import Decimal

@dataclass
class ProductModel:
    """Product data model with validation."""
    
    item_name_id: str
    brand_id: str
    barcode: Optional[str] = None
    hsn_code: Optional[str] = None
    size: Optional[str] = None
    expiry_date: Optional[date] = None
    gst_percent: int = 0
    cess_percent: Optional[int] = None
    purchase_price: float = 0.0
    mrp: float = 0.0
    rate: float = 0.0
    current_stock: int = 0
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not self.item_name_id:
            raise ValueError("item_name_id is required")
        if not self.brand_id:
            raise ValueError("brand_id is required")
        if self.mrp < 0:
            raise ValueError("MRP cannot be negative")
        if self.current_stock < 0:
            raise ValueError("Current stock cannot be negative")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insertion."""
        return {
            'item_name_id': self.item_name_id,
            'brand_id': self.brand_id,
            'barcode': self.barcode,
            'hsn_code': self.hsn_code,
            'size': self.size,
            'expiry_date': self.expiry_date,
            'gst_percent': self.gst_percent,
            'cess_percent': self.cess_percent,
            'purchase_price': self.purchase_price,
            'mrp': self.mrp,
            'rate': self.rate,
            'current_stock': self.current_stock
        }