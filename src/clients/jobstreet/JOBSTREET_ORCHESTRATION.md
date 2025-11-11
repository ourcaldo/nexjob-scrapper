# 🔍 JobStreet Orchestration Deep Dive

Complete guide to understanding how we scrape, extract, transform, and store job data from JobStreet.

---

## 📊 **Data Flow Overview**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    JOBSTREET SEARCH API ENDPOINT                    │
│  https://id.jobstreet.com/api/jobsearch/v5/search?                 │
│  siteKey=ID&page={N}&pageSize=30                                   │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ JSON Response with Basic Job Data
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      JOBSTREET CLIENT                               │
│  • Fetches paginated job listings from search API                  │
│  • Extracts basic info (id, title, company, location, etc.)        │
│  • Returns: List[Dict] - Array of job objects with IDs             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ FOR each job_id
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   JOB DETAIL PAGE SCRAPER                           │
│  URL: https://id.jobstreet.com/id/job/{job_id}                     │
│  • Fetches HTML page (SSR - Server Side Rendered)                  │
│  • Parses HTML with BeautifulSoup                                  │
│  • Extracts detailed job description from HTML                     │
│  • Merges with search API data                                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Complete job data
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   JOB TRANSFORMER                                   │
│  1. Extract raw fields from combined data                          │
│  2. Normalize/map values (education, salary, experience)           │
│  3. Clean HTML content                                             │
│  4. Build structured job dictionary                                │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ List[str] - Row data
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   GOOGLE SHEETS CLIENT                              │
│  • Appends row to spreadsheet                                      │
│  • Respects rate limits                                            │
│  • Checks for duplicates (by job ID)                               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎯 **What We Extract from JobStreet**

### **STEP 1: Search API Response Structure**

The search API (`/api/jobsearch/v5/search`) returns basic job information:

```json
{
  "data": [
    {
      "id": "81990353",
      "title": "Marketing Agency Relation Executive Tangerang Cikupa",
      "companyName": "BFI Finance Indonesia",
      "advertiser": {
        "id": "60338610",
        "description": "PT. BFI FINANCE INDONESIA, Tbk"
      },
      "employer": {
        "id": "413801",
        "name": "BFI Finance Indonesia",
        "companyId": "168556908920494"
      },
      "classifications": [
        {
          "classification": {
            "id": "6008",
            "description": "Marketing & Communications"
          },
          "subclassification": {
            "id": "6016",
            "description": "Marketing Communications"
          }
        }
      ],
      "locations": [
        {
          "label": "Tangerang District, Banten",
          "countryCode": "ID",
          "seoHierarchy": [
            {
              "contextualName": "Tangerang District Banten"
            },
            {
              "contextualName": "Banten"
            }
          ]
        }
      ],
      "workTypes": ["Full time"],
      "workArrangements": {
        "data": [
          {
            "id": "1",
            "label": {
              "text": "On-site"
            }
          }
        ]
      },
      "salaryLabel": "",
      "teaser": "Memiliki pengalaman 1 tahun dibidang sales/marketing...",
      "listingDate": "2025-02-11T05:05:44Z",
      "roleId": "relationship-executive",
      "solMetadata": {
        "jobId": "81990353",
        "token": "0~abe5a08c-0b5f-4905-bf8a-34df057454e3"
      }
    }
  ],
  "totalCount": 57944,
  "solMetadata": {
    "pageSize": 30,
    "pageNumber": 1,
    "totalJobCount": 57944
  }
}
```

### **STEP 2: Job Detail Page (HTML Scraping)**

URL Pattern: `https://id.jobstreet.com/id/job/{job_id}`

**Important**: JobStreet's individual job pages are **Server-Side Rendered (SSR)**, meaning:
- ❌ No API endpoint for detailed job information
- ✅ Must scrape HTML to extract job description
- ✅ HTML contains structured data with `<ul>`, `<li>`, `<strong>`, etc.

