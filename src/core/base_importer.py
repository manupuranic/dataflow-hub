from abc import ABC, abstractmethod
import math
from typing import Dict, List, Any, Optional, Union
import pandas as pd
from pathlib import Path
from tqdm.auto import tqdm
from src.utils.logger import get_logger
from src.core.data_processor import DataProcessor, ProcessingStats, MergeStrategy, FieldMergeMode
from src.core.exceptions import *

class BaseImporter(ABC):
    """
    Abstract base class for all data importers.
    
    Provides common functionality for:
    - File loading and validation
    - Data processing and normalization  
    - Batch processing
    - Error handling and logging
    - Statistics tracking
    """
    
    def __init__(self, db_connection, config: Dict[str, Any] = None):
        """
        Initialize the importer.
        
        Args:
            db_connection: Database connection object
            config: Configuration dictionary
        """
        self.db = db_connection
        self.config = config or {}
        self.logger = get_logger(self.__class__.__name__)
        self.processor = DataProcessor()
        self.stats = ProcessingStats()
        
        # Default configuration
        self.chunk_size = self.config.get('chunk_size', 500)
        self.max_retries = self.config.get('max_retries', 3)
        self.enable_validation = self.config.get('enable_validation', True)
        
        self.logger.info(f"🚀 {self.__class__.__name__} initialized")
    
    @abstractmethod
    def get_table_name(self) -> str:
        """Return the target database table name."""
        pass
    
    @abstractmethod
    def get_conflict_columns(self) -> List[str]:
        """Return columns used for conflict resolution."""
        pass
    
    @abstractmethod
    def process_row(self, row: pd.Series) -> Optional[Dict[str, Any]]:
        """
        Process a single row of data.
        
        Args:
            row: Pandas Series representing a row
            
        Returns:
            Dictionary of processed data or None if row should be skipped
        """
        pass
    
    @abstractmethod
    def validate_input_data(self, df: pd.DataFrame) -> bool:
        """
        Validate input data format and required columns.
        
        Args:
            df: Input dataframe
            
        Returns:
            True if validation passes, False otherwise
        """
        pass
    
    def get_merge_rules(self) -> Dict[str, FieldMergeMode]:
        """Return merge rules for duplicate resolution. Override in subclasses."""
        return {
            'current_stock': FieldMergeMode.SUM,
            'quantity': FieldMergeMode.SUM,
            'amount': FieldMergeMode.SUM,
        }
    
    def get_required_columns(self) -> List[str]:
        """Return list of required columns. Override in subclasses."""
        return []
    
    def preprocess_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Preprocess dataframe before row-by-row processing.
        Override in subclasses for custom preprocessing.
        """
        return df
    
    def postprocess_batch(self, batch_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Postprocess batch data before database insertion.
        Override in subclasses for custom postprocessing.
        """
        return batch_data
    
    def load_and_validate_file(self, file_path: str) -> pd.DataFrame:
        """Load file and perform basic validation."""
        self.logger.info(f"📂 Loading data from: {file_path}")
        
        if not Path(file_path).exists():
            raise FileProcessingError(f"File not found: {file_path}")
        
        try:
            # Import your existing read_data function
            from utils.helpers import read_data
            df = read_data(file_path)
            
            self.stats.total_input_records = len(df)
            self.logger.info(f"✅ Loaded {len(df):,} records from {Path(file_path).name}")
            
            # Validate if enabled
            if self.enable_validation and not self.validate_input_data(df):
                raise DataValidationError("Input data validation failed")
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error loading file {file_path}: {e}")
            raise FileProcessingError(f"Failed to load {file_path}: {e}")
    
    def process_batch(self, batch_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Process a batch of rows into database records."""
        batch_records = []
        
        for idx, row in batch_df.iterrows():
            try:
                processed_record = self.process_row(row)
                if processed_record:
                    batch_records.append(processed_record)
                    self.stats.successful_records += 1
                else:
                    self.stats.skipped_records += 1
                    
            except Exception as e:
                self.logger.warning(f"⚠️  Error processing row {idx}: {e}")
                self.stats.error_records += 1
        
        return batch_records
    
    def insert_batch(self, batch_data: List[Dict[str, Any]]) -> int:
        """Insert batch data into database with deduplication."""
        if not batch_data:
            return 0
        
        try:
            # Apply postprocessing
            batch_data = self.postprocess_batch(batch_data)
            
            # Deduplicate within batch
            deduped_data, dup_info = self.processor.deduplicate_records(
                batch_data,
                self.get_conflict_columns(),
                strategy=MergeStrategy.MERGE,
                merge_rules=self.get_merge_rules()
            )
            
            self.stats.duplicate_groups += len(dup_info)
            
            # Bulk insert/update
            self.db.bulkUpsertRecords(
                self.get_table_name(),
                deduped_data,
                conflict_columns=self.get_conflict_columns()
            )
            
            inserted_count = len(deduped_data)
            self.logger.info(f"✅ Inserted/updated {inserted_count:,} records")
            return inserted_count
            
        except Exception as e:
            self.logger.error(f"❌ Database insertion error: {e}")
            self.stats.database_errors += 1
            return 0
    
    def run_import(
        self, 
        file_path: str, 
        chunk_size: Optional[int] = None,
        offset: int = 0
    ) -> ProcessingStats:
        """
        Main import orchestration method.
        
        Args:
            file_path: Path to input file
            chunk_size: Override default chunk size
            offset: Number of records to skip
            
        Returns:
            ProcessingStats with detailed metrics
        """
        chunk_size = chunk_size or self.chunk_size
        self.logger.info(f"🚀 Starting {self.get_table_name()} import")
        self.logger.info(f"⚙️  Config: chunk_size={chunk_size}, offset={offset}")
        
        try:
            # Load and validate data
            df = self.load_and_validate_file(file_path)
            
            # Apply preprocessing
            df = self.preprocess_dataframe(df)
            
            # Apply offset
            if offset > 0:
                self.logger.info(f"⏭️  Applying offset: {offset:,} records")
                df = df.iloc[offset:]
            
            total_records = len(df)
            total_batches = math.ceil(total_records / chunk_size)
            self.logger.info(f"📊 Processing {total_records:,} records in {total_batches} batches")
            
            # Process in batches
            for i in range(0, total_records, chunk_size):
                batch_num = i // chunk_size + 1
                batch_df = df.iloc[i:i + chunk_size]
                
                self.logger.info(f"📦 Processing Batch {batch_num}/{total_batches} "
                               f"({len(batch_df)} records)")
                
                # Process batch
                batch_records = self.process_batch(batch_df)
                
                # Insert batch
                if batch_records:
                    inserted_count = self.insert_batch(batch_records)
                    self.stats.total_output_records += inserted_count
                
                # Progress update
                progress = (batch_num / total_batches) * 100
                self.logger.info(f"📈 Progress: {progress:.1f}% complete")
            
            self.stats.finish()
            self.stats.log_summary()
            return self.stats
            
        except Exception as e:
            self.logger.error(f"💥 Import failed: {e}")
            self.stats.finish()
            raise