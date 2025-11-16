"""
Centralized field mapping utilities for standardizing job data across all sources.

This module provides consistent mapping functions for experience level, job type,
and education fields to ensure uniform output regardless of the source (Loker.id,
JobStreet, Glints).
"""

import re
from typing import Optional


class FieldMappers:
    """Centralized mappers for standardizing job fields across all sources."""
    
    @staticmethod
    def normalize_experience(experience_input: str) -> str:
        """
        Normalize experience level to standardized output format.
        
        Mapping rules:
        - "0-2 Tahun" → "Entry Level"
        - "1-3 Tahun" → "Junior"
        - "3-5 Tahun" → "Mid Level"
        - "5-10 Tahun" → "Senior"
        - "7-10 Tahun" → "Lead / Manager"
        - Contains "10" or more → "Executive"
        
        Args:
            experience_input: Raw experience string (e.g., "1-3 Tahun", "5-10 Tahun")
            
        Returns:
            Standardized experience level string
        """
        if not experience_input:
            return "Junior"
        
        exp = experience_input.strip()
        
        # Direct mapping for exact matches
        direct_mapping = {
            "0-2 Tahun": "Entry Level",
            "1-3 Tahun": "Junior",
            "3-5 Tahun": "Mid Level",
            "5-10 Tahun": "Senior",
            "7-10 Tahun": "Lead / Manager"
        }
        
        if exp in direct_mapping:
            return direct_mapping[exp]
        
        # Handle cases like "10-12 Tahun", "10 > Tahun", "> 10 Tahun", etc.
        if re.search(r'10\s*[-–>]', exp) or re.search(r'>\s*10', exp):
            return "Executive"
        
        # Extract numbers to determine range
        numbers = re.findall(r'\d+', exp)
        if numbers:
            try:
                first_num = int(numbers[0])
                
                # Range-based mapping
                if first_num >= 10:
                    return "Executive"
                elif first_num >= 7:
                    return "Lead / Manager"
                elif first_num >= 5:
                    return "Senior"
                elif first_num >= 3:
                    return "Mid Level"
                elif first_num >= 1:
                    return "Junior"
                else:  # 0 years
                    return "Entry Level"
            except ValueError:
                pass
        
        # Default fallback
        return "Junior"
    
    @staticmethod
    def normalize_job_type(job_type_input: Optional[str]) -> str:
        """
        Normalize job type to standardized output format.
        
        Standardized values:
        - Contract
        - Freelance
        - Full Time
        - Internship
        - Part Time
        
        Args:
            job_type_input: Raw job type string
            
        Returns:
            Standardized job type string
        """
        if not job_type_input:
            return "Full Time"
        
        job_type = job_type_input.strip().upper()
        
        # Comprehensive mapping covering variations from all sources
        mapping = {
            # Full Time variations
            "FULL TIME": "Full Time",
            "FULLTIME": "Full Time",
            "FULL_TIME": "Full Time",
            "FULL-TIME": "Full Time",
            "PENUH WAKTU": "Full Time",
            "WAKTU PENUH": "Full Time",
            
            # Part Time variations
            "PART TIME": "Part Time",
            "PARTTIME": "Part Time",
            "PART_TIME": "Part Time",
            "PART-TIME": "Part Time",
            "PARUH WAKTU": "Part Time",
            "WAKTU PARUH": "Part Time",
            
            # Contract variations
            "CONTRACT": "Contract",
            "KONTRAK": "Contract",
            
            # Freelance variations
            "FREELANCE": "Freelance",
            "FREELANCER": "Freelance",
            
            # Internship variations
            "INTERNSHIP": "Internship",
            "INTERN": "Internship",
            "MAGANG": "Internship",
            "TRAINEE": "Internship"
        }
        
        # Direct mapping
        if job_type in mapping:
            return mapping[job_type]
        
        # Fuzzy matching for partial matches
        if "FULL" in job_type or "PENUH" in job_type:
            return "Full Time"
        elif "PART" in job_type or "PARUH" in job_type:
            return "Part Time"
        elif "CONTRACT" in job_type or "KONTRAK" in job_type:
            return "Contract"
        elif "FREELANCE" in job_type:
            return "Freelance"
        elif "INTERN" in job_type or "MAGANG" in job_type:
            return "Internship"
        
        # Default
        return "Full Time"
    
    @staticmethod
    def normalize_education(education_input: Optional[str]) -> str:
        """
        Normalize education level to standardized output format.
        
        Mapping rules:
        - SMA/SMK variations → "SMA/SMK/Sederajat"
        - D1 → "D1"
        - D2 → "D2"
        - D3 → "D3"
        - D4 → "D4"
        - D1-D4 combined → "D1, D2, D3, D4"
        - S1/Bachelor → "S1"
        - S2/Master → "S2"
        - S3/Doctorate → "S3"
        - Default → "SMA/SMK/Sederajat"
        
        Args:
            education_input: Raw education string
            
        Returns:
            Standardized education level string
        """
        if not education_input:
            return "SMA/SMK/Sederajat"
        
        edu = education_input.strip().upper()
        
        # Direct mapping for exact matches
        direct_mapping = {
            "SMA": "SMA/SMK/Sederajat",
            "SMK": "SMA/SMK/Sederajat",
            "SMA/SMK": "SMA/SMK/Sederajat",
            "SMA / SMK": "SMA/SMK/Sederajat",
            "SMA / SMK / STM": "SMA/SMK/Sederajat",
            "HIGH SCHOOL": "SMA/SMK/Sederajat",
            "HIGH_SCHOOL": "SMA/SMK/Sederajat",
            "D1": "D1",
            "D2": "D2",
            "D3": "D3",
            "D4": "D4",
            "S1": "S1",
            "S2": "S2",
            "S3": "S3",
            "SARJANA": "S1",
            "SARJANA / S1": "S1",
            "BACHELOR": "S1",
            "MASTER": "S2",
            "MASTER / S2": "S2",
            "DOCTORATE": "S3",
            "DOCTOR": "S3",
            "DOCTOR / S3": "S3",
            "PHD": "S3"
        }
        
        if edu in direct_mapping:
            return direct_mapping[edu]
        
        # Handle combined diploma levels like "D1-D4", "DIPLOMA/D1/D2/D3"
        if re.search(r'D[1-4]\s*[-/]\s*D[1-4]', edu) or "DIPLOMA" in edu:
            return "D1, D2, D3, D4"
        
        # Handle SMA/SMK variations with fuzzy matching
        if re.search(r'SMA|SMK', edu):
            return "SMA/SMK/Sederajat"
        
        # Handle specific diploma levels
        if "D1" in edu:
            return "D1"
        if "D2" in edu:
            return "D2"
        if "D3" in edu:
            return "D3"
        if "D4" in edu:
            return "D4"
        
        # Handle bachelor's variations
        if re.search(r'S1|SARJANA|BACHELOR', edu):
            return "S1"
        
        # Handle master's variations
        if re.search(r'S2|MASTER', edu):
            return "S2"
        
        # Handle doctorate variations
        if re.search(r'S3|DOCTOR|PHD|DOKTOR', edu):
            return "S3"
        
        # Default fallback
        return "SMA/SMK/Sederajat"
