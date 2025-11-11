# JobStreet Data Field Mapping

Quick reference for mapping JobStreet API/HTML data to Google Sheets columns.

---

## Search API → Google Sheets Mapping

| **Google Sheets Column** | **JobStreet Source** | **Extraction Method** | **Notes** |
|--------------------------|----------------------|----------------------|-----------|
| `id` | `data[i]["id"]` or `data[i]["solMetadata"]["jobId"]` | Direct | Job ID can be in two locations |
| `sumber_lowongan` | Hardcoded | `"JobStreet"` | Always constant |
| `link` | `job_id` | `f"https://id.jobstreet.com/id/job/{job_id}"` | Build from ID |
| `company_name` | `data[i]["employer"]["name"]` or `data[i]["companyName"]` | Direct | Prefer employer.name |
| `kategori_pekerjaan` | `data[i]["classifications"][0]["classification"]["description"]` | Nested extraction | First classification |
| `title` | `data[i]["title"]` | Direct | Job title |
| `content` | HTML scraping | See HTML Extraction section | From detail page |
| `lokasi_provinsi` | `data[i]["locations"][0]["seoHierarchy"][1]["contextualName"]` | Nested extraction | Province from seoHierarchy |
| `lokasi_kota` | `data[i]["locations"][0]["seoHierarchy"][0]["contextualName"]` or `label` | Nested extraction | City/district |
| `pengalaman` | HTML scraping | Pattern matching from text | Extract years, normalize to ranges |
| `tipe_pekerjaan` | `data[i]["workTypes"][0]` | Direct | "Full time", "Part time", etc. |
| `level` | Job title or `roleId` | Inference | Look for "Senior", "Junior", etc. |
| `salary_min` | `data[i]["salaryLabel"]` | Parse string to integer | Often empty/0 |
| `salary_max` | `data[i]["salaryLabel"]` | Parse string to integer | Often empty/0 |
| `pendidikan` | HTML scraping | Keyword matching | Extract from job description |
| `kebijakan_kerja` | `data[i]["workArrangements"]["data"][0]["label"]["text"]` | Nested extraction | "On-site", "Remote", "Hybrid" |
| `industry` | `data[i]["classifications"][0]["classification"]["description"]` | Nested extraction | Same as category |
| `gender` | HTML scraping | Keyword matching | Extract from job description |
| `tag` | Combined fields | Concatenation | Join category, education, level, etc. |

---

## HTML Extraction Patterns

### Job Description Content
```python
# Find sections with <strong> headers
for strong in soup.find_all("strong"):
    section_header = strong.get_text()  # e.g., "Job Description"
    # Get following <ul>, <ol>, <p> elements
    # Continue until next <strong> tag
```

### Education Keywords
```python
keywords = {
    "S3", "DOCTOR" → "S3",
    "S2", "MASTER" → "S2",
    "S1", "SARJANA" → "S1",
    "D1", "D2", "D3", "D4", "DIPLOMA" → "D1-D4",
    "SMA", "SMK", "STM" → "SMA/SMK"
}
# Search in uppercase text
```

### Experience Patterns
```python
patterns = [
    r"(\d+)\s*[-–]\s*(\d+)\s*tahun"  # "2-3 tahun"
    r"minimal\s*(\d+)\s*tahun"        # "minimal 1 tahun"
    r"(\d+)\s*tahun"                  # "1 tahun"
]

# Normalize ranges:
# <= 2 years → "1-3 Tahun"
# <= 5 years → "3-5 Tahun"
# <= 10 years → "5-10 Tahun"
# > 10 years → "Lebih dari 10 Tahun"
```

### Gender Keywords
```python
text = soup.get_text().lower()

# Check for keywords:
"laki-laki" or "pria" → Male
"perempuan" or "wanita" → Female
Both → "Laki-laki/Perempuan"
None → "Laki-laki/Perempuan" (default)
```

---

## Example JSON → Sheets Transformation

### Input (Search API Response)
```json
{
  "id": "81990353",
  "title": "Marketing Agency Relation Executive",
  "companyName": "BFI Finance Indonesia",
  "employer": {
    "name": "BFI Finance Indonesia"
  },
  "classifications": [{
    "classification": {
      "description": "Marketing & Communications"
    }
  }],
  "locations": [{
    "label": "Tangerang District, Banten",
    "seoHierarchy": [
      {"contextualName": "Tangerang District Banten"},
      {"contextualName": "Banten"}
    ]
  }],
  "workTypes": ["Full time"],
  "workArrangements": {
    "data": [{
      "label": {"text": "On-site"}
    }]
  },
  "salaryLabel": ""
}
```

