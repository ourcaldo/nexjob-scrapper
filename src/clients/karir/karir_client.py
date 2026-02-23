"""
Karir.com API client module.
"""

import requests
import logging
from typing import Optional, Tuple, List, Dict, Any
from src.utils.retry import retry_request

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://gateway2-beta.karir.com/v2/search/opportunities"
_DETAIL_URL = "https://gateway2-beta.karir.com/v1/opportunity/detail"
class KarirClient:
    """Client for interacting with Karir.com REST API."""

    PAGE_SIZE = 20

    def __init__(self, timeout: int = 30):
        """
        Initialize the Karir.com API client.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
        })

    def fetch_page(self, offset: int = 0) -> Tuple[Optional[List[Dict[str, Any]]], bool, int]:
        """
        Fetch a single page of job listings from the search endpoint.

        Args:
            offset: Number of records to skip (0-based)

        Returns:
            Tuple of (jobs, has_more, total) where:
                - jobs: List of job dicts, or None on error
                - has_more: True if more pages remain
                - total: Total number of available jobs
        """
        payload = {
            "keyword": "",
            "location_ids": [],
            "company_ids": [],
            "industry_ids": [],
            "job_function_ids": [],
            "degree_ids": [],
            "locale": "id",
            "limit": self.PAGE_SIZE,
            "offset": offset,
            "level": "",
            "is_opportunity": True,
            "sort_order": "",
            "is_recomendation": False,
            "is_preference": False,
            "is_choice_opportunity": False,
            "is_subscribe": False,
            "workplace": None,
        }

        try:
            response = self.session.post(_SEARCH_URL, json=payload, timeout=self.timeout)
            response.raise_for_status()

            data = response.json().get("data", {})
            jobs = data.get("opportunities") or []
            total = data.get("total_opportunities", 0)
            has_more = (offset + len(jobs)) < total

            logger.debug(f"Karir.com page offset={offset}: {len(jobs)} jobs returned (total={total})")
            return jobs, has_more, total

        except requests.exceptions.RequestException as e:
            logger.error(f"Karir.com fetch_page failed at offset={offset}: {e}")
            return None, False, 0

    def fetch_job_detail(self, opportunity_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch full job details from the detail endpoint.

        Args:
            opportunity_id: Integer job ID from the list endpoint

        Returns:
            Detail dict on success, None on error
        """
        payload = {
            "opportunity_id": opportunity_id,
            "language": "id",
        }

        try:
            response = retry_request(
                self.session.post,
                _DETAIL_URL,
                json=payload,
                timeout=self.timeout,
                exceptions=(requests.exceptions.RequestException,),
            )
            response.raise_for_status()

            data = response.json().get("data")
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Karir.com fetch_job_detail failed for id={opportunity_id}: {e}")
            return None
