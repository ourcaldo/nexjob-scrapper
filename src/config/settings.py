"""
Configuration module for the job scraper.

Loads configuration from files and environment variables.
"""

import os
import json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


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
        self.google_sheets_worksheet: str = os.getenv("GOOGLE_SHEETS_WORKSHEET", "Jobs")
        
        self.enable_loker: bool = os.getenv("ENABLE_LOKER", "true").lower() == "true"
        self.enable_jobstreet: bool = os.getenv("ENABLE_JOBSTREET", "false").lower() == "true"
        self.enable_glints: bool = os.getenv("ENABLE_GLINTS", "true").lower() == "true"
        self.enable_linkedin: bool = os.getenv("ENABLE_LINKEDIN", "false").lower() == "true"
        
        self.max_pages_loker: int = int(os.getenv("MAX_PAGES_LOKER", "0"))
        self.max_pages_jobstreet: int = int(os.getenv("MAX_PAGES_JOBSTREET", "10"))
        self.max_pages_glints: int = int(os.getenv("MAX_PAGES_GLINTS", "10"))
        
        self.read_requests_per_minute: int = int(os.getenv("READ_REQUESTS_PER_MINUTE", "300"))
        self.write_requests_per_minute: int = int(os.getenv("WRITE_REQUESTS_PER_MINUTE", "60"))
        self.total_requests_per_100_seconds: int = int(os.getenv("TOTAL_REQUESTS_PER_100_SECONDS", "500"))
        
        self.scrape_interval_seconds: int = int(os.getenv("SCRAPE_INTERVAL_SECONDS", "3600"))
        self.page_delay_seconds: int = int(os.getenv("PAGE_DELAY_SECONDS", "1"))
        self.request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
    
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
        
        if not any([self.enable_loker, self.enable_jobstreet, self.enable_glints, self.enable_linkedin]):
            raise ValueError(
                "At least one job source must be enabled. "
                "Set ENABLE_LOKER=true, ENABLE_JOBSTREET=true, or ENABLE_GLINTS=true in your .env file"
            )


settings = Settings()
