"""
Loker.id job data transformation module for normalizing and mapping fields.
"""

import uuid
from typing import Dict, Any, List
from src.transformers.content_cleaner import ContentCleaner


class LokerTransformer:
    """Transforms and normalizes job data from Loker.id format."""
    
    def __init__(self):
        """Initialize the transformer with a content cleaner."""
        self.content_cleaner = ContentCleaner()
    
    @staticmethod
    def map_education(val: str) -> str:
        """
        Normalizes education requirements from Loker.id format.
        
        Args:
            val: Raw education value from API
            
        Returns:
            Normalized education string
        """
        mapping = {
            "SMA / SMK / STM": "SMA/SMK",
            "Diploma/D1/D2/D3": "D1-D4",
            "Sarjana / S1": "S1",
            "Master / S2": "S2",
            "Doctor / S3": "S3"
        }
        return mapping.get(val, "Tanpa Minimal Pendidikan")
    
    @staticmethod
    def extract_salary_range(val: str) -> tuple[int, int]:
        """
        Extracts salary min and max from Loker.id salary string.
        
        Args:
            val: Raw salary value from API (e.g., "Rp.1 – 2 Juta")
            
        Returns:
            Tuple of (salary_min, salary_max) in rupiah
            Returns (0, 0) for negotiable or unknown salaries
        """
        if not val or val == "Negosiasi":
            return (0, 0)
        
        salary_mappings = {
            "Rp.1 – 2 Juta": (1000000, 2000000),
            "Rp.2 – 3 Juta": (2000000, 3000000),
            "Rp.3 – 4 Juta": (3000000, 4000000),
            "Rp.4 – 5 Juta": (4000000, 5000000),
            "Rp.5 – 6 Juta": (5000000, 6000000),
            "Rp.6 – 7 Juta": (6000000, 7000000),
            "Rp.7 – 8 Juta": (7000000, 8000000),
            "Rp.8 – 9 Juta": (8000000, 9000000),
            "Rp.9 – 10 Juta": (9000000, 10000000),
            "Rp.10 – 15 Juta": (10000000, 15000000),
            "Rp.15 – 20 Juta": (15000000, 20000000),
            "Rp.20 – 25 Juta": (20000000, 25000000),
        }
        
        if val in salary_mappings:
            return salary_mappings[val]
        
        return (0, 0)
    
    @staticmethod
    def map_experience(val: str) -> str:
        """
        Normalizes experience requirements from Loker.id format.
        
        Args:
            val: Raw experience value from API
            
        Returns:
            Normalized experience string
        """
        if not val:
            return "1-3 Tahun"
            
        if val == "1-2 Tahun":
            return "1-3 Tahun"
        elif val in ["2-3 Tahun", "3-4 Tahun", "4-5 Tahun"]:
            return "3-5 Tahun"
        elif any(x in val for x in ["5-6 Tahun", "6-10 Tahun", "7-10 Tahun", "8-10 Tahun"]):
            return "5-10 Tahun"
        elif "Tahun" in val:
            try:
                first_num = int(val.split("-")[0])
                if first_num > 10:
                    return "Lebih dari 10 Tahun"
            except (ValueError, IndexError):
                pass
        
        return "1-3 Tahun"
    
    @staticmethod
    def map_work_policy(val: bool) -> str:
        """
        Normalizes work policy information from Loker.id boolean.
        
        Args:
            val: Boolean indicating if job is remote
            
        Returns:
            Work policy string
        """
        return "Remote Working" if val else "On-site Working"
    
    def transform_job(self, job: Dict[str, Any], headers: List[str]) -> List[str]:
        """
        Transforms a job dictionary from Loker.id into a row for Google Sheets.
        
        Args:
            job: Job data from Loker.id API
            headers: List of column headers from Google Sheets
            
        Returns:
            List of values matching the header columns
        """
        pendidikan = self.map_education(job.get("education", ""))
        pengalaman = self.map_experience(job.get("job_experience", ""))
        kebijakan_kerja = self.map_work_policy(job.get("is_remote", False))
        salary_min, salary_max = self.extract_salary_range(job.get("job_salary", ""))
        content = self.content_cleaner.clean_html(job.get("content", ""))

        tag_items = []
        if job.get("category"):
            tag_items.append(job["category"])
        if pendidikan:
            tag_items.append(pendidikan)
        if job.get("level"):
            tag_items.append(job["level"]["name"])
        if job.get("tag"):
            tag_items.append(job["tag"]["name"])
        if kebijakan_kerja:
            tag_items.append(kebijakan_kerja)
        tag_combined = ", ".join(tag_items)

        job_dict = {
            "internal_id": str(uuid.uuid4()),
            "source_id": str(job["id"]),
            "job_source": "Loker.id",
            "link": f"https://www.loker.id/cari-lowongan-kerja?jobid={job['id']}",
            "company_name": job["company_name"],
            "job_category": job.get("category", ""),
            "title": job["title"],
            "content": content,
            "province": job["locations"][0]["name"] if job.get("locations") else "",
            "city": job["locations"][1]["name"] if len(job.get("locations", [])) > 1 else "",
            "experience": pengalaman,
            "job_type": job.get("job_type", ""),
            "level": job.get("level", {}).get("name", ""),
            "salary_min": str(salary_min),
            "salary_max": str(salary_max),
            "education": pendidikan,
            "work_policy": kebijakan_kerja,
            "industry": job["industries"][0]["name"] if job.get("industries") else "",
            "gender": job.get("gender", ""),
            "tags": tag_combined
        }

        return [job_dict.get(col.strip(), "") for col in headers]
