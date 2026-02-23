"""
Glints GraphQL API client module.
"""

import logging
from typing import Optional, Tuple, List, Dict, Any
from curl_cffi import requests
from src.utils.retry import retry_request

logger = logging.getLogger(__name__)


class GlintsClient:
    """Client for interacting with Glints GraphQL API."""
    
    BASE_URL = "https://glints.com/api/v2-alc/graphql"
    
    DETAIL_QUERY = """query getJobDetailsById($opportunityId: String!, $traceInfo: String, $source: String) {
  getJobById(id: $opportunityId, traceInfo: $traceInfo, source: $source) {
    id
    title
    status
    type
    workArrangementOption
    descriptionJsonString
    educationLevel
    minYearsOfExperience
    maxYearsOfExperience
    gender
    company {
      name
      industry {
        name
      }
    }
    location {
      id
      name
      formattedName
      level
      administrativeLevelName
      parents {
        id
        name
        formattedName
        level
        administrativeLevelName
      }
    }
    skills {
      mustHave
      skill {
        name
      }
    }
    salaries {
      minAmount
      maxAmount
    }
    hierarchicalJobCategory {
      level
      name
      parents {
        level
        name
      }
    }
  }
}"""
    
    GRAPHQL_QUERY = """query searchJobsV3($data: JobSearchConditionInput!) {
  searchJobsV3(data: $data) {
    jobsInPage {
      id
      title
      workArrangementOption
      status
      type
      educationLevel
      minYearsOfExperience
      maxYearsOfExperience
      company {
        name
        industry {
          name
        }
      }
      location {
        id
        name
        formattedName
        level
        administrativeLevelName
        parents {
          id
          name
          formattedName
          level
          administrativeLevelName
        }
      }
      salaries {
        minAmount
        maxAmount
      }
      skills {
        skill {
          name
        }
        mustHave
      }
      hierarchicalJobCategory {
        level
        name
        parents {
          level
          name
        }
      }
      traceInfo
    }
    hasMore
  }
}"""
    
    def __init__(
        self,
        timeout: int = 30,
        page_size: int = 20,
        country_code: str = "ID",
        proxies: Optional[dict] = None
    ):
        """
        Initialize Glints GraphQL client.
        
        Args:
            timeout: Request timeout in seconds
            page_size: Number of jobs per page (default: 20)
            country_code: Country code for job search (default: "ID" for Indonesia)
            proxies: Optional proxy configuration
        """
        self.timeout = timeout
        self.page_size = page_size
        self.country_code = country_code
        self.proxies = proxies
        self.session = requests.Session(
            impersonate="chrome120",
            proxies=proxies or {},
        )
        
        self.session.headers.update({
            "Origin": "https://glints.com",
            "Referer": "https://glints.com/id/opportunities/jobs/explore",
        })
        
        self._warm_session()
    
    def _warm_session(self) -> None:
        """
        Visit the Glints explore page to acquire session cookies before
        making any GraphQL requests. Glints (Cloudflare-protected) blocks
        API calls without the cookie set by this page visit.
        """
        try:
            logger.info("Warming Glints session (fetching explore page for cookies)...")
            resp = self.session.get(
                "https://glints.com/id/opportunities/jobs/explore",
                timeout=self.timeout,
            )
            logger.info(f"Glints session warm-up: HTTP {resp.status_code} | cookies: {list(self.session.cookies.keys())}")
        except Exception as e:
            logger.warning(f"Glints session warm-up failed (will try anyway): {e}")
    
    def fetch_page(self, page_num: int = 1) -> Tuple[Optional[List[Dict[str, Any]]], bool]:
        """
        Fetch a page of job listings from Glints GraphQL API.
        
        Args:
            page_num: Page number to fetch (1-indexed)
            
        Returns:
            Tuple of (jobs_data, has_more) where:
                - jobs_data: List of job dictionaries with complete info
                - has_more: Whether there are more pages available
        """
        payload = {
            "operationName": "searchJobsV3",
            "variables": {
                "data": {
                    "CountryCode": self.country_code,
                    "includeExternalJobs": True,
                    "pageSize": self.page_size,
                    "page": page_num,
                    "sortBy": "LATEST"
                }
            },
            "query": self.GRAPHQL_QUERY
        }
        
        try:
            logger.info(f"Fetching Glints page {page_num} (pageSize: {self.page_size})...")
            
            response = retry_request(
                self.session.post,
                f"{self.BASE_URL}?op=searchJobsV3",
                json=payload,
                timeout=self.timeout,
                exceptions=(Exception,),
            )
            
            if response.status_code == 404:
                logger.info(f"Page {page_num} returned 404 - no more pages")
                return None, False
            
            response.raise_for_status()
            data = response.json()
            
            search_results = data.get("data", {}).get("searchJobsV3", {})
            jobs = search_results.get("jobsInPage", [])
            has_more = search_results.get("hasMore", False)
            
            logger.info(
                f"Fetched {len(jobs)} jobs from Glints page {page_num} "
                f"(hasMore: {has_more})"
            )
            
            return jobs, has_more
            
        except Exception as e:
            logger.error(f"Error fetching Glints page {page_num}: {e}")
            return None, False
    
    def fetch_job_detail(
        self, 
        job_id: str, 
        trace_info: Optional[str] = None, 
        source: str = "Explore"
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed job information from Glints GraphQL API.
        
        Args:
            job_id: The job ID (opportunityId)
            trace_info: Optional trace info from search results
            source: Source of the request (default: "Explore")
            
        Returns:
            Dictionary with complete job details or None if error
        """
        payload = {
            "operationName": "getJobDetailsById",
            "variables": {
                "opportunityId": job_id,
                "traceInfo": trace_info or "",
                "source": source
            },
            "query": self.DETAIL_QUERY
        }
        
        try:
            logger.debug(f"Fetching Glints job detail for ID: {job_id}")
            
            response = retry_request(
                self.session.post,
                f"{self.BASE_URL}?op=getJobDetailsById",
                json=payload,
                timeout=self.timeout,
                exceptions=(Exception,),
            )
            
            response.raise_for_status()
            data = response.json()
            
            job_detail = data.get("data", {}).get("getJobById", {})
            
            if not job_detail:
                logger.warning(f"No detail data found for job {job_id}")
                return None
            
            logger.debug(f"Successfully fetched detail for job {job_id}")
            return job_detail
            
        except Exception as e:
            logger.error(f"Error fetching Glints job detail {job_id}: {e}")
            return None
    
    def close(self):
        """Close the session."""
        self.session.close()