**What to Extract from HTML:**
1. **Job Description** - Detailed requirements and responsibilities
2. **Minimum Qualifications** - Education, experience requirements
3. **Additional Details** - Skills, benefits, etc.

**Example HTML Structure:**
```html
<strong>Job Description</strong><br />
<ul>
  <li>Mencari dan merekrut BA (Business Agent)/Agen/Mitra baru...</li>
  <li>Menjaga hubungan baik dengan BA...</li>
  <li>Melakukan koordinasi dengan supervisor...</li>
  <li>Bertanggung jawab atas pencapaian target bulanan.</li>
</ul>

<strong>Minimum Qualifications</strong><br />
<ul>
  <li><p>Berusia maksimal 35 tahun.</p></li>
  <li><p>Pendidikan min SMA (berpengalaman) segala jurusan.</p></li>
  <li><p>Fresh graduate S1 dipersilakan melamar.</p></li>
  <li><p>Memiliki pengalaman 1 tahun dibidang sales/marketing...</p></li>
  <li><p>Menyukai pekerjaan lapangan.</p></li>
</ul>
```

---

## 🔄 **Field-by-Field Extraction & Mapping**

### 1. **Basic Identification Fields**

| **Field** | **Source** | **Transformation** | **Output Column** |
|-----------|------------|-------------------|------------------|
| Job ID | `data[i]["id"]` OR `data[i]["solMetadata"]["jobId"]` | Convert to string | `id` |
| Source | Hardcoded | Always "JobStreet" | `sumber_lowongan` |
| Direct Link | `job_id` | Build URL: `https://id.jobstreet.com/id/job/{job_id}` | `link` |

**Code:**
```python
# Extract ID (can be from two locations)
job_id = str(job.get("id") or job.get("solMetadata", {}).get("jobId"))

"id": job_id
"sumber_lowongan": "JobStreet"
"link": f"https://id.jobstreet.com/id/job/{job_id}"
```

**⚠️ Important:** JobStreet has the ID in two places:
- `data[i]["id"]` - Top-level ID
- `data[i]["solMetadata"]["jobId"]` - Metadata ID

Both should have the same value, but always check both for safety.

---

### 2. **Company & Job Title**

| **Field** | **Source** | **Transformation** | **Output Column** |
|-----------|------------|-------------------|------------------|
| Company Name | `job["companyName"]` OR `job["employer"]["name"]` | Direct copy, prefer employer.name | `company_name` |
| Job Title | `job["title"]` | Direct copy | `title` |
| Category | `job["classifications"][0]["classification"]["description"]` | First classification | `kategori_pekerjaan` |

**Code:**
```python
"company_name": job.get("employer", {}).get("name") or job.get("companyName", "")
"title": job.get("title", "")

# Extract category from nested classifications
classifications = job.get("classifications", [])
category = classifications[0]["classification"]["description"] if classifications else ""
"kategori_pekerjaan": category
```

---

### 3. **Location Fields** 📍

**Source:** `job["locations"]` (array)

JobStreet locations are structured differently from Loker.id:

```python
# locations[0]["seoHierarchy"] contains nested location info
location = job.get("locations", [{}])[0]

# Extract from seoHierarchy
seo_hierarchy = location.get("seoHierarchy", [])

# Province is typically the second item in hierarchy
province = seo_hierarchy[1]["contextualName"] if len(seo_hierarchy) > 1 else ""

# City/District is typically the first item
city = seo_hierarchy[0]["contextualName"] if seo_hierarchy else location.get("label", "")
```

**Example:**
```json
"locations": [
  {
    "label": "Tangerang District, Banten",
    "seoHierarchy": [
      {"contextualName": "Tangerang District Banten"},  // City
      {"contextualName": "Banten"}                       // Province
    ]
  }
]
```

