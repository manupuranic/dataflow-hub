from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import pandas as pd
from datetime import date
from core.base_importer import BaseImporter
from core.data_processor import FieldMergeMode, ProcessingStats
from models.product import ProductModel
from utils.field_normalizer import FieldNormalizer
from core.exceptions import DataValidationError

class ProductImporter(BaseImporter):
    """
    Specialized importer for product data.
    
    Handles:
    - Product and inventory data merging
    - Brand and item name normalization
    - GST/Cess parsing
    - Stock calculation
    """
    
    def __init__(self, db_connection, config: Dict[str, Any] = None):
        super().__init__(db_connection, config)
        
        # Product-specific configuration
        self.merge_keys = ['Barcode', 'Item Name', 'Brand', 'MRP', 'Expiry Date']
        self.default_expiry = date(9999, 12, 31)
        
        # Cache for database lookups
        self._item_name_cache = {}
        self._brand_cache = {}
    
    def get_table_name(self) -> str:
        return "products"
    
    def get_conflict_columns(self) -> List[str]:
        return ['item_name_id', 'brand_id', 'mrp', 'barcode', 'expiry_date']
    
    def get_required_columns(self) -> List[str]:
        return ['Item Name', 'Brand', 'MRP', 'Expiry Date', 'Barcode', 'Rate']

    def get_merge_rules(self) -> Dict[str, FieldMergeMode]:
        return {
            'current_stock': FieldMergeMode.LAST,
            'purchase_price': FieldMergeMode.LAST,
            'rate': FieldMergeMode.LAST,
            'gst_percent': FieldMergeMode.LAST,
            'cess_percent': FieldMergeMode.LAST
        }
    
    def validate_input_data(self, df: pd.DataFrame) -> bool:
        """Validate product data structure."""
        required_cols = self.get_required_columns()
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            self.logger.error(f"Missing required columns: {missing_cols}")
            return False
        
        # Check for empty dataframe
        if df.empty:
            self.logger.error("Input dataframe is empty")
            return False
        
        # Validate critical fields
        null_item_names = df['Item Name'].isna().sum()
        if null_item_names > 0:
            self.logger.warning(f"Found {null_item_names} records with null item names")
        
        deleted_items = df[df['Item Name'] == 'Deleted Item'].shape[0]
        if deleted_items > 0:
            self.logger.info(f"Found {deleted_items} deleted items (will be skipped)")
        
        self.logger.info("Input data validation passed")
        return True
    
    def preprocess_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Product-specific preprocessing."""
        self.logger.info("Applying product-specific preprocessing")
        
        # Apply field normalization
        df = self.processor.normalize_dataframe(df)
        
        # Only calculate current_stock if not already present
        if 'current_stock' in df.columns:
            self.logger.info("'current_stock' already present, skipping recalculation")
            return df
    
        # Calculate current stock if inventory data is merged
        if 'Net Qty' in df.columns:
            df['current_stock'] = df['Net Qty'].fillna(0)
            self.logger.info("Using 'Net Qty' for current stock")
        elif all(col in df.columns for col in ['Qty - Puranic Health Mart-PHM', 'Qty - WAREHOUSE-1-WH']):
            df['current_stock'] = (
                pd.to_numeric(df['Qty - Puranic Health Mart-PHM'], errors='coerce').fillna(0) +
                pd.to_numeric(df['Qty - WAREHOUSE-1-WH'], errors='coerce').fillna(0)
            )
            self.logger.info("Calculated current stock from PHM + Warehouse quantities")
        else:
            df['current_stock'] = 0
            self.logger.warning("No quantity fields found, setting current_stock to 0")
    
        return df
    
    def get_or_create_item_name(self, item_name_raw: str) -> Optional[str]:
        """Get or create item name with caching."""
        if not item_name_raw or item_name_raw == 'Deleted Item':
            return None
        
        # Import your existing clean_item_name function
        from utils.helpers import clean_item_name
        cleaned_name = clean_item_name(item_name_raw)
        
        # Check cache first
        if cleaned_name in self._item_name_cache:
            return self._item_name_cache[cleaned_name]
        
        try:
            # Try to find existing record
            item_name_obj = self.db.listOne(
                'item_names', 
                {"filters": [{'field': 'original_name', 'value': cleaned_name}]}
            )
            
            if not item_name_obj:
                # Create new record
                self.db.upsertRecord(
                    'item_names', 
                    {'original_name': cleaned_name}, 
                    conflict_columns=['original_name']
                )
                item_name_obj = self.db.listOne(
                    'item_names', 
                    {"filters": [{'field': 'original_name', 'value': cleaned_name}]}
                )
                self.logger.debug(f"Created new item name: {cleaned_name}")
            
            item_id = item_name_obj.id if item_name_obj else None
            self._item_name_cache[cleaned_name] = item_id
            return item_id
            
        except Exception as e:
            self.logger.error(f"Error processing item name '{item_name_raw}': {e}")
            return None
    
    def get_or_create_brand(self, brand_name: str) -> Optional[str]:
        """Get or create brand with caching."""
        brand_name = brand_name or 'NA'
        
        # if brand_name is not a string, then make it 'NA'
        if not isinstance(brand_name, str):
            brand_name = 'NA'
        
        # Check cache first
        if brand_name in self._brand_cache:
            return self._brand_cache[brand_name]
        
        try:
            brand_obj = self.db.listOne(
                'brands', 
                {"filters": [{'field': 'name', 'value': brand_name}]}
            )
            
            if not brand_obj:
                self.db.upsertRecord(
                    'brands', 
                    {'name': brand_name}, 
                    conflict_columns=['name']
                )
                brand_obj = self.db.listOne(
                    'brands', 
                    {"filters": [{'field': 'name', 'value': brand_name}]}
                )
                self.logger.debug(f"Created new brand: {brand_name}")
            
            brand_id = brand_obj.id if brand_obj else None
            self._brand_cache[brand_name] = brand_id
            return brand_id
            
        except Exception as e:
            self.logger.error(f"Error processing brand '{brand_name}': {e}")
            return None
    
    def parse_gst_and_cess(self, gst_raw: Any) -> Tuple[int, Optional[int]]:
        """Parse GST percentage and cess from tax category string."""
        if not gst_raw or pd.isna(gst_raw):
            return 0, None
            
        gst_str = str(gst_raw).strip()
        
        try:
            if '(' in gst_str and ')' in gst_str:
                # Extract content between parentheses: "GST 18% (18+0)"
                inside = gst_str.split('(')[1].split(')')[0]
                parts = inside.split('+')
                
                gst_percent = int(parts[0].strip()) if parts[0].strip() else 0
                cess_percent = int(parts[1].strip()) if len(parts) > 1 and parts[1].strip() else None
                
                return gst_percent, cess_percent
            else:
                # Try direct numeric parsing
                gst_percent = int(float(gst_str))
                return gst_percent, None
                
        except (ValueError, IndexError) as e:
            self.logger.warning(f"Cannot parse GST '{gst_str}': {e}")
            return 0, None
    
    def process_row(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """Process a single product row."""
        try:
            # Get or create item name
            item_name_id = self.get_or_create_item_name(row.get('Item Name'))
            if not item_name_id:
                return None
            
            # Get or create brand
            brand_id = self.get_or_create_brand(row.get('Brand'))
            if not brand_id:
                return None
            
            # Parse GST and Cess
            gst_percent, cess_percent = self.parse_gst_and_cess(row.get('Tax Category'))
            
            # Parse expiry date
            expiry_date = FieldNormalizer.parse_date(
                row.get('Expiry Date'), 
                default_date=self.default_expiry
            )
            
            # Parse numeric fields
            purchase_price = FieldNormalizer.parse_numeric(row.get('Purchase Price', 0))
            mrp = FieldNormalizer.parse_numeric(row.get('MRP', 0))
            rate = FieldNormalizer.parse_numeric(row.get('Rate', 0))
            current_stock = FieldNormalizer.parse_integer(row.get('current_stock', 0))
            
            # Create and validate product model
            product = ProductModel(
                item_name_id=item_name_id,
                brand_id=brand_id,
                barcode=FieldNormalizer.normalize_barcode(row.get('Barcode')),
                hsn_code=row.get('HsnCode') or row.get('HSN Code'),
                size=row.get('Size'),
                expiry_date=expiry_date,
                gst_percent=gst_percent,
                cess_percent=cess_percent,
                purchase_price=purchase_price,
                mrp=mrp,
                rate=rate,
                current_stock=current_stock
            )
            
            return product.to_dict()
            
        except Exception as e:
            self.logger.warning(f"Error processing product row: {e}")
            return None
    
    def merge_with_inventory(
        self, 
        product_path: str, 
        inventory_path: str
    ) -> pd.DataFrame:
        """Merge product data with inventory data."""
        self.logger.info("Starting product-inventory merge")
        
        # Load both datasets
        product_df = self.load_and_validate_file(product_path)
        inventory_df = self.load_and_validate_file(inventory_path)
        
        # Normalize both datasets
        product_df = self.processor.normalize_dataframe(product_df)
        inventory_df = self.processor.normalize_dataframe(inventory_df)
        
        # Calculate current stock in inventory
        inventory_df = self.preprocess_dataframe(inventory_df)
        
        # Perform merge
        self.logger.info(f"Merging on keys: {self.merge_keys}")
        merged_df = product_df.merge(
            inventory_df[self.merge_keys + ['current_stock']],
            on=self.merge_keys,
            how='left',
            indicator=True
        )
        
        # Log merge statistics
        merge_stats = merged_df['_merge'].value_counts()
        for merge_type, count in merge_stats.items():
            self.logger.info(f"{merge_type}: {count:,} records")
        
        # Fill missing stock
        merged_df['current_stock'] = merged_df['current_stock'].fillna(0).astype(int)
        merged_df = merged_df.drop('_merge', axis=1)
        
        self.logger.info(f"Merge completed: {len(merged_df):,} records")
        return merged_df
    
    def run_product_import(
        self,
        product_path: str,
        inventory_path: Optional[str] = None,
        chunk_size: Optional[int] = None,
        offset: int = 0
    ) -> ProcessingStats:
        """
        Run complete product import process with optional inventory merge.
        
        Args:
            product_path: Path to product data file
            inventory_path: Optional path to inventory data file
            chunk_size: Processing batch size
            offset: Records to skip from beginning
            
        Returns:
            Processing statistics
        """
        self.logger.info("Starting comprehensive product import")
        
        try:
            if inventory_path:
                # Merge product and inventory data first
                merged_df = self.merge_with_inventory(product_path, inventory_path)
                
                # Save merged data temporarily for processing
                temp_path = "temp_merged_products.csv"
                merged_df.to_csv(temp_path, index=False)
                
                # Run import on merged data
                stats = self.run_import(temp_path, chunk_size, offset)
                
                # Cleanup temp file
                Path(temp_path).unlink(missing_ok=True)
                
            else:
                # Direct product import
                stats = self.run_import(product_path, chunk_size, offset)
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Product import failed: {e}")
            raise
