"""
JobStreet job data transformation module for normalizing and mapping fields.
"""

import uuid
from typing import Dict, Any, List
import re
from src.transformers.content_cleaner import ContentCleaner


class JobStreetTransformer:
    """Transforms and normalizes job data from JobStreet format."""
    
    def __init__(self):
        """Initialize the transformer with a content cleaner."""
        self.content_cleaner = ContentCleaner()
    
    @staticmethod
    def extract_job_id(job: Dict[str, Any]) -> str:
        """
        Extract job ID from JobStreet data (can be in two locations).
        
        Args:
            job: Job data from JobStreet API
            
        Returns:
            Job ID as string
        """
        return str(job.get("id") or job.get("solMetadata", {}).get("jobId", ""))
    
    @staticmethod
    def extract_company_name(job: Dict[str, Any]) -> str:
        """
        Extract company name from JobStreet data.
        
        Args:
            job: Job data from JobStreet API
            
        Returns:
            Company name
        """
        return job.get("employer", {}).get("name") or job.get("companyName", "")
    
    @staticmethod
    def extract_category(job: Dict[str, Any]) -> str:
        """
        Extract job category from JobStreet classifications.
        
        Args:
            job: Job data from JobStreet API
            
        Returns:
            Job category/classification
        """
        classifications = job.get("classifications", [])
        if classifications:
            return classifications[0].get("classification", {}).get("description", "")
        return ""
    
    @staticmethod
    def extract_location(job: Dict[str, Any]) -> tuple[str, str]:
        """
        Extract province and city from JobStreet location seoHierarchy.
        
        Args:
            job: Job data from JobStreet API
            
        Returns:
            Tuple of (province, city)
        """
        locations = job.get("locations", [])
        if not locations:
            return ("", "")
        
        location = locations[0]
        seo_hierarchy = location.get("seoHierarchy", [])
        
        province = seo_hierarchy[1].get("contextualName", "") if len(seo_hierarchy) > 1 else ""
        city = seo_hierarchy[0].get("contextualName", "") if seo_hierarchy else location.get("label", "")
        
        if not province and "," in city:
            city, province = city.split(",", 1)
            province = province.strip()
            city = city.strip()
        
        return (province, city)
    
    @staticmethod
    def extract_work_type(job: Dict[str, Any]) -> str:
        """
        Extract work type from JobStreet data.
        
        Args:
            job: Job data from JobStreet API
            
        Returns:
            Work type (e.g., "Full time", "Part time")
        """
        work_types = job.get("workTypes", [])
        return work_types[0] if work_types else "Full time"
    
    @staticmethod
    def extract_work_arrangement(job: Dict[str, Any]) -> str:
        """
        Extract and normalize work arrangement from JobStreet data.
        
        Args:
            job: Job data from JobStreet API
            
        Returns:
            Normalized work policy (e.g., "On-site Working", "Remote Working")
        """
        work_arrangements = job.get("workArrangements", {}).get("data", [])
        
        if work_arrangements:
            arrangement = work_arrangements[0].get("label", {}).get("text", "On-site")
        else:
            arrangement = "On-site"
        
        if "remote" in arrangement.lower():
            return "Remote Working"
        elif "hybrid" in arrangement.lower():
            return "Hybrid Working"
        else:
            return "On-site Working"
    
    @staticmethod
    def parse_salary(salary_label: str) -> tuple[int, int]:
        """
        Parse salary string to extract min and max values.
        
        Args:
            salary_label: Salary string from JobStreet (often empty)
            
        Returns:
            Tuple of (salary_min, salary_max) in rupiah
        """
        if not salary_label or salary_label.lower() in ["negotiable", "negosiasi"]:
            return (0, 0)
        
        salary_pattern = r"(\d[\d,]*)"
        matches = re.findall(salary_pattern, salary_label)
        
        if len(matches) >= 2:
            try:
                min_val = int(matches[0].replace(",", ""))
                max_val = int(matches[1].replace(",", ""))
                return (min_val, max_val)
            except ValueError:
                pass
        
        return (0, 0)
    
    @staticmethod
    def infer_job_level(job: Dict[str, Any]) -> str:
        """
        Infer job level from title or roleId.
        
        Args:
            job: Job data from JobStreet API
            
        Returns:
            Job level (e.g., "Entry Level", "Mid Level", "Senior Level")
        """
        title = job.get("title", "").lower()
        role_id = job.get("roleId", "").lower()
        
        if any(keyword in title for keyword in ["senior", "manager", "lead"]):
            return "Senior Level"
        elif any(keyword in title for keyword in ["director", "head", "chief"]):
            return "Management"
        elif any(keyword in title for keyword in ["junior", "entry", "trainee"]):
            return "Entry Level"
        else:
            return "Mid Level"
    
    def transform_job(self, job: Dict[str, Any], headers: List[str]) -> List[str]:
        """
        Transforms a job dictionary from JobStreet into a row for Google Sheets.
        
        JobStreet data comes from two sources:
        1. Search API - basic job info
        2. HTML scraping - detailed description, education, experience, gender
        
        Args:
            job: Combined job data (API + HTML scraped data)
            headers: List of column headers from Google Sheets
            
        Returns:
            List of values matching the header columns
        """
        job_id = self.extract_job_id(job)
        company_name = self.extract_company_name(job)
        category = self.extract_category(job)
        province, city = self.extract_location(job)
        work_type = self.extract_work_type(job)
        work_arrangement = self.extract_work_arrangement(job)
        salary_min, salary_max = self.parse_salary(job.get("salaryLabel", ""))
        level = self.infer_job_level(job)
        
        content = job.get("content", "")
        if content:
            content = self.content_cleaner.clean_html(content)
        
        pendidikan = job.get("pendidikan", "Tanpa Minimal Pendidikan")
        pengalaman = job.get("pengalaman", "1-3 Tahun")
        gender = job.get("gender", "Laki-laki/Perempuan")
        
        tag_items = []
        if category:
            tag_items.append(category)
        if pendidikan and pendidikan != "Tanpa Minimal Pendidikan":
            tag_items.append(pendidikan)
        if level:
            tag_items.append(level)
        if work_type:
            tag_items.append(work_type)
        if work_arrangement:
            tag_items.append(work_arrangement)
        tag_combined = ", ".join(tag_items)
        
        job_dict = {
            "internal_id": str(uuid.uuid4()),
            "source_id": job_id,
            "job_source": "JobStreet",
            "link": f"https://id.jobstreet.com/id/job/{job_id}",
            "company_name": company_name,
            "job_category": category,
            "title": job.get("title", ""),
            "content": content,
            "province": province,
            "city": city,
            "experience": pengalaman,
            "job_type": work_type,
            "level": level,
            "salary_min": str(salary_min),
            "salary_max": str(salary_max),
            "education": pendidikan,
            "work_policy": work_arrangement,
            "industry": category,
            "gender": gender,
            "tags": tag_combined
        }
        
        return [job_dict.get(col.strip(), "") for col in headers]
