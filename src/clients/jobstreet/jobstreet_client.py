"""
JobStreet client for fetching job listings and details.

This client uses a two-step process:
1. Fetch basic job data from the search API
2. Fetch detailed job descriptions by scraping HTML pages
"""

import requests
import logging
from typing import Optional, Tuple, List, Dict, Any
from bs4 import BeautifulSoup
import time
import re


logger = logging.getLogger(__name__)


class JobStreetClient:
    """Client for interacting with JobStreet job listings."""
    
    BASE_SEARCH_URL = "https://id.jobstreet.com/api/jobsearch/v5/search"
    BASE_JOB_URL = "https://id.jobstreet.com/id/job"
    
    def __init__(
        self, 
        timeout: int = 30,
        page_size: int = 30,
        proxies: Optional[dict] = None
    ):
        """
        Initialize JobStreet client.
        
        Args:
            timeout: Request timeout in seconds
            page_size: Number of jobs per page (default: 30)
            proxies: Optional proxy configuration
        """
        self.timeout = timeout
        self.page_size = page_size
        self.proxies = proxies
        self.session = requests.Session()
        
        if proxies:
            self.session.proxies.update(proxies)
    
    def fetch_search_page(self, page_num: int = 1) -> Tuple[Optional[List[Dict[str, Any]]], bool, int]:
        """
        Fetch a page of job listings from JobStreet search API.
        
        Args:
            page_num: Page number to fetch (1-indexed)
            
        Returns:
            Tuple of (jobs_data, has_more, total_count)
            - jobs_data: List of job dictionaries with basic info
            - has_more: Whether there are more pages available
            - total_count: Total number of jobs available
            
        Raises:
            requests.RequestException: If the request fails
        """
        params = {
            "siteKey": "ID",
            "page": page_num,
            "pageSize": self.page_size
        }
        
        try:
            logger.info(f"Fetching JobStreet search page {page_num}...")
            
            response = self.session.get(
                self.BASE_SEARCH_URL,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code == 404:
                logger.info(f"Page {page_num} returned 404 - no more pages")
                return None, False, 0
            
            response.raise_for_status()
            data = response.json()
            
            jobs = data.get("data", [])
            total_count = data.get("solMetadata", {}).get("totalJobCount", 0)
            
            total_pages = (total_count + self.page_size - 1) // self.page_size
            has_more = page_num < total_pages
            
            logger.info(
                f"Fetched {len(jobs)} jobs from page {page_num}/{total_pages} "
                f"(total: {total_count} jobs)"
            )
            
            return jobs, has_more, total_count
            
        except requests.RequestException as e:
            logger.error(f"Error fetching JobStreet search page {page_num}: {e}")
            raise
    
    def fetch_job_detail(self, job_id: str) -> Dict[str, Any]:
        """
        Fetch detailed job information by scraping the job detail HTML page.
        
        Args:
            job_id: The job ID to fetch details for
            
        Returns:
            Dictionary containing:
            - content: Cleaned HTML job description
            - pendidikan: Extracted education requirement
            - pengalaman: Extracted experience requirement
            - gender: Extracted gender requirement
            
        Raises:
            requests.RequestException: If the request fails
        """
        url = f"{self.BASE_JOB_URL}/{job_id}"
        
        try:
            logger.debug(f"Fetching job detail for ID {job_id}...")
            
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            
            job_detail = {
                "content": self._extract_job_description(soup),
                "pendidikan": self._extract_education(soup),
                "pengalaman": self._extract_experience(soup),
                "gender": self._extract_gender(soup)
            }
            
            logger.debug(f"Successfully extracted details for job {job_id}")
            return job_detail
            
        except requests.RequestException as e:
            logger.error(f"Error fetching job detail for {job_id}: {e}")
            raise
    
    def _extract_job_description(self, soup: BeautifulSoup) -> str:
        """
        Extract the job description HTML from the page.
        
        The job description is embedded in the HTML body.
        We look for sections containing job-related content.
        
        Args:
            soup: BeautifulSoup object of the job page
            
        Returns:
            Raw HTML string of the job description
        """
        content_html = ""
        
        # Find job description sections
        # JobStreet typically has sections with <strong> headers and <ul> lists
        for strong in soup.find_all("strong"):
            section_html = ""
            section_html += f"<strong>{strong.get_text()}</strong><br />"
            
            # Get the next sibling elements (usually <ul> or <p>)
            current = strong.next_sibling
            while current:
                if current.name in ["ul", "ol", "p", "div"]:
                    section_html += str(current)
                elif current.name == "br":
                    section_html += str(current)
                elif current.name == "strong":
                    # Stop when we hit the next section
                    break
                
                current = current.next_sibling
            
            content_html += section_html
        
        # If no content found with <strong> tags, try alternative selectors
        if not content_html:
            # Look for common job description containers
            job_desc = soup.find("div", {"data-automation": "jobDescription"})
            if job_desc:
                content_html = str(job_desc)
        
        return content_html or ""
    
    def _extract_education(self, soup: BeautifulSoup) -> str:
        """
        Extract education requirement from job description text.
        
        Args:
            soup: BeautifulSoup object of the job page
            
        Returns:
            Normalized education level (e.g., "S1", "SMA/SMK", "D1-D4")
        """
        text = soup.get_text().upper()
        
        # Education keywords mapping
        education_keywords = {
            "S3": "S3",
            "DOCTOR": "S3",
            "S2": "S2",
            "MASTER": "S2",
            "S1": "S1",
            "SARJANA": "S1",
            "D4": "D1-D4",
            "D3": "D1-D4",
            "D2": "D1-D4",
            "D1": "D1-D4",
            "DIPLOMA": "D1-D4",
            "SMK": "SMA/SMK",
            "SMA": "SMA/SMK",
            "STM": "SMA/SMK"
        }
        
        # Check for education keywords in order of priority (highest to lowest)
        for keyword, normalized in education_keywords.items():
            if keyword in text:
                return normalized
        
        return "Tanpa Minimal Pendidikan"
    
    def _extract_experience(self, soup: BeautifulSoup) -> str:
        """
        Extract experience requirement from job description text.
        
        Args:
            soup: BeautifulSoup object of the job page
            
        Returns:
            Normalized experience level (e.g., "1-3 Tahun", "3-5 Tahun")
        """
        text = soup.get_text()
        
        # Pattern to match experience mentions
        # Examples: "1 tahun", "2-3 tahun", "minimal 1 tahun"
        patterns = [
            r"(\d+)\s*[-–]\s*(\d+)\s*tahun",  # "2-3 tahun"
            r"minimal\s*(\d+)\s*tahun",        # "minimal 1 tahun"
            r"(\d+)\s*tahun",                  # "1 tahun"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Get the first match
                if isinstance(matches[0], tuple):
                    # Range match (e.g., "2-3 tahun")
                    years = int(matches[0][1])  # Use upper bound
                else:
                    # Single number match
                    years = int(matches[0])
                
                # Normalize to standard ranges
                if years <= 2:
                    return "1-3 Tahun"
                elif years <= 5:
                    return "3-5 Tahun"
                elif years <= 10:
                    return "5-10 Tahun"
                else:
                    return "Lebih dari 10 Tahun"
        
        # Check for "fresh graduate" mention
        if re.search(r"fresh\s+graduate", text, re.IGNORECASE):
            return "1-3 Tahun"
        
        return "1-3 Tahun"  # Default
    
    def _extract_gender(self, soup: BeautifulSoup) -> str:
        """
        Extract gender requirement from job description text.
        
        Args:
            soup: BeautifulSoup object of the job page
            
        Returns:
            Gender requirement (e.g., "Laki-laki/Perempuan", "Laki-laki", "Perempuan")
        """
        text = soup.get_text().lower()
        
        has_male = "laki-laki" in text or "pria" in text
        has_female = "perempuan" in text or "wanita" in text
        
        if has_male and has_female:
            return "Laki-laki/Perempuan"
        elif has_male:
            return "Laki-laki"
        elif has_female:
            return "Perempuan"
        else:
            return "Laki-laki/Perempuan"  # Default (no restriction)
    
    def close(self):
        """Close the session."""
        self.session.close()
