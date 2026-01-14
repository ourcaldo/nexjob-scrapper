# Field Mapping Standardization - Implementation Summary

## Overview
Standardized the **experience level**, **job_type**, and **education** fields across all three job sources (Loker.id, JobStreet, Glints) to ensure consistent output regardless of the source.

## Centralized Mapping System

Created a new centralized utility: **`src/transformers/field_mappers.py`**

This module provides three standardized mapping functions that all transformers now use:
- `FieldMappers.normalize_experience()`
- `FieldMappers.normalize_job_type()`
- `FieldMappers.normalize_education()`

---

## 1. Experience Level Standardization

### Output Values

All sources now output these standardized experience levels:

| Input Range | Output |
|-------------|--------|
| 0-2 Tahun | **Entry Level** |
| 1-3 Tahun | **Junior** |
| 3-5 Tahun | **Mid Level** |
| 5-10 Tahun | **Senior** |
| 7-10 Tahun | **Lead / Manager** |
| 10+ Tahun | **Executive** |

### Mapping Logic

```python
def normalize_experience(experience_input: str) -> str:
    # Direct mapping
    direct_mapping = {
        "0-2 Tahun": "Entry Level",
        "1-3 Tahun": "Junior",
        "3-5 Tahun": "Mid Level",
        "5-10 Tahun": "Senior",
        "7-10 Tahun": "Lead / Manager"
    }
    
    # Handle "10-12 Tahun", "10 > Tahun", etc.
    if re.search(r'10\s*[-–>]', exp):
        return "Executive"
    
    # Extract numbers and map to ranges
    # Falls back to "Junior" if unknown
```

### How Each Source Maps

**Loker.id:**
- API provides: `"1-2 Tahun"`, `"3-5 Tahun"`, `"5-10 Tahun"`, etc.
- Now normalized through: `FieldMappers.normalize_experience()`

**JobStreet:**
- HTML scraped data provides: `"1-3 Tahun"`, `"3-5 Tahun"`, etc.
- Now normalized through: `FieldMappers.normalize_experience()`

**Glints:**
- API provides: `minYearsOfExperience=3`, `maxYearsOfExperience=5`
- Converted to: `"3-5 Tahun"`
- Then normalized through: `FieldMappers.normalize_experience()`

---

## 2. Job Type Standardization

### Output Values

All sources now output these standardized job types:

- **Contract**
- **Freelance**
- **Full Time**
- **Internship**
- **Part Time**

### Mapping Logic

```python
def normalize_job_type(job_type_input: str) -> str:
    mapping = {
        # Full Time variations
        "FULL TIME": "Full Time",
        "FULL_TIME": "Full Time",
        "PENUH WAKTU": "Full Time",
        
        # Part Time variations
        "PART TIME": "Part Time",
        "PART_TIME": "Part Time",
        "PARUH WAKTU": "Part Time",
        
        # Other types
        "CONTRACT": "Contract",
        "FREELANCE": "Freelance",
        "INTERNSHIP": "Internship",
        "MAGANG": "Internship"
    }
    
    # Fuzzy matching for partial matches
    # Default: "Full Time"
```

### How Each Source Maps

**Loker.id:**
- API provides: `"Full Time"`, `"Part Time"`, `"Contract"`, etc.
- Now normalized through: `FieldMappers.normalize_job_type()`

**JobStreet:**
- API provides: `["Full time"]` (array, take first)
- Now normalized through: `FieldMappers.normalize_job_type()`

**Glints:**
- API provides: `"FULL_TIME"`, `"PART_TIME"`, `"CONTRACT"`, etc.
- Now normalized through: `FieldMappers.normalize_job_type()`

---

## 3. Education Level Standardization

### Output Values

All sources now output these standardized education levels:

| Input | Output |
|-------|--------|
| SMA, SMK, High School | **SMA/SMK/Sederajat** |
| D1 | **D1** |
| D2 | **D2** |
| D3 | **D3** |
| D4 | **D4** |
| D1-D4 (range), Diploma (generic) | **D1** (fallback) |
| S1, Bachelor, Sarjana | **S1** |
| S2, Master | **S2** |
| S3, Doctorate, PhD | **S3** |
| Unknown/Empty | **SMA/SMK/Sederajat** (default) |

### Mapping Logic

```python
def normalize_education(education_input: str) -> str:
    # Direct mapping
    direct_mapping = {
        "SMA": "SMA/SMK/Sederajat",
        "SMK": "SMA/SMK/Sederajat",
        "D1": "D1",
        "D2": "D2",
        "D3": "D3",
        "D4": "D4",
        "S1": "S1",
        "BACHELOR": "S1",
        "S2": "S2",
        "MASTER": "S2",
        "S3": "S3",
        "DOCTORATE": "S3"
    }
    
    # Handle ranges like "D1-D4" or generic "DIPLOMA" → fallback to D1
    if re.search(r'D[1-4]\s*[-–/]\s*D[1-4]', edu):
        return "D1"
    if edu == "DIPLOMA":
        return "D1"
    
    # Check for specific levels (substring match)
    if "D4" in edu: return "D4"
    if "D3" in edu: return "D3"
    if "D2" in edu: return "D2"
    if "D1" in edu: return "D1"
    
    # Fuzzy matching for SMA/SMK variations
    # Default: "SMA/SMK/Sederajat"
```

