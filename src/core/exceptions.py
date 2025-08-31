class DataFlowError(Exception):
    """Base exception for DataFlow Hub."""
    pass

class DataValidationError(DataFlowError):
    """Raised when data validation fails."""
    pass

class ImportConfigError(DataFlowError):
    """Raised when import configuration is invalid."""
    pass

class DatabaseConnectionError(DataFlowError):
    """Raised when database connection fails."""
    pass

class FileProcessingError(DataFlowError):
    """Raised when file processing fails."""
    pass