**Mapping:**
```python
"lokasi_provinsi": "Banten"              # From seoHierarchy[1]
"lokasi_kota": "Tangerang District"      # From seoHierarchy[0] or label
```

---

### 4. **Work Type & Arrangements** 💼

**Work Type:** `job["workTypes"]` (array)

```python
work_types = job.get("workTypes", [])
tipe_pekerjaan = work_types[0] if work_types else "Full time"
# Examples: "Full time", "Part time", "Contract"
```

**Work Policy:** `job["workArrangements"]["data"]`

```python
work_arrangements = job.get("workArrangements", {}).get("data", [])

if work_arrangements:
    arrangement_label = work_arrangements[0].get("label", {}).get("text", "On-site")
else:
    arrangement_label = "On-site"

# Map to kebijakan_kerja
# "On-site" → "On-site Working"
# "Remote" → "Remote Working"
# "Hybrid" → "Hybrid Working"
```

---

### 5. **Salary Information** 💰

**Source:** `job["salaryLabel"]` (string)

**Challenge:** JobStreet often doesn't display salary in search results.

```python
salary_label = job.get("salaryLabel", "")

if salary_label:
    # Parse salary range (format varies)
    # Examples:
    # "Rp 4,000,000 - Rp 5,000,000"
    # "Negotiable"
    # Extract min/max as integers
    salary_min, salary_max = parse_salary(salary_label)
else:
    # No salary specified
    salary_min = 0
    salary_max = 0
```

**Normalization (similar to Loker.id):**
```python
# Extract numbers from salary string
# "Rp 4,000,000 - Rp 5,000,000" → salary_min: 4000000, salary_max: 5000000
# "Negotiable" or "" → salary_min: 0, salary_max: 0
```

---

### 6. **Job Content (HTML from Detail Page)** 📝

**Source:** HTML scraping from `https://id.jobstreet.com/id/job/{job_id}`

**Extraction Strategy:**

#### Step 1: Fetch HTML Page
```python
import requests
from bs4 import BeautifulSoup

url = f"https://id.jobstreet.com/id/job/{job_id}"
response = requests.get(url)
soup = BeautifulSoup(response.content, "html.parser")
```

#### Step 2: Extract Job Description Sections
JobStreet embeds job description in the HTML body. Look for:
- `<strong>` tags for section headers (e.g., "Job Description", "Minimum Qualifications")
- `<ul>` and `<li>` tags for lists
- `<p>` tags for paragraphs

**Parsing Logic:**
```python
# Find all sections with job content
# Typically found in divs with specific data-automation attributes
job_content_sections = soup.find_all("section", {"data-automation": "jobDescription"})

# Extract HTML content
content_html = ""
for section in job_content_sections:
    content_html += str(section)
```

#### Step 3: Clean & Structure HTML

Use the **ContentCleaner** (same as Loker.id) to:
1. Parse HTML
2. Normalize headings (`<strong>` → `<h2>`)
3. Format lists properly
4. Remove duplicates
5. Output clean, structured HTML

**Example Transformation:**

**Input (Raw HTML):**
```html
<strong>Job Description</strong><br />
<ul>
  <li>Mencari dan merekrut BA baru...</li>
  <li>Menjaga hubungan baik dengan BA...</li>
</ul>
<strong>Minimum Qualifications</strong><br />
<ul>
  <li><p>Berusia maksimal 35 tahun.</p></li>
  <li><p>Pendidikan min SMA...</p></li>
</ul>
```

**Output (Cleaned HTML):**
```html
<h2>Job Description</h2>
<ul>
  <li>Mencari dan merekrut BA baru...</li>
  <li>Menjaga hubungan baik dengan BA...</li>
</ul>
<h2>Minimum Qualifications</h2>
<ul>
  <li>Berusia maksimal 35 tahun.</li>
  <li>Pendidikan min SMA...</li>
</ul>
```

---

### 7. **Education & Experience (EXTRACTED FROM HTML)** 🎓

