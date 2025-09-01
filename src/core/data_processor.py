from datetime import datetime
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
import math
import copy
from utils.logger import get_logger
from utils.field_normalizer import FieldNormalizer

logger = get_logger(__name__)

class MergeStrategy(Enum):
    FIRST = "first"
    LAST = "last"
    KEEP_MAX = "keep_max"
    MERGE = "merge"

class FieldMergeMode(Enum):
    SUM = "sum"
    MAX = "max"
    MIN = "min"
    AVG = "avg"
    FIRST = "first"
    LAST = "last"
    CONCAT = "concat"

@dataclass
class ProcessingStats:
    """Track comprehensive processing statistics."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_input_records: int = 0
    total_output_records: int = 0
    successful_records: int = 0
    skipped_records: int = 0
    error_records: int = 0
    duplicate_groups: int = 0
    validation_errors: int = 0
    database_errors: int = 0
    
    def __post_init__(self):
        if self.start_time is None:
            self.start_time = datetime.now()
    
    def finish(self):
        """Mark processing as finished."""
        self.end_time = datetime.now()
    
    @property
    def duration(self) -> Optional[float]:
        """Get processing duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_input_records == 0:
            return 0.0
        return (self.successful_records / self.total_input_records) * 100
    
    def log_summary(self):
        """Log comprehensive processing summary."""
        logger.info("=" * 60)
        logger.info("PROCESSING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Duration: {self.duration:.2f}s" if self.duration else "Duration: N/A")
        logger.info(f"Input records: {self.total_input_records:,}")
        logger.info(f"Output records: {self.total_output_records:,}")
        logger.info(f"Successful: {self.successful_records:,}")
        logger.info(f"Skipped: {self.skipped_records:,}")
        logger.info(f"Errors: {self.error_records:,}")
        logger.info(f"Duplicate groups: {self.duplicate_groups:,}")
        logger.info(f"Success rate: {self.success_rate:.2f}%")

        if self.validation_errors > 0:
            logger.warning(f"Validation errors: {self.validation_errors:,}")
        if self.database_errors > 0:
            logger.error(f"Database errors: {self.database_errors:,}")

        logger.info("=" * 60)

class DataProcessor:
    """Core data processing utilities."""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        self.normalizer = FieldNormalizer()
    
    def normalize_dataframe(
        self, 
        df: pd.DataFrame, 
        column_mappings: Dict[str, str] = None
    ) -> pd.DataFrame:
        """Normalize dataframe with optional column mapping."""
        self.logger.info(f"Normalizing dataframe with {len(df):,} records")
        
        # Apply column mappings if provided
        if column_mappings:
            df = df.rename(columns=column_mappings)
            self.logger.debug(f"Applied column mappings: {column_mappings}")
        
        # Normalize common fields
        normalization_rules = {
            'Barcode': lambda x: self.normalizer.normalize_barcode(x),
            'MRP': lambda x: self.normalizer.parse_numeric(x),
            'Item Name': lambda x: self.normalizer.normalize_string(x),
            'Brand': lambda x: self.normalizer.normalize_string(x),
            'Expiry Date': lambda x: self.normalizer.parse_date(x)
        }
        
        for column, normalizer_func in normalization_rules.items():
            if column in df.columns:
                df[column] = df[column].apply(normalizer_func)
                self.logger.debug(f"Normalized column: {column}")
        
        return df
    
    def deduplicate_records(
        self,
        records: List[Dict[str, Any]],
        conflict_columns: List[str],
        strategy: MergeStrategy = MergeStrategy.LAST,
        merge_rules: Optional[Dict[str, FieldMergeMode]] = None
    ) -> Tuple[List[Dict[str, Any]], Dict[tuple, List[Tuple[int, Dict[str, Any]]]]]:
        """Advanced deduplication with multiple strategies."""
        
        self.logger.info(f"Starting deduplication: {len(records):,} records, strategy: {strategy.value}")
        
        # Group records by conflict columns
        groups = defaultdict(list)
        for idx, record in enumerate(records):
            key = self._create_conflict_key(record, conflict_columns)
            groups[key].append((idx, record))
        
        duplicates_info = {k: v for k, v in groups.items() if len(v) > 1}
        
        if duplicates_info:
            total_duplicates = sum(len(v) for v in duplicates_info.values())
            self.logger.warning(f"Found {len(duplicates_info):,} duplicate groups "
                              f"affecting {total_duplicates:,} records")
        
        # Process each group
        deduped_records = []
        for key, items in groups.items():
            if len(items) == 1:
                deduped_records.append(items[0][1])
            else:
                merged_record = self._resolve_duplicates(
                    [item[1] for item in items], strategy, merge_rules
                )
                deduped_records.append(merged_record)
        
        self.logger.info(f"Deduplication completed: {len(deduped_records):,} unique records")
        return deduped_records, duplicates_info
    
    def _create_conflict_key(self, record: Dict[str, Any], columns: List[str]) -> tuple:
        """Create normalized key for conflict detection."""
        key_parts = []
        for col in columns:
            val = record.get(col)
            if isinstance(val, str):
                val = val.strip().lower() if val else None
            elif isinstance(val, float) and math.isnan(val):
                val = None
            key_parts.append(val)
        return tuple(key_parts)
    
    def _resolve_duplicates(
        self, 
        records: List[Dict[str, Any]], 
        strategy: MergeStrategy,
        merge_rules: Optional[Dict[str, FieldMergeMode]] = None
    ) -> Dict[str, Any]:
        """Resolve duplicates based on strategy."""
        
        if strategy == MergeStrategy.FIRST:
            return records[0]
        elif strategy == MergeStrategy.LAST:
            return records[-1]
        elif strategy == MergeStrategy.MERGE:
            return self._merge_records(records, merge_rules or {})
        else:  # KEEP_MAX
            # Implement max strategy based on a priority field
            return max(records, key=lambda r: r.get('priority_field', 0))

    def _merge_records(
        self, 
        records: List[Dict[str, Any]], 
        merge_rules: Dict[str, FieldMergeMode]
    ) -> Dict[str, Any]:
        """Merge multiple records using specified rules."""
        merged = copy.deepcopy(records[-1])  # Start with last record
        
        all_fields = set()
        for record in records:
            all_fields.update(record.keys())
        
        for field in all_fields:
            values = [record.get(field) for record in records]
            mode = merge_rules.get(field, FieldMergeMode.LAST)
            merged[field] = self._apply_merge_mode(values, mode)
        
        return merged
    
    def _apply_merge_mode(self, values: List[Any], mode: FieldMergeMode) -> Any:
        """Apply specific merge mode to field values."""
        # Filter out None and NaN values
        filtered = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
        
        if not filtered:
            return None
            
        if mode == FieldMergeMode.SUM:
            return sum(filtered)
        elif mode == FieldMergeMode.MAX:
            return max(filtered)
        elif mode == FieldMergeMode.MIN:
            return min(filtered)
        elif mode == FieldMergeMode.AVG:
            return sum(filtered) / len(filtered)
        elif mode == FieldMergeMode.CONCAT:
            return " | ".join(str(v) for v in filtered)
        elif mode == FieldMergeMode.FIRST:
            return next((v for v in values if v is not None), None)
        else:  # LAST
            return next((v for v in reversed(values) if v is not None), None)