from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from src.core.data_processor import ProcessingStats
from src.utils.logger import get_logger

logger = get_logger(__name__)

def generate_import_report(
    stats: ProcessingStats, 
    output_path: str,
    additional_info: Dict[str, Any] = None
) -> None:
    """Generate detailed import report."""
    
    logger.info(f"📄 Generating import report: {output_path}")
    
    try:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write("DATAFLOW HUB - IMPORT PROCESSING REPORT\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duration: {stats.duration:.2f} seconds\n" if stats.duration else "Duration: N/A\n")
            f.write("\n")
            
            # Summary Statistics
            f.write("SUMMARY STATISTICS\n")
            f.write("-" * 30 + "\n")
            f.write(f"Total input records: {stats.total_input_records:,}\n")
            f.write(f"Total output records: {stats.total_output_records:,}\n")
            f.write(f"Successful records: {stats.successful_records:,}\n")
            f.write(f"Skipped records: {stats.skipped_records:,}\n")
            f.write(f"Error records: {stats.error_records:,}\n")
            f.write(f"Duplicate groups: {stats.duplicate_groups:,}\n")
            f.write(f"Success rate: {stats.success_rate:.2f}%\n")
            f.write("\n")
            
            # Performance Metrics
            f.write("PERFORMANCE METRICS\n")
            f.write("-" * 30 + "\n")
            if stats.duration:
                rps = stats.total_input_records / stats.duration
                f.write(f"Processing rate: {rps:.0f} records/second\n")
                f.write(f"Total processing time: {stats.duration:.2f} seconds\n")
            
            # Error Analysis
            if stats.error_records > 0 or stats.validation_errors > 0:
                f.write("\nERROR ANALYSIS\n")
                f.write("-" * 20 + "\n")
                f.write(f"Processing errors: {stats.error_records:,}\n")
                f.write(f"Validation errors: {stats.validation_errors:,}\n")
                f.write(f"Database errors: {stats.database_errors:,}\n")
            
            # Additional Information
            if additional_info:
                f.write("\nADDITIONAL INFORMATION\n")
                f.write("-" * 30 + "\n")
                for key, value in additional_info.items():
                    f.write(f"{key}: {value}\n")
        
        logger.info("✅ Report generated successfully")
        
    except Exception as e:
        logger.error(f"❌ Error generating report: {e}")