### Output (Google Sheets Row)
```python
[
  "81990353",                           # id
  "JobStreet",                          # sumber_lowongan
  "https://id.jobstreet.com/id/job/81990353",  # link
  "BFI Finance Indonesia",              # company_name
  "Marketing & Communications",         # kategori_pekerjaan
  "Marketing Agency Relation Executive", # title
  "<h2>Job Description</h2><ul>...</ul>",  # content (from HTML)
  "Banten",                             # lokasi_provinsi
  "Tangerang District",                 # lokasi_kota
  "1-3 Tahun",                          # pengalaman (from HTML)
  "Full time",                          # tipe_pekerjaan
  "Mid Level",                          # level (inferred)
  "0",                                  # salary_min
  "0",                                  # salary_max
  "SMA/SMK",                            # pendidikan (from HTML)
  "On-site Working",                    # kebijakan_kerja
  "Marketing & Communications",         # industry
  "Laki-laki/Perempuan",               # gender (from HTML)
  "Marketing & Communications, SMA/SMK, Mid Level, Full time, On-site Working"  # tag
]
```

---

## Two-Step Data Collection Process

### Step 1: Search API Call
```python
GET https://id.jobstreet.com/api/jobsearch/v5/search
Params: siteKey=ID, page=1, pageSize=30

Returns:
- Basic job info (id, title, company, location, etc.)
- Pagination metadata (totalJobCount, pageSize)
```

### Step 2: HTML Detail Scraping
```python
GET https://id.jobstreet.com/id/job/{job_id}

Parse HTML to extract:
- Job description content
- Education requirements
- Experience requirements
- Gender requirements
```

### Step 3: Merge & Transform
```python
combined_data = {
    **search_api_data,
    **html_scraped_data
}

transformed_row = JobTransformer.transform_job(combined_data, headers)
```

---

## Special Handling Requirements

### 1. Location Parsing
```python
# JobStreet uses nested seoHierarchy
location = job["locations"][0]
province = location["seoHierarchy"][1]["contextualName"]  # Province
city = location["seoHierarchy"][0]["contextualName"]      # City

# Fallback to label if seoHierarchy is missing
if not province:
    province = location.get("label", "").split(",")[-1].strip()
```

### 2. Work Arrangements
```python
# JobStreet uses structured workArrangements
arrangements = job["workArrangements"]["data"]
if arrangements:
    work_policy = arrangements[0]["label"]["text"]
    # Map: "On-site" → "On-site Working"
    #      "Remote" → "Remote Working"
    #      "Hybrid" → "Hybrid Working"
```

### 3. Job Level Inference
```python
title = job["title"].lower()

if "senior" in title or "manager" in title:
    level = "Senior Level"
elif "junior" in title or "entry" in title:
    level = "Entry Level"
elif "director" in title or "head" in title:
    level = "Management"
else:
    level = "Mid Level"  # Default
```

---

## Rate Limiting Recommendations

- **Search API**: 1-2 second delay between pages
- **HTML Detail Pages**: 2-3 second delay between requests
- **Reason**: Avoid being rate-limited or blocked by JobStreet

```python
# Between search API calls
time.sleep(1)

# Between HTML scraping
time.sleep(2)
```

---

## Error Handling

### Missing Fields
```python
# Use .get() with defaults
company_name = job.get("employer", {}).get("name") or job.get("companyName", "")

# Handle empty arrays
locations = job.get("locations", [])
if locations:
    province = locations[0].get("seoHierarchy", [{}])[1].get("contextualName", "")
```

### HTML Parsing Failures
```python
try:
    content = extract_job_description(soup)
except Exception as e:
    logger.error(f"Failed to extract content: {e}")
    content = ""  # Use empty string as fallback
```

---

## Summary

- **Total API Requests per Job**: 2 (search + HTML detail)
- **Required Libraries**: `requests`, `beautifulsoup4`
- **Extraction Complexity**: Medium-High (JSON + HTML parsing)
- **Data Completeness**: Medium (some fields missing/inferred)
- **Reliability**: Medium (HTML structure may change)
