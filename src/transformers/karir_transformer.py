"""
Karir.com job data transformation module for normalizing and mapping fields.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from src.transformers.field_mappers import FieldMappers


logger = logging.getLogger(__name__)


class KarirTransformer:
    """Transforms and normalizes job data from Karir.com REST API format."""

    # Karir.com workplace values → unified work_policy
    _WORKPLACE_MAP = {
        "REMOTE": "Remote Working",
        "WFH": "Remote Working",
        "HYBRID": "Hybrid Working",
        "ONSITE": "On-site Working",
        "ON-SITE": "On-site Working",
    }

    @staticmethod
    def _experience_years_to_range(years: Optional[int]) -> str:
        """
        Convert an integer years-of-experience value returned by Karir.com
        into a range string that FieldMappers.normalize_experience() understands.

        Args:
            years: Work experience in years (e.g. 1, 3, 5)

        Returns:
            Range string e.g. "1-3 Tahun"
        """
        if not years or years <= 0:
            return "0-2 Tahun"
        elif years <= 2:
            return "1-3 Tahun"
        elif years <= 4:
            return "3-5 Tahun"
        elif years <= 6:
            return "5-10 Tahun"
        elif years <= 9:
            return "7-10 Tahun"
        else:
            return "10-12 Tahun"

    @staticmethod
    def _map_work_policy(workplace: Optional[str]) -> str:
        """
        Map Karir.com workplace string to unified work_policy.

        Karir.com returns "Tidak Disebutkan" when unspecified — default to On-site.

        Args:
            workplace: Raw workplace string from detail endpoint

        Returns:
            Unified work_policy string
        """
        if not workplace or workplace.strip().upper() in ("TIDAK DISEBUTKAN", ""):
            return "On-site Working"

        key = workplace.strip().upper()
        return KarirTransformer._WORKPLACE_MAP.get(key, "On-site Working")

    @staticmethod
    def _best_education(degrees: Optional[List[str]]) -> str:
        """
        Pick the highest education level from the degrees array and normalize it.

        Karir.com returns degrees ordered highest-first (e.g. ["S1", "D3", "SMA"]).

        Args:
            degrees: List of degree strings from detail endpoint

        Returns:
            Normalized education string
        """
        if not degrees:
            return FieldMappers.normalize_education(None)
        # First element is highest qualification — use it
        return FieldMappers.normalize_education(degrees[0])

    @staticmethod
    def build_job_content(detail: Dict[str, Any]) -> str:
        """
        Build unified HTML job content from the detail endpoint fields.

        Combines responsibilities (deskripsi pekerjaan) and requirements
        (kualifikasi) into a single HTML string.

        Args:
            detail: Job detail dict from fetch_job_detail()

        Returns:
            Combined HTML string
        """
        parts = []

        responsibilities = (detail.get("responsibilities") or "").strip()
        requirements = (detail.get("requirements") or "").strip()

        if responsibilities:
            parts.append("<h2>Deskripsi Pekerjaan</h2>")
            parts.append(responsibilities)

        if requirements:
            parts.append("<h2>Kualifikasi</h2>")
            parts.append(requirements)

        return "\n".join(parts)

    def transform_job(
        self,
        list_job: Dict[str, Any],
        detail: Dict[str, Any],
        headers: List[str],
    ) -> List[Any]:
        """
        Transform a Karir.com job (list + detail) into a storage row.

        Args:
            list_job: Job dict from the search/list endpoint
            detail:   Job dict from the detail endpoint
            headers:  Column order from the storage backend

        Returns:
            Ordered list of values matching the storage schema
        """
        job_id = str(list_job.get("id", ""))
        title = (list_job.get("job_position") or "").strip()
        company_name = (list_job.get("company_name") or "").strip()

        # Salary — already integers from both endpoints; list endpoint is sufficient
        salary_min = list_job.get("salary_lower") or 0
        salary_max = list_job.get("salary_upper") or 0

        # Detail fields
        city = (detail.get("location") or "").strip()
        link = (detail.get("opportunities_link") or "").strip()
        content = self.build_job_content(detail)

        job_type = FieldMappers.normalize_job_type(detail.get("job_type"))
        work_policy = self._map_work_policy(detail.get("workplace"))
        education = self._best_education(detail.get("degrees"))

        experience_range = self._experience_years_to_range(detail.get("work_experience"))
        experience = FieldMappers.normalize_experience(experience_range)

        # job_levels is a list e.g. ["Pemula / Staf"]
        job_levels = detail.get("job_levels") or []
        level = job_levels[0] if job_levels else ""

        # job_functions is a list e.g. ["Layanan Pelanggan", "Komunikasi"]
        job_functions = detail.get("job_functions") or []
        job_category = job_functions[0] if job_functions else ""
        tags = ", ".join(job_functions) if job_functions else ""

        company_info = detail.get("company") or {}
        industry = (company_info.get("industry_name") or "").strip()

        row = {
            "internal_id": str(uuid.uuid4()),
            "source_id": job_id,
            "job_source": "Karir.com",
            "link": link,
            "company_name": company_name,
            "job_category": job_category,
            "title": title,
            "content": content,
            "province": "",
            "city": city,
            "experience": experience,
            "job_type": job_type,
            "level": level,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "education": education,
            "work_policy": work_policy,
            "industry": industry,
            "gender": "",
            "tags": tags,
        }

        return [row.get(h, "") for h in headers]
