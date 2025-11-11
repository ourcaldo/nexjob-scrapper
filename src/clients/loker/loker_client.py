"""
Loker.id API client module.
"""

import requests
import logging
from typing import Optional, Tuple, List, Dict, Any

logger = logging.getLogger(__name__)


class LokerClient:
    """Client for interacting with Loker.id API."""
    
    def __init__(self, proxies: Optional[Dict[str, str]] = None, timeout: int = 30):
        """
        Initialize the Loker.id API client.
        
        Args:
            proxies: Optional proxy configuration dictionary
            timeout: Request timeout in seconds
        """
        self.proxies = proxies
        self.timeout = timeout
        self.base_url = "https://www.loker.id/cari-lowongan-kerja"
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json"
        }
    
    def fetch_page(self, page_num: int) -> Tuple[Optional[List[Dict[str, Any]]], bool]:
        """
        Fetches a single page of job listings.
        
        Args:
            page_num: Page number to fetch
            
        Returns:
            Tuple of (jobs_data, has_more) where:
                - jobs_data: List of job dictionaries or None on error
                - has_more: Boolean indicating if more pages exist
        """
        url = f"{self.base_url}/page/{page_num}?_data"
        
        try:
            response = requests.get(
                url,
                headers=self.headers,
                proxies=self.proxies,
                timeout=self.timeout
            )
            
            if response.status_code == 404:
                logger.info(f"No more pages at page {page_num}")
                return None, False
                
            response.raise_for_status()
            jobs = response.json().get("jobs", [])
            return jobs, True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch page {page_num}: {e}")
            return None, False
