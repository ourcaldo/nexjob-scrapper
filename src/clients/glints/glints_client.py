"""
Glints GraphQL API client module.
"""

import requests
import logging
from typing import Optional, Tuple, List, Dict, Any

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
    createdAt
    updatedAt
    expiryDate
    descriptionJsonString
    interviewProcessJsonString
    educationLevel
    minYearsOfExperience
    maxYearsOfExperience
    gender
    minAge
    maxAge
    isActivelyHiring
    isHot
    isCoverLetterMandatory
    isEducationRequiredForCandidate
    isLocationRequiredForCandidate
    shouldShowSalary
    shouldShowBenefits
    benefits
    externalApplyURL
    fraudReportFlag
    resumeRequiredStatus
    CityId
    CountryCode
    company {
      id
      name
      logo
      status
      isVIP
      IndustryId
      website
      address
      size
      descriptionJsonString
      photosJsonString
      socialMediaSitesJsonString
      isApprovedToTalentHunt
      industry {
        id
        name
        __typename
      }
      verificationTier {
        type
        __typename
      }
      __typename
    }
    country {
      code
      name
      __typename
    }
    city {
      id
      name
      __typename
    }
    citySubDivision {
      id
      name
      __typename
    }
    location {
      id
      name
      formattedName
      level
      administrativeLevelName
      latitude
      longitude
      slug
      parents {
        CountryCode
        id
        name
        formattedName
        level
        administrativeLevelName
        slug
        parents {
          formattedName
          level
          slug
          __typename
        }
        __typename
      }
      __typename
    }
    hierarchicalJobCategory {
      HierarchicalJobCategoryId
      level
      name
      parents {
        HierarchicalJobCategoryId
        level
        name
        __typename
      }
      __typename
    }
    skills {
      mustHave
      skill {
        id
        name
        __typename
      }
      __typename
    }
    salaries {
      id
      salaryType
      salaryMode
      maxAmount
      minAmount
      CurrencyCode
      __typename
    }
    salaryEstimate {
      minAmount
      maxAmount
      CurrencyCode
      __typename
    }
    creator {
      id
      name
      image
      online
      lastSeen
      isHighResponseRate
      __typename
    }
    creatorResponseTime
    canUserApplyWithReason {
      canApply
      reason
      __typename
    }
    oneTapApply {
      isEligible
      __typename
    }
    expInfo
    traceInfo
    __typename
  }
}"""
    
    GRAPHQL_QUERY = """query searchJobsV3($data: JobSearchConditionInput!) {
  searchJobsV3(data: $data) {
    jobsInPage {
      id
      title
      workArrangementOption
      status
      createdAt
      updatedAt
      isActivelyHiring
      isHot
      isApplied
      shouldShowSalary
      educationLevel
      type
      fraudReportFlag
      salaryEstimate {
        minAmount
        maxAmount
        CurrencyCode
        __typename
      }
      company {
        id
        name
        logo
        status
        isVIP
        IndustryId
        industry {
          id
          name
          __typename
        }
        verificationTier {
          type
          __typename
        }
        __typename
      }
      citySubDivision {
        id
        name
        __typename
      }
      city {
        id
        name
        __typename
      }
      country {
        code
        name
        __typename
      }
      salaries {
        id
        salaryType
        salaryMode
        maxAmount
        minAmount
        CurrencyCode
        __typename
      }
      location {
        id
        name
        formattedName
        level
        administrativeLevelName
        latitude
        longitude
        slug
        parents {
          CountryCode
          id
          name
          formattedName
          level
          administrativeLevelName
          slug
          parents {
            formattedName
            level
            slug
            __typename
          }
          __typename
        }
        __typename
      }
      minYearsOfExperience
      maxYearsOfExperience
      source
      hierarchicalJobCategory {
        id
        level
        name
        children {
          name
          level
          id
          __typename
        }
        parents {
          id
          level
          name
          __typename
        }
        __typename
      }
      skills {
        skill {
          id
          name
          __typename
        }
        mustHave
        __typename
      }
      traceInfo
      __typename
    }
    expInfo
    hasMore
    __typename
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
        self.session = requests.Session()
        
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        
        if proxies:
            self.session.proxies.update(proxies)
    
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
            
            response = self.session.post(
                f"{self.BASE_URL}?op=searchJobsV3",
                json=payload,
                timeout=self.timeout
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
            
        except requests.RequestException as e:
            logger.error(f"Error fetching Glints page {page_num}: {e}")
            return None, False
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Glints response: {e}")
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
            
            response = self.session.post(
                f"{self.BASE_URL}?op=getJobDetailsById",
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            
            job_detail = data.get("data", {}).get("getJobById", {})
            
            if not job_detail:
                logger.warning(f"No detail data found for job {job_id}")
                return None
            
            logger.debug(f"Successfully fetched detail for job {job_id}")
            return job_detail
            
        except requests.RequestException as e:
            logger.error(f"Error fetching Glints job detail {job_id}: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing Glints detail response for {job_id}: {e}")
            return None
    
    def close(self):
        """Close the session."""
        self.session.close()
