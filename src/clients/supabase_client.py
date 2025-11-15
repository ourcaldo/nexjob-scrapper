"""
Supabase client module for PostgreSQL storage backend.
"""

import logging
from typing import List, Set, Optional
from supabase import create_client, Client
from src.clients.base_storage_client import BaseStorageClient

logger = logging.getLogger(__name__)


class SupabaseClient(BaseStorageClient):
    """Client for interacting with Supabase PostgreSQL database."""
    
    # Define the standard headers/columns in order
    HEADERS = [
        "internal_id", "source_id", "job_source", "link", "company_name",
        "job_category", "title", "content", "province", "city",
        "experience", "job_type", "level", "salary_min", "salary_max",
        "education", "work_policy", "industry", "gender", "tags"
    ]
    
    def __init__(
        self,
        supabase_url: str,
        supabase_key: str,
        table_name: str = "job_scraper"
    ):
        """
        Initialize the Supabase client.
        
        Args:
            supabase_url: Supabase project URL
            supabase_key: Supabase API key (anon or service role)
            table_name: Name of the table to use (default: job_scraper)
        """
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.table_name = table_name
        self.client: Optional[Client] = None
    
    def connect(self) -> bool:
        """
        Establishes connection to Supabase.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.client = create_client(self.supabase_url, self.supabase_key)
            
            # Test the connection by querying the table
            response = self.client.table(self.table_name).select("id").limit(1).execute()
            
            logger.info(f"Successfully connected to Supabase table: {self.table_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Supabase: {e}")
            return False
    
    def get_headers(self) -> List[str]:
        """
        Returns the standard column headers.
        
        Returns:
            List of header column names
        """
        return self.HEADERS.copy()
    
    def get_existing_ids(self) -> Set[str]:
        """
        Gets all existing job source IDs from the database.
        
        Returns:
            Set of existing job source IDs
        """
        try:
            if not self.client:
                logger.error("Not connected to Supabase")
                return set()
            
            # Query all source_ids from the table
            response = self.client.table(self.table_name).select("source_id").execute()
            
            existing_ids = {row["source_id"] for row in response.data if row.get("source_id")}
            logger.info(f"Found {len(existing_ids)} existing jobs in database")
            return existing_ids
            
        except Exception as e:
            logger.error(f"Error fetching existing IDs: {e}")
            return set()
    
    def append_row(self, row_data: List[str]) -> bool:
        """
        Inserts a new job record into the database.
        
        Args:
            row_data: List of values matching the headers
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.client:
                logger.error("Not connected to Supabase")
                return False
            
            # Map row_data to column names
            data = {}
            for i, header in enumerate(self.HEADERS):
                if i < len(row_data):
                    value = row_data[i]
                    
                    # Handle empty strings and None values
                    if value == "" or value is None:
                        if header in ["salary_min", "salary_max"]:
                            data[header] = 0
                        else:
                            data[header] = None
                    # Convert salary fields to integers
                    elif header in ["salary_min", "salary_max"]:
                        try:
                            data[header] = int(value) if value else 0
                        except (ValueError, TypeError):
                            data[header] = 0
                    else:
                        data[header] = value
            
            # Add default status for new jobs
            data["status"] = "active"
            
            # Insert the record
            response = self.client.table(self.table_name).insert(data).execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to insert record: {e}")
            return False
    
    def disconnect(self) -> None:
        """
        Close connection to Supabase.
        
        Note: Supabase client uses connection pooling, so explicit disconnect is not required.
        """
        self.client = None
        logger.info("Disconnected from Supabase")