**Challenge:** Unlike Loker.id, JobStreet doesn't provide structured education/experience data in the API.

**Solution:** Extract from job description HTML using pattern matching.

#### Education Extraction:
```python
# Search for education keywords in HTML content
education_keywords = {
    "SMA": "SMA/SMK",
    "SMK": "SMA/SMK",
    "D1": "D1-D4",
    "D2": "D1-D4",
    "D3": "D1-D4",
    "D4": "D1-D4",
    "S1": "S1",
    "Sarjana": "S1",
    "S2": "S2",
    "Master": "S2",
    "S3": "S3",
    "Doctor": "S3"
}

# Extract from HTML text
text = soup.get_text()
for keyword, normalized in education_keywords.items():
    if keyword in text:
        pendidikan = normalized
        break
else:
    pendidikan = "Tanpa Minimal Pendidikan"
```

#### Experience Extraction:
```python
# Search for experience patterns
# Examples: "1 tahun", "2-3 tahun", "minimal 1 tahun"

import re
experience_pattern = r"(\d+)[-\s]*(?:tahun|years?)"
matches = re.findall(experience_pattern, text, re.IGNORECASE)

if matches:
    # Normalize based on years
    years = int(matches[0])
    if years <= 2:
        pengalaman = "1-3 Tahun"
    elif years <= 5:
        pengalaman = "3-5 Tahun"
    elif years <= 10:
        pengalaman = "5-10 Tahun"
    else:
        pengalaman = "Lebih dari 10 Tahun"
else:
    pengalaman = "1-3 Tahun"  # Default
```

---

### 8. **Job Level** 📊

**Source:** Not directly available in JobStreet API

**Options:**
1. Infer from `roleId` field (e.g., "relationship-executive")
2. Extract from job title (e.g., "Senior", "Junior", "Manager")
3. Default to "Mid Level"

```python
role_id = job.get("roleId", "")
title = job.get("title", "").lower()

# Check title for level indicators
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

### 9. **Industry** 🏭

**Source:** `job["classifications"][0]["classification"]["description"]`

```python
classifications = job.get("classifications", [])
if classifications:
    industry = classifications[0]["classification"]["description"]
else:
    industry = ""

# Examples: "Marketing & Communications", "Information Technology"
```

---

### 10. **Gender Requirement**

**Source:** HTML content (not in API)

**Extraction:**
```python
# Search for gender keywords in HTML
text = soup.get_text().lower()

if "laki-laki" in text and "perempuan" in text:
    gender = "Laki-laki/Perempuan"
elif "laki-laki" in text:
    gender = "Laki-laki"
elif "perempuan" in text:
    gender = "Perempuan"
else:
    gender = "Laki-laki/Perempuan"  # Default (no restriction)
```

---

### 11. **Tags (COMBINED)** 🏷️

**Source:** Multiple fields combined

```python
tag_items = []

# Add category
if category:
    tag_items.append(category)

# Add education
if pendidikan and pendidikan != "Tanpa Minimal Pendidikan":
    tag_items.append(pendidikan)

# Add level
if level:
    tag_items.append(level)

# Add work type
if tipe_pekerjaan:
    tag_items.append(tipe_pekerjaan)

# Add work arrangement
if kebijakan_kerja:
    tag_items.append(kebijakan_kerja)

