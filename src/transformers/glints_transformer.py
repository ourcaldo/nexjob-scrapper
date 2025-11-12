"""
Glints job data transformation module for normalizing and mapping fields.
"""

import uuid
from typing import Dict, Any, List, Optional

logger = None
try:
    import logging
    logger = logging.getLogger(__name__)
except:
    pass


class GlintsTransformer:
    """Transforms and normalizes job data from Glints GraphQL API format."""
    
    @staticmethod
    def map_education(education_level: str) -> str:
        """
        Normalizes education requirements from Glints format.
        
        Args:
            education_level: Raw education value from Glints API
                            (e.g., "DIPLOMA", "BACHELOR", "MASTER", "DOCTORATE")
            
        Returns:
            Normalized education string matching our standard format
        """
        mapping = {
            "HIGH_SCHOOL": "SMA/SMK",
            "DIPLOMA": "D1-D4",
            "BACHELOR": "S1",
            "MASTER": "S2",
            "DOCTORATE": "S3",
            "PHD": "S3"
        }
        
        if not education_level:
            return "Tanpa Minimal Pendidikan"
        
        return mapping.get(education_level.upper(), "Tanpa Minimal Pendidikan")
    
    @staticmethod
    def map_experience(min_years: int, max_years: int) -> str:
        """
        Normalizes experience requirements from Glints min/max years.
        
        Args:
            min_years: Minimum years of experience
            max_years: Maximum years of experience
            
        Returns:
            Normalized experience string
        """
        if max_years is None or max_years == 0:
            max_years = min_years if min_years else 3
        
        if min_years is None or min_years == 0:
            min_years = 0
        
        avg_years = (min_years + max_years) / 2
        
        if avg_years <= 2:
            return "1-3 Tahun"
        elif avg_years <= 5:
            return "3-5 Tahun"
        elif avg_years <= 10:
            return "5-10 Tahun"
        else:
            return "Lebih dari 10 Tahun"
    
    @staticmethod
    def map_work_arrangement(work_arrangement: str) -> str:
        """
        Normalizes work arrangement from Glints format.
        
        Args:
            work_arrangement: Raw work arrangement value
                            (e.g., "ONSITE", "REMOTE", "HYBRID")
            
        Returns:
            Normalized work policy string
        """
        mapping = {
            "ONSITE": "On-site Working",
            "REMOTE": "Remote Working",
            "HYBRID": "Hybrid Working",
            "WORK_FROM_HOME": "Remote Working"
        }
        
        if not work_arrangement:
            return "On-site Working"
        
        return mapping.get(work_arrangement.upper(), "On-site Working")
    
    @staticmethod
    def map_job_type(job_type: str) -> str:
        """
        Normalizes job type from Glints format.
        
        Args:
            job_type: Raw job type value (e.g., "FULL_TIME", "PART_TIME", "CONTRACT")
            
        Returns:
            Normalized job type string
        """
        mapping = {
            "FULL_TIME": "Full Time",
            "PART_TIME": "Part Time",
            "CONTRACT": "Contract",
            "INTERNSHIP": "Internship",
            "FREELANCE": "Freelance"
        }
        
        if not job_type:
            return "Full Time"
        
        return mapping.get(job_type.upper(), "Full Time")
    
    @staticmethod
    def extract_location(job: Dict[str, Any]) -> tuple[str, str]:
        """
        Extract province and city from Glints location data.
        
        Glints has hierarchical location with parents array.
        Structure: District (level 4) -> City (level 3) -> Province (level 2) -> Country (level 1)
        
        Args:
            job: Job data from Glints API
            
        Returns:
            Tuple of (province, city)
        """
        location = job.get("location", {})
        
        if not location:
            return ("", "")
        
        city_name = ""
        province_name = ""
        
        parents = location.get("parents", [])
        
        for parent in parents:
            level = parent.get("level")
            admin_level = parent.get("administrativeLevelName", "")
            
            if level == 2 or admin_level == "Province":
                province_name = parent.get("name", "") or parent.get("formattedName", "")
            elif level == 3 or admin_level == "City":
                city_name = parent.get("name", "") or parent.get("formattedName", "")
        
        if not city_name:
            district_name = location.get("name", "") or location.get("formattedName", "")
            if location.get("level") == 4 or location.get("administrativeLevelName") == "District":
                city_name = district_name
        
        return (province_name, city_name)
    
    @staticmethod
    def extract_salary(job: Dict[str, Any]) -> tuple[int, int]:
        """
        Extract salary min and max from Glints salary data.
        
        Args:
            job: Job data from Glints API
            
        Returns:
            Tuple of (salary_min, salary_max) in rupiah
        """
        salaries = job.get("salaries", [])
        
        if not salaries:
            return (0, 0)
        
        basic_salary = salaries[0]
        
        min_amount = basic_salary.get("minAmount", 0)
        max_amount = basic_salary.get("maxAmount", 0)
        
        return (int(min_amount or 0), int(max_amount or 0))
    
    @staticmethod
    def extract_skills(job: Dict[str, Any]) -> str:
        """
        Extract and format skills from Glints skills array.
        
        Args:
            job: Job data from Glints API
            
        Returns:
            Comma-separated string of skill names
        """
        skills_data = job.get("skills", [])
        
        if not skills_data:
            return ""
        
        must_have_skills = []
        optional_skills = []
        
        for skill_item in skills_data:
            skill_name = skill_item.get("skill", {}).get("name", "")
            if not skill_name:
                continue
            
            if skill_item.get("mustHave", False):
                must_have_skills.append(skill_name)
            else:
                optional_skills.append(skill_name)
        
        all_skills = must_have_skills + optional_skills
        
        return ", ".join(all_skills[:10])
    
    @staticmethod
    def build_job_description(job: Dict[str, Any]) -> str:
        """
        Build a formatted job description from Glints data.
        
        Since Glints API doesn't provide detailed HTML description,
        we construct a structured description from available fields.
        
        Args:
            job: Job data from Glints API
            
        Returns:
            HTML formatted job description
        """
        parts = []
        
        parts.append("<h2>Job Information</h2>")
        
        company = job.get("company", {})
        if company:
            industry = company.get("industry", {}).get("name", "")
            if industry:
                parts.append(f"<p><strong>Industry:</strong> {industry}</p>")
        
        min_exp = job.get("minYearsOfExperience", 0) or 0
        max_exp = job.get("maxYearsOfExperience", 0) or 0
        if min_exp or max_exp:
            parts.append(f"<p><strong>Experience Required:</strong> {min_exp}-{max_exp} years</p>")
        
        education = job.get("educationLevel", "")
        if education:
            parts.append(f"<p><strong>Education Level:</strong> {education}</p>")
        
        skills_data = job.get("skills", [])
        if skills_data:
            parts.append("<h2>Required Skills</h2>")
            parts.append("<ul>")
            for skill_item in skills_data[:15]:
                skill_name = skill_item.get("skill", {}).get("name", "")
                if skill_name:
                    must_have = " (Required)" if skill_item.get("mustHave") else ""
                    parts.append(f"<li>{skill_name}{must_have}</li>")
            parts.append("</ul>")
        
        category = job.get("hierarchicalJobCategory", {})
        if category:
            cat_name = category.get("name", "")
            if cat_name:
                parts.append(f"<p><strong>Job Category:</strong> {cat_name}</p>")
        
        return "\n".join(parts)
    
    @staticmethod
    def infer_job_level(job: Dict[str, Any]) -> str:
        """
        Infer job level from title and experience requirements.
        
        Args:
            job: Job data from Glints API
            
        Returns:
            Job level (e.g., "Entry Level", "Mid Level", "Senior Level")
        """
        title = job.get("title", "").lower()
        min_exp = job.get("minYearsOfExperience", 0) or 0
        max_exp = job.get("maxYearsOfExperience", 0) or 0
        
        if any(keyword in title for keyword in ["director", "head", "chief", "vp", "vice president"]):
            return "Management"
        elif any(keyword in title for keyword in ["senior", "sr", "lead"]):
            return "Senior Level"
        elif any(keyword in title for keyword in ["junior", "jr", "entry", "trainee", "intern"]):
            return "Entry Level"
        elif max_exp <= 2:
            return "Entry Level"
        elif max_exp <= 5:
            return "Mid Level"
        elif max_exp > 5:
            return "Senior Level"
        else:
            return "Mid Level"
    
    def transform_job(self, job: Dict[str, Any], headers: List[str]) -> Optional[List[str]]:
        """
        Transforms a job dictionary from Glints into a row for Google Sheets.
        
        IMPORTANT: Only transforms jobs with status === "OPEN"
        
        Args:
            job: Job data from Glints GraphQL API
            headers: List of column headers from Google Sheets
            
        Returns:
            List of values matching the header columns, or None if job is not OPEN
        """
        if job.get("status") != "OPEN":
            if logger:
                logger.debug(f"Skipping job {job.get('id')} - status is {job.get('status')}, not OPEN")
            return None
        
        job_id = job.get("id", "")
        company_name = job.get("company", {}).get("name", "")
        title = job.get("title", "")
        
        category_data = job.get("hierarchicalJobCategory", {})
        category = category_data.get("name", "")
        
        province, city = self.extract_location(job)
        
        work_arrangement = self.map_work_arrangement(job.get("workArrangementOption", ""))
        job_type = self.map_job_type(job.get("type", ""))
        
        min_years = job.get("minYearsOfExperience", 0)
        max_years = job.get("maxYearsOfExperience", 0)
        experience = self.map_experience(min_years, max_years)
        
        education = self.map_education(job.get("educationLevel", ""))
        
        salary_min, salary_max = self.extract_salary(job)
        
        level = self.infer_job_level(job)
        
        content = self.build_job_description(job)
        
        industry = job.get("company", {}).get("industry", {}).get("name", "")
        
        tag_items = []
        if category:
            tag_items.append(category)
        if education and education != "Tanpa Minimal Pendidikan":
            tag_items.append(education)
        if level:
            tag_items.append(level)
        if job_type:
            tag_items.append(job_type)
        if work_arrangement:
            tag_items.append(work_arrangement)
        if industry:
            tag_items.append(industry)
        
        tag_combined = ", ".join(tag_items)
        
        job_dict = {
            "internal_id": str(uuid.uuid4()),
            "source_id": job_id,
            "job_source": "Glints",
            "link": f"https://glints.com/id/opportunities/jobs/{job_id}",
            "company_name": company_name,
            "job_category": category,
            "title": title,
            "content": content,
            "province": province,
            "city": city,
            "experience": experience,
            "job_type": job_type,
            "level": level,
            "salary_min": str(salary_min),
            "salary_max": str(salary_max),
            "education": education,
            "work_policy": work_arrangement,
            "industry": industry,
            "gender": "Laki-laki/Perempuan",
            "tags": tag_combined
        }
        
        return [job_dict.get(col.strip(), "") for col in headers]
