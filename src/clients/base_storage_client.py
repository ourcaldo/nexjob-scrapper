"""
Base storage client interface for job scraper data persistence.

This abstract base class defines the interface that all storage backends
(Google Sheets, Supabase, etc.) must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Set, Optional


class BaseStorageClient(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the storage backend.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_headers(self) -> List[str]:
        """
        Get the column headers/field names for the storage.
        
        Returns:
            List of header names in order
        """
        pass
    
    @abstractmethod
    def get_existing_ids(self) -> Set[str]:
        """
        Retrieve existing job source IDs for duplicate detection.
        
        Returns:
            Set of source_id values already stored
        """
        pass
    
    @abstractmethod
    def append_row(self, row_data: List[str]) -> bool:
        """
        Add a new job record to storage.
        
        Args:
            row_data: List of values matching the headers
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """
        Close connection to the storage backend.
        """
        pass