tag_combined = ", ".join(tag_items)
```

**Example Output:**
```
"Marketing & Communications, S1, Mid Level, Full time, On-site Working"
```

---

## 📋 **Final Google Sheets Columns**

The final row data contains these columns (in order):

1. **id** - Job ID from API
2. **sumber_lowongan** - Always "JobStreet"
3. **link** - Direct URL to job posting
4. **company_name** - Company name (from employer.name)
5. **kategori_pekerjaan** - Job category (from classifications)
6. **title** - Job title
7. **content** - Cleaned HTML description (from HTML scraping)
8. **lokasi_provinsi** - Province (from seoHierarchy)
9. **lokasi_kota** - City/District (from seoHierarchy)
10. **pengalaman** - Normalized experience level (extracted from HTML)
11. **tipe_pekerjaan** - Job type (Full time, Part time, etc.)
12. **level** - Job level (inferred from title/roleId)
13. **salary_min** - Minimum salary in Rupiah (integer, often 0)
14. **salary_max** - Maximum salary in Rupiah (integer, often 0)
15. **pendidikan** - Normalized education requirement (extracted from HTML)
16. **kebijakan_kerja** - Work policy (On-site/Remote/Hybrid)
17. **industry** - Industry sector (from classifications)
18. **gender** - Gender requirement (extracted from HTML)
19. **tag** - Combined tags

---

## 🔁 **Complete Orchestration Flow**

### ScraperService.scrape_jobstreet()

```python
1. Initialize Sheets Client
   └─→ Load service account credentials
   └─→ Connect to Google Sheets
   └─→ Load existing job IDs (for duplicate detection)

2. Scrape All Pages from Search API
   page_num = 1
   WHILE page_num <= total_pages:
       │
       ├─→ JobStreetClient.fetch_search_page(page_num)
       │   └─→ GET https://id.jobstreet.com/api/jobsearch/v5/search
       │   └─→ Params: siteKey=ID, page={page_num}, pageSize=30
       │   └─→ Returns: data[] array with basic job info
       │
       ├─→ FOR each job in data[]:
       │   │
       │   ├─→ Extract job_id from job["id"] or job["solMetadata"]["jobId"]
       │   │
       │   ├─→ Check if job_id already exists in Google Sheets
       │   │   └─→ If exists: SKIP (duplicate)
       │   │   └─→ If new: CONTINUE
       │   │
       │   ├─→ JobStreetClient.fetch_job_detail(job_id)
       │   │   └─→ GET https://id.jobstreet.com/id/job/{job_id}
       │   │   └─→ Parse HTML with BeautifulSoup
       │   │   └─→ Extract job description HTML
       │   │   └─→ Extract education/experience from text
       │   │   └─→ Extract gender from text
       │   │   └─→ Return: job_detail dict
       │   │
       │   ├─→ Merge search data + detail data
       │   │   └─→ combined_job = {**search_job, **detail_job}
       │   │
       │   ├─→ JobTransformer.transform_job(combined_job, headers)
       │   │   ├─→ map_education()
       │   │   ├─→ map_salary()
       │   │   ├─→ map_experience()
       │   │   ├─→ map_work_policy()
       │   │   ├─→ ContentCleaner.clean_html()
       │   │   └─→ Build job_dict
       │   │   └─→ Return row_data[]
       │   │
       │   └─→ SheetsClient.append_row(row_data)
       │       └─→ RateLimiter.check("write")
       │       └─→ sheet.append_row()
       │       └─→ Add job_id to existing_ids set
       │   
       │   └─→ Sleep 2 seconds (to avoid rate limiting on HTML fetches)
       │
       ├─→ Calculate total_pages from solMetadata.totalJobCount
       ├─→ Sleep 1 second (page_delay)
       └─→ page_num++

3. Wait 60 minutes before next cycle
```

---

## ⚙️ **Key Differences from Loker.id**

| **Aspect** | **Loker.id** | **JobStreet** |
|-----------|-------------|---------------|
| **Data Source** | Single API endpoint | Search API + HTML scraping |
| **Job Details** | Complete in API response | Must scrape HTML page |
| **Education** | Structured field in API | Extract from HTML text |
| **Experience** | Structured field in API | Extract from HTML text |
| **Salary** | Always provided in API | Often missing/hidden |
| **Work Policy** | Boolean `is_remote` | Structured `workArrangements` |
| **Location** | Simple array | Nested `seoHierarchy` |
| **Requests per Job** | 1 request | 2 requests (search + detail) |
| **Parsing Complexity** | Low (JSON only) | High (JSON + HTML) |

---

## 🎯 **Pagination Logic**

JobStreet provides pagination metadata:

```json
"solMetadata": {
  "pageSize": 30,
  "pageNumber": 1,
  "totalJobCount": 57944
}
```

**Calculate total pages:**
```python
total_jobs = response["solMetadata"]["totalJobCount"]
page_size = response["solMetadata"]["pageSize"]
total_pages = (total_jobs + page_size - 1) // page_size

