#!/usr/bin/env python3
"""
DataFlow Hub - Main Orchestrator Script
Enterprise Data Integration Platform
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.logger import setup_logging, get_logger
from src.config.settings import load_config
from src.core.data_processor import ProcessingStats
from src.importers.product_importer import ProductImporter
# from src.importers.invoice_importer import InvoiceImporter
# from src.importers.purchase_importer import PurchaseImporter
from db.core import DB

logger = get_logger(__name__)

class DataFlowOrchestrator:
    """Main orchestrator for all import operations."""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        """Initialize orchestrator with configuration."""
        self.config = load_config(config_path)
        self.db = DB(self.config.database.__dict__)  # Assuming your DB class accepts dict
        
        # Initialize importers
        self.importers = {
            'products': ProductImporter(self.db, self.config.importer.__dict__),
            # 'invoices': InvoiceImporter(self.db, self.config.importer.__dict__),
            # 'purchases': PurchaseImporter(self.db, self.config.importer.__dict__),
        }
        
        logger.info("🎯 DataFlow Hub Orchestrator initialized")
    
    def run_single_import(
        self, 
        import_type: str, 
        file_path: str,
        **kwargs
    ) -> ProcessingStats:
        """Run a single import operation."""
        
        if import_type not in self.importers:
            raise ValueError(f"Unknown import type: {import_type}")
        
        importer = self.importers[import_type]
        logger.info(f"🚀 Starting {import_type} import from {file_path}")
        
        try:
            if import_type == 'products' and 'inventory_path' in kwargs:
                # Special handling for product imports with inventory
                stats = importer.run_product_import(
                    file_path, 
                    kwargs.get('inventory_path'),
                    kwargs.get('chunk_size'),
                    kwargs.get('offset', 0)
                )
            else:
                stats = importer.run_import(
                    file_path,
                    kwargs.get('chunk_size'),
                    kwargs.get('offset', 0)
                )
            
            logger.info(f"✅ {import_type} import completed successfully")
            return stats
            
        except Exception as e:
            logger.error(f"💥 {import_type} import failed: {e}")
            raise
    
    def run_all_imports(self, input_dir: str = "data/input") -> Dict[str, ProcessingStats]:
        """Run all available imports in sequence."""
        logger.info("🚀 Starting complete data import sequence")
        
        # Define import sequence and file mappings
        import_sequence = [
            ('products', 'products.xlsx', {'inventory_path': 'inventory.csv'}),
            # ('invoices', 'invoices.xlsx', {}),
            # ('purchases', 'purchases.csv', {}),
        ]
        
        results = {}
        
        for import_type, filename, extra_kwargs in import_sequence:
            file_path = Path(input_dir) / filename
            
            if not file_path.exists():
                logger.warning(f"⚠️  Skipping {import_type}: file not found {file_path}")
                continue
            
            try:
                # Add inventory path if it's a products import
                if 'inventory_path' in extra_kwargs:
                    inventory_file = Path(input_dir) / extra_kwargs['inventory_path']
                    if inventory_file.exists():
                        extra_kwargs['inventory_path'] = str(inventory_file)
                    else:
                        extra_kwargs.pop('inventory_path')
                        logger.warning("⚠️  Inventory file not found, proceeding without merge")
                
                stats = self.run_single_import(import_type, str(file_path), **extra_kwargs)
                results[import_type] = stats
                
            except Exception as e:
                logger.error(f"❌ Failed to import {import_type}: {e}")
                # Continue with other imports
                continue
        
        # Log overall summary
        self._log_overall_summary(results)
        return results
    
    def _log_overall_summary(self, results: Dict[str, ProcessingStats]):
        """Log summary of all import operations."""
        logger.info("\n" + "=" * 80)
        logger.info("🎯 OVERALL IMPORT SUMMARY")
        logger.info("=" * 80)
        
        total_records = sum(stats.successful_records for stats in results.values())
        total_errors = sum(stats.error_records for stats in results.values())
        
        for import_type, stats in results.items():
            logger.info(f"📊 {import_type.upper()}: "
                       f"{stats.successful_records:,} success, "
                       f"{stats.error_records:,} errors, "
                       f"{stats.success_rate:.1f}% rate")
        
        logger.info(f"\n🎯 TOTALS: {total_records:,} successful, {total_errors:,} errors")
        logger.info("=" * 80)

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DataFlow Hub - Enterprise Data Integration Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/main.py --type products --file data/input/products.xlsx
  python scripts/main.py --type products --file data/products.xlsx --inventory data/inventory.csv
  python scripts/main.py --type all
  python scripts/main.py --type invoices --chunk-size 1000 --offset 5000
        """
    )
    
    parser.add_argument(
        "--type", 
        choices=["products", "invoices", "purchases", "suppliers", "all"],
        required=True,
        help="Type of data to import"
    )
    
    parser.add_argument(
        "--file",
        help="Path to input file (required for single imports)"
    )
    
    parser.add_argument(
        "--inventory",
        help="Path to inventory file (for product imports)"
    )
    
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--chunk-size",
        type=int,
        help="Override default chunk size"
    )
    
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Number of records to skip from beginning"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    
    parser.add_argument(
        "--input-dir",
        default="data/input",
        help="Input directory for batch imports"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(log_level=args.log_level)
    logger.info(f"🎯 DataFlow Hub starting at {datetime.now()}")
    
    try:
        orchestrator = DataFlowOrchestrator(args.config)
        
        if args.type == "all":
            # Run all imports
            results = orchestrator.run_all_imports(args.input_dir)
            
        else:
            # Run single import
            if not args.file:
                logger.error("❌ --file argument required for single imports")
                sys.exit(1)
            
            kwargs = {
                'chunk_size': args.chunk_size,
                'offset': args.offset
            }
            
            if args.inventory:
                kwargs['inventory_path'] = args.inventory
            
            stats = orchestrator.run_single_import(args.type, args.file, **kwargs)
            
            # Generate report
            from src.utils.report_generator import generate_import_report
            generate_import_report(stats, f"logs/{args.type}_import_report.txt")
        
        logger.info("🎉 DataFlow Hub execution completed successfully!")
        
    except Exception as e:
        logger.error(f"💥 Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()