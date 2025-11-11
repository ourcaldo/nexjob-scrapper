"""
Job scraper service module for orchestrating the entire scraping workflow.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Set
from src.config.settings import Settings
from src.clients.loker.loker_client import LokerClient
from src.clients.jobstreet.jobstreet_client import JobStreetClient
from src.clients.sheets_client import SheetsClient
from src.transformers.loker_transformer import LokerTransformer
from src.transformers.jobstreet_transformer import JobStreetTransformer
from src.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class ScraperService:
    """
    Orchestrates the job scraping workflow for multiple sources.
    
    Coordinates between job source clients (Loker.id, JobStreet), Google Sheets client, 
    and source-specific data transformers to scrape and store job postings.
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the scraper service.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            read_requests_per_minute=settings.read_requests_per_minute,
            write_requests_per_minute=settings.write_requests_per_minute,
            total_requests_per_100_seconds=settings.total_requests_per_100_seconds
        )
        
        # Initialize source clients
        self.loker_client = LokerClient(
            proxies=settings.get_proxies(),
            timeout=settings.request_timeout_seconds
        )
        
        self.jobstreet_client = JobStreetClient(
            timeout=settings.request_timeout_seconds,
            page_size=30,
            proxies=settings.get_proxies()
        )
        
        # Initialize transformers (one per source)
        self.loker_transformer = LokerTransformer()
        self.jobstreet_transformer = JobStreetTransformer()
        
        self.sheets_client = None
        self.existing_ids: Set[str] = set()
    
    def initialize_sheets_client(self) -> bool:
        """
        Initialize and connect to Google Sheets.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.settings.validate()
            
            credentials_dict = self.settings.load_service_account_credentials()
            
            self.sheets_client = SheetsClient(
                credentials_dict=credentials_dict,
                sheet_url=self.settings.google_sheets_url,
                worksheet_name=self.settings.google_sheets_worksheet,
                rate_limiter=self.rate_limiter
            )
            
            if not self.sheets_client.connect():
                logger.error("Failed to connect to Google Sheets")
                return False
            
            self.existing_ids = self.sheets_client.get_existing_ids()
            return True
            
        except Exception as e:
            logger.error(f"Error initializing sheets client: {e}")
            return False
    
    def process_loker_job(self, job: dict) -> bool:
        """
        Process and store a single Loker.id job listing if it's not a duplicate.
        
        Args:
            job: Job dictionary from Loker.id API
            
        Returns:
            True if job was added, False if duplicate or error
        """
        if not self.sheets_client:
            logger.error("Sheets client not initialized")
            return False
            
        try:
            job_id = str(job["id"])
            
            if job_id in self.existing_ids:
                return False
            
            headers = self.sheets_client.get_headers()
            row_data = self.loker_transformer.transform_job(job, headers)
            
            if self.sheets_client.append_row(row_data):
                self.existing_ids.add(job_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to process Loker.id job {job.get('id')}: {e}")
            return False
    
    def process_jobstreet_job(self, job: dict) -> bool:
        """
        Process and store a single JobStreet job listing if it's not a duplicate.
        
        This method expects a combined job dict with both search API data
        and HTML scraped data (content, pendidikan, pengalaman, gender).
        
        Args:
            job: Combined job dictionary (search API + HTML data)
            
        Returns:
            True if job was added, False if duplicate or error
        """
        if not self.sheets_client:
            logger.error("Sheets client not initialized")
            return False
            
        try:
            job_id = self.jobstreet_transformer.extract_job_id(job)
            
            if job_id in self.existing_ids:
                return False
            
            headers = self.sheets_client.get_headers()
            row_data = self.jobstreet_transformer.transform_job(job, headers)
            
            if self.sheets_client.append_row(row_data):
                self.existing_ids.add(job_id)
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to process JobStreet job {job.get('id')}: {e}")
            return False
    
    def scrape_loker_all_pages(self) -> int:
        """
        Scrape job listings from Loker.id.
        
        Respects MAX_PAGES_LOKER setting (0 = unlimited).
        
        Returns:
            Number of new jobs added
        """
        total_new_jobs = 0
        page_num = 1
        max_pages = self.settings.max_pages_loker if self.settings.max_pages_loker > 0 else float('inf')
        
        logger.info(f"Starting Loker.id scraping (max {max_pages if max_pages != float('inf') else 'unlimited'} pages)...")
        
        while page_num <= max_pages:
            logger.info(f"Scraping Loker.id page {page_num}...")
            jobs_data, has_more = self.loker_client.fetch_page(page_num)
            
            if not jobs_data:
                logger.info(f"No more data found at Loker.id page {page_num}")
                break
            
            page_new_jobs = 0
            
            for job in jobs_data:
                if self.process_loker_job(job):
                    page_new_jobs += 1
            
            total_new_jobs += page_new_jobs
            logger.info(f"Loker.id page {page_num} processed. Added {page_new_jobs} new jobs")
            
            if not has_more:
                break
            
            page_num += 1
            time.sleep(self.settings.page_delay_seconds)
        
        logger.info(f"Loker.id scraping complete. Total {total_new_jobs} new jobs added")
        return total_new_jobs
    
    def scrape_jobstreet_all_pages(self, max_pages: int = 10) -> int:
        """
        Scrape job listings from JobStreet.
        
        This method:
        1. Fetches job listings from search API
        2. For each job, fetches detail page HTML
        3. Merges search data with HTML data
        4. Transforms and stores in Google Sheets
        
        Args:
            max_pages: Maximum number of pages to scrape (default: 10 for testing)
            
        Returns:
            Number of new jobs added
        """
        total_new_jobs = 0
        page_num = 1
        
        logger.info(f"Starting JobStreet scraping (max {max_pages} pages)...")
        
        while page_num <= max_pages:
            logger.info(f"Scraping JobStreet page {page_num}...")
            
            try:
                jobs_data, has_more, total_count = self.jobstreet_client.fetch_search_page(page_num)
                
                if not jobs_data:
                    logger.info(f"No more data found at JobStreet page {page_num}")
                    break
                
                page_new_jobs = 0
                
                for job in jobs_data:
                    try:
                        job_id = self.jobstreet_transformer.extract_job_id(job)
                        
                        if job_id in self.existing_ids:
                            logger.debug(f"Skipping duplicate JobStreet job {job_id}")
                            continue
                        
                        logger.debug(f"Fetching detail for JobStreet job {job_id}...")
                        job_detail = self.jobstreet_client.fetch_job_detail(job_id)
                        
                        combined_job = {**job, "detail": job_detail}
                        
                        if self.process_jobstreet_job(combined_job):
                            page_new_jobs += 1
                        
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"Error processing JobStreet job: {e}")
                        continue
                
                total_new_jobs += page_new_jobs
                logger.info(f"JobStreet page {page_num} processed. Added {page_new_jobs} new jobs")
                
                if not has_more:
                    logger.info("No more JobStreet pages available")
                    break
                
                page_num += 1
                time.sleep(self.settings.page_delay_seconds)
                
            except Exception as e:
                logger.error(f"Error scraping JobStreet page {page_num}: {e}")
                break
        
        logger.info(f"JobStreet scraping complete. Total {total_new_jobs} new jobs added")
        return total_new_jobs
    
    def run_once(self) -> int:
        """
        Execute a single scraping run for enabled sources.
        
        Scrapes from sources based on environment configuration:
        - Loker.id (if ENABLE_LOKER=true)
        - JobStreet (if ENABLE_JOBSTREET=true)
        
        Returns:
            Total number of new jobs added from all sources
        """
        logger.info("Starting scraping run...")
        
        if not self.initialize_sheets_client():
            logger.error("Failed to initialize sheets client")
            return 0
        
        total_new_jobs = 0
        enabled_sources = []
        
        if self.settings.enable_loker:
            enabled_sources.append("Loker.id")
            logger.info("Scraping from Loker.id...")
            loker_jobs = self.scrape_loker_all_pages()
            total_new_jobs += loker_jobs
            logger.info(f"Loker.id: Added {loker_jobs} new jobs")
        
        if self.settings.enable_jobstreet:
            enabled_sources.append("JobStreet")
            logger.info("Scraping from JobStreet...")
            max_pages = self.settings.max_pages_jobstreet if self.settings.max_pages_jobstreet > 0 else float('inf')
            jobstreet_jobs = self.scrape_jobstreet_all_pages(max_pages=int(max_pages) if max_pages != float('inf') else 999999)
            total_new_jobs += jobstreet_jobs
            logger.info(f"JobStreet: Added {jobstreet_jobs} new jobs")
        
        if not enabled_sources:
            logger.warning("No job sources are enabled! Check your .env configuration.")
        else:
            logger.info(f"Enabled sources: {', '.join(enabled_sources)}")
        
        logger.info(f"Scraping run completed. Added {total_new_jobs} new jobs from {len(enabled_sources)} source(s)")
        return total_new_jobs
    
    def run_continuous(self) -> None:
        """
        Run the scraper continuously with configured intervals.
        """
        proxies = self.settings.get_proxies()
        if proxies:
            logger.info(f"Using proxy: {self.settings.proxy_username}@{self.settings.proxy_host}:{self.settings.proxy_port}")
        else:
            logger.warning("No proxy configured - using direct connection")
        
        while True:
            start_time = datetime.now()
            logger.info(f"Starting scraping at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            try:
                self.run_once()
            except Exception as e:
                logger.error(f"Error during scraping: {e}", exc_info=True)
            
            # Calculate sleep time
            end_time = datetime.now()
            elapsed = (end_time - start_time).total_seconds()
            sleep_time = max(self.settings.scrape_interval_seconds - elapsed, 0)
            
            next_run = end_time + timedelta(seconds=sleep_time)
            logger.info(f"Next run in {sleep_time/60:.1f} minutes at {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            
            time.sleep(sleep_time)