# Example: 57944 jobs / 30 per page = 1932 pages
```

**Loop through all pages:**
```python
for page_num in range(1, total_pages + 1):
    jobs = fetch_search_page(page_num)
    # Process jobs...
```

---

## ⚠️ **Important Considerations**

### 1. **Rate Limiting**
- JobStreet requires **2 requests per job** (search + detail)
- Add delays between requests to avoid being blocked
- Recommended: 2-3 seconds between HTML fetch requests

### 2. **HTML Structure Changes**
- JobStreet's HTML structure may change over time
- Use flexible selectors (e.g., look for `<strong>` tags for sections)
- Implement error handling for missing elements

### 3. **Missing Data**
- Salary often not displayed in search results
- Education/experience must be extracted from free text
- Some fields may be completely missing

### 4. **Data Quality**
- HTML extraction is less reliable than API data
- Implement validation for extracted values
- Use defaults when extraction fails

---

## 📊 **Data Normalization Benefits**

### Education Extraction Examples

**Input (HTML Text):**
```
"Pendidikan min SMA (berpengalaman) segala jurusan"
"Fresh graduate S1 dipersilakan melamar"
```

**Output (Normalized):**
```
"SMA/SMK"  # Detected "SMA"
"S1"       # Detected "S1"
```

### Experience Extraction Examples

**Input (HTML Text):**
```
"Memiliki pengalaman 1 tahun dibidang sales/marketing"
"Minimal 3 tahun pengalaman"
"Fresh graduate dipersilakan melamar"
```

**Output (Normalized):**
```
"1-3 Tahun"   # Detected "1 tahun"
"3-5 Tahun"   # Detected "3 tahun"
"1-3 Tahun"   # Default for fresh graduate
```

---

## 🎯 **Summary**

| **Component** | **Purpose** | **Output** |
|--------------|-------------|------------|
| **JobStreetClient (Search)** | Fetch basic job data from search API | `List[Dict]` - Array with job IDs and basic info |
| **JobStreetClient (Detail)** | Fetch HTML and extract job description | `Dict` - Job detail data from HTML |
| **JobTransformer** | Normalize & map fields, merge search + detail | `List[str]` - Row data for spreadsheet |
| **ContentCleaner** | Clean HTML descriptions | Clean, formatted HTML string |
| **SheetsClient** | Store in Google Sheets | Appended row with duplicate check |
| **RateLimiter** | Respect API quotas | Automatic delays when needed |

**Total Fields Extracted:** 19 columns per job  
**Normalization Applied:** Education, Salary, Experience, Work Policy  
**HTML Cleaning:** Automatic formatting of lists and headings  
**Duplicate Detection:** By job ID (column A)  
**Pagination:** Automatic based on totalJobCount  
**Requests per Job:** 2 (search API + HTML detail page)

---

## 🚀 **Implementation Roadmap**

1. ✅ Create JobStreet client for search API
2. ✅ Implement HTML scraping for job details
3. ✅ Create transformer for JobStreet data structure
4. ✅ Implement education/experience extraction from HTML
5. ✅ Add location parsing for seoHierarchy
6. ✅ Integrate with existing Google Sheets client
7. ✅ Add rate limiting for HTML requests
8. ✅ Test with sample jobs
9. ✅ Deploy and monitor

---

**End of JobStreet Orchestration Document**