### How Each Source Maps

**Loker.id:**
- API provides: `"SMA / SMK / STM"`, `"Diploma/D1/D2/D3"`, `"Sarjana / S1"`, etc.
- Now normalized through: `FieldMappers.normalize_education()`

**JobStreet:**
- HTML scraped provides: `"SMA/SMK"`, `"D3"`, `"S1"`, etc.
- Now normalized through: `FieldMappers.normalize_education()`

**Glints:**
- API provides: `"HIGH_SCHOOL"`, `"DIPLOMA"`, `"BACHELOR"`, `"MASTER"`, etc.
- Now normalized through: `FieldMappers.normalize_education()`

---

## Files Modified

### 1. Created New File
**`src/transformers/field_mappers.py`** (NEW)
- Centralized mapping utilities
- ~200 lines of standardization logic
- Comprehensive regex patterns and fuzzy matching

### 2. Updated Transformers

**`src/transformers/loker_transformer.py`**
- Added import: `from src.transformers.field_mappers import FieldMappers`
- Removed old `map_education()` method
- Removed old `map_experience()` method
- Updated `transform_job()` to use centralized mappers

**`src/transformers/jobstreet_transformer.py`**
- Added import: `from src.transformers.field_mappers import FieldMappers`
- Updated `transform_job()` to use centralized mappers
- Extracts raw values, then normalizes through `FieldMappers`

**`src/transformers/glints_transformer.py`**
- Added import: `from src.transformers.field_mappers import FieldMappers`
- Removed old `map_education()` method
- Removed old `map_job_type()` method
- Renamed `map_experience()` to `map_experience_from_years()` (only converts years to range)
- Updated `transform_job()` to use centralized mappers

---

## Benefits

### ✅ Consistency Across Sources
- All three sources (Loker, JobStreet, Glints) now produce identical output formats
- Easier to filter, search, and analyze jobs regardless of source

### ✅ Single Source of Truth
- All mapping logic in one file (`field_mappers.py`)
- Easy to update mapping rules globally
- No duplicate logic across transformers

### ✅ Comprehensive Coverage
- Handles Indonesian and English variations
- Fuzzy matching for typos and formatting differences
- Safe defaults for unknown values

### ✅ Future-Proof
- Adding new job sources just requires using `FieldMappers`
- Changing mapping rules only requires editing one file
- Easy to extend with new experience levels or education types

---

## Testing Examples

### Experience Level

| Source | Raw Input | Normalized Output |
|--------|-----------|-------------------|
| Loker.id | "1-2 Tahun" | Junior |
| Loker.id | "5-10 Tahun" | Senior |
| JobStreet | "7-10 Tahun" | Lead / Manager |
| Glints | min=10, max=15 → "10-15 Tahun" | Executive |

### Job Type

| Source | Raw Input | Normalized Output |
|--------|-----------|-------------------|
| Loker.id | "Full Time" | Full Time |
| JobStreet | "Full time" | Full Time |
| Glints | "FULL_TIME" | Full Time |
| Glints | "INTERNSHIP" | Internship |

### Education

| Source | Raw Input | Normalized Output |
|--------|-----------|-------------------|
| Loker.id | "SMA / SMK / STM" | SMA/SMK/Sederajat |
| Loker.id | "Diploma/D1/D2/D3" | D1 (fallback) |
| Loker.id | "D3" | D3 |
| JobStreet | "S1" | S1 |
| Glints | "BACHELOR" | S1 |
| Glints | "HIGH_SCHOOL" | SMA/SMK/Sederajat |
| Any | "D1-D4" | D1 (fallback) |
| Any | "DIPLOMA" | D1 (fallback) |

---

## Backward Compatibility

✅ **Fully backward compatible** - No breaking changes to existing data

- Existing stored jobs remain unchanged
- New jobs will use standardized format
- Both old and new formats can coexist in storage

---

## Migration Notes

**No migration needed** - This is a forward-only change:
1. Existing jobs in storage keep their current values
2. New jobs scraped from now on will use standardized values
3. Over time, all active jobs will naturally migrate to the new format

**To force migration** (optional):
1. Re-scrape all sources with the new transformers
2. Duplicate checking will skip existing jobs
3. Only new jobs will be added with standardized values

---

## Next Steps (Optional Enhancements)

Future improvements to consider:

1. **Add validation tests**
   - Unit tests for each mapper function
   - Test edge cases and fuzzy matching

2. **Add configuration**
   - Allow custom mappings via config file
   - Support different languages/locales

3. **Add logging**
   - Log when fuzzy matching is used
   - Track which raw values are most common

4. **Data quality reporting**
   - Report unmapped values to improve coverage
   - Statistics on mapping success rates

---

**Implementation Date:** November 15, 2025  
**Files Created:** 1 new file (`field_mappers.py`)  
**Files Modified:** 3 transformers  
**Total Lines Changed:** ~300 lines
