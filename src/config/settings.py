"""
Configuration module for the job scraper.

Loads configuration from files and environment variables.
"""

import os
import json
from pathlib import Path
from typing import Optional


class Settings:
    """Application settings and configuration."""
    
    def __init__(self):
        self.proxy_username: str = os.getenv("PROXY_USERNAME", "")
        self.proxy_password: str = os.getenv("PROXY_PASSWORD", "")
        self.proxy_host: str = os.getenv("PROXY_HOST", "la.residential.rayobyte.com")
        self.proxy_port: str = os.getenv("PROXY_PORT", "8000")
        
        self.service_account_path: str = os.getenv(
            "SERVICE_ACCOUNT_PATH",
            str(Path(__file__).parent / "service-account.json")
        )
        
        self.google_sheets_url: str = os.getenv("GOOGLE_SHEETS_URL", "")
        
        self.read_requests_per_minute: int = 300
        self.write_requests_per_minute: int = 60
        self.total_requests_per_100_seconds: int = 500
        
        self.scrape_interval_seconds: int = 3600
        self.page_delay_seconds: int = 1
        self.request_timeout_seconds: int = 30
    
    def get_proxies(self) -> Optional[dict]:
        """
        Returns proxy configuration if credentials are available.
        
        Returns:
            Dictionary with http/https proxy configuration or None
        """
        if self.proxy_username and self.proxy_password:
            proxy_url = f"http://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}"
            return {
                "http": proxy_url,
                "https": proxy_url
            }
        return None
    
    def load_service_account_credentials(self) -> dict:
        """
        Loads service account credentials from JSON file.
        
        Returns:
            Dictionary containing service account credentials
            
        Raises:
            FileNotFoundError: If service account file doesn't exist
            ValueError: If JSON is invalid
        """
        if not Path(self.service_account_path).exists():
            raise FileNotFoundError(
                f"Service account file not found at: {self.service_account_path}"
            )
        
        with open(self.service_account_path, "r") as f:
            return json.load(f)
    
    def validate(self) -> None:
        """
        Validates required configuration.
        
        Raises:
            ValueError: If required configuration is missing
        """
        if not Path(self.service_account_path).exists():
            raise FileNotFoundError(
                f"Service account file not found: {self.service_account_path}\n"
                f"Please place your service-account.json file in the config directory."
            )
        if not self.google_sheets_url:
            raise ValueError("GOOGLE_SHEETS_URL environment variable not set")


settings = Settings()
