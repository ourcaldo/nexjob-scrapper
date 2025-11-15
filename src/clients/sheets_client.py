"""
Google Sheets client module.
"""

import logging
from typing import List, Set, Optional, Dict, Any
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from src.utils.rate_limiter import RateLimiter
from src.clients.base_storage_client import BaseStorageClient

logger = logging.getLogger(__name__)


class SheetsClient(BaseStorageClient):
    """Client for interacting with Google Sheets."""
    
    def __init__(
        self,
        credentials_dict: Dict[str, Any],
        sheet_url: str,
        worksheet_name: str = "Loker.id",
        rate_limiter: Optional[RateLimiter] = None
    ):
        """
        Initialize the Google Sheets client.
        
        Args:
            credentials_dict: Dictionary containing service account credentials
            sheet_url: URL of the Google Sheet
            worksheet_name: Name of the worksheet to use
            rate_limiter: Optional RateLimiter instance for API quota management
        """
        self.credentials_dict = credentials_dict
        self.sheet_url = sheet_url
        self.worksheet_name = worksheet_name
        self.rate_limiter = rate_limiter
        self.sheet = None
        self.headers = []
    
    def connect(self) -> bool:
        """
        Establishes connection to Google Sheets.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(self.credentials_dict, scope)
            client = gspread.authorize(creds)
            
            self.sheet = client.open_by_url(self.sheet_url).worksheet(self.worksheet_name)
            
            if self.rate_limiter:
                self.rate_limiter.check("read")
            self.headers = self.sheet.row_values(1)
            
            logger.info(f"Successfully connected to Google Sheets worksheet: {self.worksheet_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            return False
    
    def get_existing_ids(self) -> Set[str]:
        """
        Gets all existing job source IDs from column B (source_id).
        
        Returns:
            Set of existing job source IDs
        """
        try:
            if self.rate_limiter:
                self.rate_limiter.check("read")
            
            # Column B is index 2 in gspread (A=1, B=2, C=3)
            # source_id is now in column B (internal_id is column A)
            existing_ids = self.sheet.col_values(2)[1:]  # Skip header row
            logger.info(f"Found {len(existing_ids)} existing jobs in sheet")
            return set(existing_ids)
            
        except Exception as e:
            logger.error(f"Error fetching existing IDs: {e}")
            return set()
    
    def append_row(self, row_data: List[str]) -> bool:
        """
        Appends a row to the sheet.
        
        Args:
            row_data: List of values to append
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.rate_limiter:
                self.rate_limiter.check("write")
            
            self.sheet.append_row(row_data, value_input_option="USER_ENTERED")
            return True
            
        except Exception as e:
            logger.error(f"Failed to append row: {e}")
            return False
    
    def get_headers(self) -> List[str]:
        """
        Returns the header row from the sheet.
        
        Returns:
            List of header column names
        """
        return self.headers
    
    def disconnect(self) -> None:
        """
        Close connection to Google Sheets.
        
        Note: Google Sheets API doesn't require explicit disconnection.
        """
        logger.info("Disconnecting from Google Sheets (no-op)")
