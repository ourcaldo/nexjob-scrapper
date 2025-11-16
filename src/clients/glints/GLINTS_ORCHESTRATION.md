# 🔍 Glints Orchestration Deep Dive

Complete guide to understanding how we scrape, extract, transform, and store job data from Glints using their GraphQL API.

---

## 📊 **Data Flow Overview**

```
┌─────────────────────────────────────────────────────────────────────┐
│               STEP 1: SEARCH API (searchJobsV3)                     │
│  https://glints.com/api/v2-alc/graphql?op=searchJobsV3             │
│  Method: POST with GraphQL query payload                           │
│  Returns: List of jobs with basic info + pagination                │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Job list with IDs
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│               STEP 2: DETAIL API (getJobDetailsById)                │
│  https://glints.com/api/v2-alc/graphql?op=getJobDetailsById        │
│  Method: POST with job ID in GraphQL payload                       │
│  Returns: Complete job details (description, benefits, etc.)       │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Complete job data (search + detail)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      GLINTS CLIENT                                  │
│  • Sends GraphQL POST requests with pagination (search)            │
│  • For each job, fetches detailed info (detail)                    │
│  • Combines search data + detail data                              │
│  • Checks hasMore field for pagination                             │
│  • Returns: List[Dict] - Array of combined job objects             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Complete combined job data
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   JOB TRANSFORMER                                   │
│  1. Filter: Only process jobs with status === "OPEN"               │
│  2. Extract raw fields from GraphQL response                       │
│  3. Normalize/map values (education, salary, experience)           │
│  4. Build structured HTML description from data                    │
│  5. Build structured job dictionary                                │
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

## 🎯 **What We Extract from Glints GraphQL API**

### GraphQL Request Structure

**Endpoint:** `https://glints.com/api/v2-alc/graphql?op=searchJobsV3`

**Method:** `POST`

**Headers:**
```json
{
  "Content-Type": "application/json",
  "Accept": "application/json",
  "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
```

**Payload:**
```json
{
  "operationName": "searchJobsV3",
  "variables": {
    "data": {
      "CountryCode": "ID",
      "includeExternalJobs": true,
      "pageSize": 20,
      "page": 1,
      "sortBy": "LATEST"
    }
  },
  "query": "query searchJobsV3($data: JobSearchConditionInput!) { ... }"
}
```

### GraphQL Response Structure

**Complete response includes:**
```json
{
  "data": {
    "searchJobsV3": {
      "__typename": "JobSearchResults",
      "hasMore": true,
      "jobsInPage": [
        {
          "id": "6693dbc2-1041-4a51-9985-c993fe9e83d8",
          "title": "Tax and Accounting Staff",
          "status": "OPEN",
          "type": "FULL_TIME",
          "workArrangementOption": "ONSITE",
          "educationLevel": "DIPLOMA",
          "minYearsOfExperience": 1,
          "maxYearsOfExperience": 3,
          "company": {
            "id": "660fdc8d-e505-4449-8800-d7c0aa236b54",
            "name": "PT.Semesta Sukses Nawasena",
            "industry": {
              "id": 116,
              "name": "Logistics and Supply Chain"
            }
          },
          "location": {
            "name": "Cilincing",
            "formattedName": "Cilincing",
            "level": 4,
            "administrativeLevelName": "District",
            "parents": [
              {
                "level": 3,
                "name": "Jakarta Utara",
                "administrativeLevelName": "City"
              },
              {
                "level": 2,
                "name": "DKI Jakarta",
                "administrativeLevelName": "Province"
              }
            ]
          },
          "salaries": [
            {
              "minAmount": 4400000,
              "maxAmount": 5500000,
              "CurrencyCode": "IDR",
              "salaryMode": "MONTH",
              "salaryType": "BASIC"
            }
          ],
          "skills": [
            {
              "mustHave": true,
              "skill": {
                "name": "Financial Analysis"
              }
            }
          ],
          "hierarchicalJobCategory": {
            "id": "5a4b25e8-b050-42d0-9e2e-c38edde0c897",
            "level": 3,
            "name": "Tax Accountant",
            "parents": [
              {
                "level": 1,
                "name": "Accounting"
              }
            ]
          },
          "createdAt": "2025-11-12T02:59:38.841000Z",
          "updatedAt": "2025-11-12T02:59:40.288000Z"
        }
      ],
      "expInfo": "..."
    }
  }
}
```

---

## ⚠️ **CRITICAL: Status Filtering**

**IMPORTANT:** Glints jobs have a `status` field that can be:
- `"OPEN"` - Active job posting (✅ SCRAPE THIS)
- `"CLOSED"` - Job posting closed (❌ SKIP)
- `"DRAFT"` - Not yet published (❌ SKIP)

**Filter Rule:**
```python
if job.get("status") != "OPEN":
    return None  # Skip this job
```

**Why This Matters:**
- Only OPEN jobs should be added to Google Sheets
- Closed/Draft jobs waste storage and confuse users
- Must check BEFORE transformation

---

## 🔄 **Field-by-Field Extraction & Mapping**

### 1. **Basic Identification Fields**

| **Field** | **Source** | **Transformation** | **Output Column** |
|-----------|------------|-------------------|------------------|
| Job ID | `job["id"]` | Direct copy as string | `source_id` |
| Internal ID | Generated | `uuid.uuid4()` | `internal_id` |
| Source | Hardcoded | Always "Glints" | `job_source` |
| Direct Link | `job["id"]` | Build URL: `https://glints.com/id/opportunities/jobs/{id}` | `link` |

**Code:**
```python
"source_id": job["id"]
"internal_id": str(uuid.uuid4())
"job_source": "Glints"
"link": f"https://glints.com/id/opportunities/jobs/{job['id']}"
```

---

### 2. **Company & Job Title**

| **Field** | **Source** | **Transformation** | **Output Column** |
|-----------|------------|-------------------|------------------|
| Company Name | `job["company"]["name"]` | Direct copy | `company_name` |
| Job Title | `job["title"]` | Direct copy | `title` |
| Category | `job["hierarchicalJobCategory"]["name"]` | Direct copy | `job_category` |
| Industry | `job["company"]["industry"]["name"]` | Direct copy | `industry` |

**Code:**
```python
"company_name": job.get("company", {}).get("name", "")
"title": job.get("title", "")
"job_category": job.get("hierarchicalJobCategory", {}).get("name", "")
"industry": job.get("company", {}).get("industry", {}).get("name", "")
```

---

### 3. **Education Level (NORMALIZED)** ✨

**Raw Values from Glints API:**
- "HIGH_SCHOOL"
- "DIPLOMA"
- "BACHELOR"
- "MASTER"
- "DOCTORATE" / "PHD"

**Normalization Mapping:**
```python
{
    "HIGH_SCHOOL": "SMA/SMK/Sederajat",
    "DIPLOMA": "D1",  # Generic diploma fallback
    "BACHELOR": "S1",
    "MASTER": "S2",
    "DOCTORATE": "S3",
    "PHD": "S3"
}
# Default: "SMA/SMK/Sederajat"
```

**Example:**
- Input: `"BACHELOR"` → Output: `"S1"`
- Input: `"DIPLOMA"` → Output: `"D1"` (generic fallback)
- Input: `"HIGH_SCHOOL"` → Output: `"SMA/SMK/Sederajat"`

---

### 4. **Salary Range (DIRECT FROM API)** 💰

**Source:** `job["salaries"]` (array of salary objects)

**Structure:**
```json
"salaries": [
  {
    "minAmount": 4400000,
    "maxAmount": 5500000,
    "CurrencyCode": "IDR",
    "salaryMode": "MONTH",
    "salaryType": "BASIC"
  }
]
```

**Extraction:**
```python
salaries = job.get("salaries", [])
if salaries:
    salary_min = salaries[0].get("minAmount", 0)
    salary_max = salaries[0].get("maxAmount", 0)
else:
    salary_min = 0
    salary_max = 0
```

**Example:**
- Input: `"minAmount": 4400000, "maxAmount": 5500000`
- Output: `salary_min: 4400000, salary_max: 5500000`

---

### 5. **Experience Level (NORMALIZED)** 📈

**Source:** `minYearsOfExperience` and `maxYearsOfExperience` (integers)

**Normalization Logic:**
```python
# Calculate average years
avg_years = (min_years + max_years) / 2

if avg_years <= 2:
    return "1-3 Tahun"
elif avg_years <= 5:
    return "3-5 Tahun"
elif avg_years <= 10:
    return "5-10 Tahun"
else:
    return "Lebih dari 10 Tahun"
```

**Example:**
- Input: `minYearsOfExperience: 1, maxYearsOfExperience: 3` → Output: `"1-3 Tahun"`
- Input: `minYearsOfExperience: 3, maxYearsOfExperience: 5` → Output: `"3-5 Tahun"`

---

### 6. **Work Arrangement (NORMALIZED)** 🏠

**Source:** `workArrangementOption` (string)

**Raw Values:**
- "ONSITE"
- "REMOTE" / "WORK_FROM_HOME"
- "HYBRID"

**Mapping:**
```python
{
    "ONSITE": "On-site Working",
    "REMOTE": "Remote Working",
    "WORK_FROM_HOME": "Remote Working",
    "HYBRID": "Hybrid Working"
}
# Default: "On-site Working"
```

---

### 7. **Job Type (NORMALIZED)** 💼

**Source:** `type` (string)

**Raw Values:**
- "FULL_TIME"
- "PART_TIME"
- "CONTRACT"
- "INTERNSHIP"
- "FREELANCE"

**Mapping:**
```python
{
    "FULL_TIME": "Full Time",
    "PART_TIME": "Part Time",
    "CONTRACT": "Contract",
    "INTERNSHIP": "Internship",
    "FREELANCE": "Freelance"
}
# Default: "Full Time"
```

---

### 8. **Location Fields** 📍

**Source:** `job["location"]` (hierarchical structure)

Glints uses a hierarchical location system with `parents` array:

```python
location = {
    "name": "Cilincing",              # District (level 4)
    "level": 4,
    "administrativeLevelName": "District",
    "parents": [
        {
            "level": 3,
            "name": "Jakarta Utara",  # City
            "administrativeLevelName": "City"
        },
        {
            "level": 2,
            "name": "DKI Jakarta",    # Province
            "administrativeLevelName": "Province"
        },
        {
            "level": 1,
            "name": "Indonesia",      # Country
            "administrativeLevelName": "Country"
        }
    ]
}
```

**Extraction Logic:**
```python
# Find province (level 2)
province = ""
city = ""

for parent in location.get("parents", []):
    if parent.get("level") == 2:
        province = parent.get("name", "")
    elif parent.get("level") == 3:
        city = parent.get("name", "")

# If no city found, use district name
if not city:
    city = location.get("name", "")
```

**Example:**
```python
"province": "DKI Jakarta"
"city": "Jakarta Utara"
```

---

### 9. **Skills Extraction** 🎯

**Source:** `job["skills"]` (array)

**Structure:**
```json
"skills": [
  {
    "mustHave": true,
    "skill": {
      "id": "...",
      "name": "Financial Analysis"
    }
  }
]
```

**Extraction:**
```python
# Separate must-have and optional skills
must_have_skills = []
optional_skills = []

for skill_item in job.get("skills", []):
    skill_name = skill_item.get("skill", {}).get("name", "")
    if skill_item.get("mustHave"):
        must_have_skills.append(skill_name)
    else:
        optional_skills.append(skill_name)

# Combine (must-have first, limit to 10)
all_skills = must_have_skills + optional_skills
skills_str = ", ".join(all_skills[:10])
```

---

### 10. **Job Description (FROM DETAIL API)** 📝

**Source:** Detail API provides `descriptionJsonString` in DraftJS JSON format.

**Detail API Endpoint:** `https://glints.com/api/v2-alc/graphql?op=getJobDetailsById`

**Detail API Payload:**
```json
{
  "operationName": "getJobDetailsById",
  "variables": {
    "opportunityId": "<job_id>",
    "traceInfo": "<trace_from_search>",
    "source": "Explore"
  },
  "query": "query getJobDetailsById($opportunityId: String!, ...) { ... }"
}
```

**Detail API Response Contains:**
- `descriptionJsonString` - Full job description in DraftJS JSON format
- `benefits` - Job benefits
- `interviewProcessJsonString` - Interview process
- Complete company info (website, address, description, photos, social media)

**JSON Description Parsing:**
```python
# Parse DraftJS JSON to HTML
desc_data = json.loads(detail["descriptionJsonString"])
blocks = desc_data.get("blocks", [])

for block in blocks:
    text = block.get("text", "")
    block_type = block.get("type", "unstyled")
    
    if block_type == "header-two":
        html_parts.append(f"<h2>{text}</h2>")
    elif block_type == "unordered-list-item":
        html_parts.append(f"<li>{text}</li>")
    else:
        html_parts.append(f"<p>{text}</p>")
```

**Fallback Construction Logic (if detail API fails):**
```python
parts = []

# Section 1: Job Information
parts.append("<h2>Job Information</h2>")

# Industry
industry = job.get("company", {}).get("industry", {}).get("name", "")
if industry:
    parts.append(f"<p><strong>Industry:</strong> {industry}</p>")

# Experience Required
min_exp = job.get("minYearsOfExperience", 0) or 0
max_exp = job.get("maxYearsOfExperience", 0) or 0
if min_exp or max_exp:
    parts.append(f"<p><strong>Experience Required:</strong> {min_exp}-{max_exp} years</p>")

# Education Level
education = job.get("educationLevel", "")
if education:
    parts.append(f"<p><strong>Education Level:</strong> {education}</p>")

# Section 2: Required Skills
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

# Section 3: Job Category
category = job.get("hierarchicalJobCategory", {}).get("name", "")
if category:
    parts.append(f"<p><strong>Job Category:</strong> {category}</p>")

# Combine all parts
content = "\n".join(parts)
```

**Example Output:**
```html
<h2>Job Information</h2>
<p><strong>Industry:</strong> Logistics and Supply Chain</p>
<p><strong>Experience Required:</strong> 1-3 years</p>
<p><strong>Education Level:</strong> DIPLOMA</p>
<h2>Required Skills</h2>
<ul>
<li>Financial Analysis (Required)</li>
<li>Tax Reporting (Required)</li>
<li>Accounting (Required)</li>
<li>Tax Planning (Required)</li>
<li>Microsoft Excel (Required)</li>
</ul>
<p><strong>Job Category:</strong> Tax Accountant</p>
```

---

### 11. **Job Level (INFERRED)** 📊

**Source:** Inferred from `title` and `minYearsOfExperience`/`maxYearsOfExperience`

**Inference Logic:**
```python
title_lower = job.get("title", "").lower()
max_exp = job.get("maxYearsOfExperience", 0) or 0

# Check title keywords first
if any(keyword in title_lower for keyword in ["director", "head", "chief", "vp"]):
    return "Management"
elif any(keyword in title_lower for keyword in ["senior", "sr", "lead"]):
    return "Senior Level"
elif any(keyword in title_lower for keyword in ["junior", "jr", "entry", "trainee", "intern"]):
    return "Entry Level"
# Check experience years
elif max_exp <= 2:
    return "Entry Level"
elif max_exp <= 5:
    return "Mid Level"
elif max_exp > 5:
    return "Senior Level"
else:
    return "Mid Level"  # Default
```

---

### 12. **Gender Requirement**

**Source:** Not provided by Glints API

**Default:**
```python
"gender": "Laki-laki/Perempuan"  # No restriction
```

---

### 13. **Tags (COMBINED)** 🏷️

**Source:** Multiple fields combined

**Logic:**
```python
tag_items = []

# Add category
if category:
    tag_items.append(category)

# Add education
if education and education != "Tanpa Minimal Pendidikan":
    tag_items.append(education)

# Add level
if level:
    tag_items.append(level)

# Add job type
if job_type:
    tag_items.append(job_type)

# Add work arrangement
if work_arrangement:
    tag_items.append(work_arrangement)

# Add industry
if industry:
    tag_items.append(industry)

tag_combined = ", ".join(tag_items)
```

**Example Output:**
```
"Tax Accountant, D1-D4, Entry Level, Full Time, On-site Working, Logistics and Supply Chain"
```

---

## 📋 **Final Google Sheets Columns**

The final row data contains these columns (in order):

1. **internal_id** - Auto-generated UUID
2. **source_id** - Job ID from Glints
3. **job_source** - Always "Glints"
4. **link** - Direct URL to job posting
5. **company_name** - Company name
6. **job_category** - Job category from hierarchicalJobCategory
7. **title** - Job title
8. **content** - Constructed HTML description
9. **province** - Province (from location.parents level 2)
10. **city** - City (from location.parents level 3)
11. **experience** - Normalized experience level
12. **job_type** - Job type (Full Time, Part Time, etc.)
13. **level** - Job level (inferred from title/experience)
14. **salary_min** - Minimum salary in Rupiah (integer)
15. **salary_max** - Maximum salary in Rupiah (integer)
16. **education** - Normalized education requirement
17. **work_policy** - Work policy (On-site/Remote/Hybrid)
18. **industry** - Industry sector
19. **gender** - Always "Laki-laki/Perempuan" (not provided by API)
20. **tags** - Combined tags

---

## 🔁 **Complete Orchestration Flow**

### ScraperService.scrape_glints_all_pages()

```python
1. Initialize Sheets Client
   └─→ Load service account credentials
   └─→ Connect to Google Sheets
   └─→ Load existing job IDs (for duplicate detection)

2. Scrape All Pages from GraphQL API
   page_num = 1
   WHILE True:
       │
       ├─→ GlintsClient.fetch_page(page_num)
       │   └─→ POST https://glints.com/api/v2-alc/graphql?op=searchJobsV3
       │   └─→ Payload: GraphQL query with page number
       │   └─→ Returns: (jobsInPage[], hasMore)
       │
       ├─→ FOR each job in jobsInPage[]:
       │   │
       │   ├─→ Check status field
       │   │   └─→ If status != "OPEN": SKIP (important!)
       │   │
       │   ├─→ Check if job["id"] already exists
       │   │   └─→ If exists: SKIP (duplicate)
       │   │   └─→ If new: CONTINUE
       │   │
       │   ├─→ GlintsClient.fetch_job_detail(job_id, trace_info)
       │   │   └─→ POST https://glints.com/api/v2-alc/graphql?op=getJobDetailsById
       │   │   └─→ Payload: job ID + trace info
       │   │   └─→ Returns: Complete job detail with description
       │   │
       │   ├─→ Combine search data + detail data
       │   │   └─→ combined_job = {**job, "detail": job_detail}
       │   │
       │   ├─→ GlintsTransformer.transform_job(combined_job, headers)
       │   │   ├─→ Filter by status === "OPEN"
       │   │   ├─→ map_education()
       │   │   ├─→ map_experience()
       │   │   ├─→ map_work_arrangement()
       │   │   ├─→ map_job_type()
       │   │   ├─→ extract_location()
       │   │   ├─→ extract_salary()
       │   │   ├─→ extract_skills()
       │   │   ├─→ build_job_description()
       │   │   ├─→ infer_job_level()
       │   │   └─→ Build job_dict
       │   │   └─→ Return row_data[] or None
       │   │
       │   ├─→ IF row_data is not None:
       │   │   └─→ SheetsClient.append_row(row_data)
       │   │       └─→ RateLimiter.check("write")
       │   │       └─→ sheet.append_row()
       │   │       └─→ Add job ID to existing_ids set
       │
       ├─→ Check hasMore field
       │   └─→ If hasMore == False: BREAK
       │
       ├─→ Sleep 1 second (page_delay)
       └─→ page_num++

3. Wait 60 minutes before next cycle
```

---

## ⚙️ **Key Differences from Other Sources**

| **Aspect** | **Loker.id** | **JobStreet** | **Glints** |
|-----------|-------------|---------------|-----------|
| **API Type** | REST JSON | REST + HTML scraping | GraphQL |
| **Data Completeness** | Complete in API | Requires HTML scraping | Complete in API ✅ |
| **Education** | Structured field | Extract from HTML | Structured field ✅ |
| **Experience** | Structured field | Extract from HTML | Structured field ✅ |
| **Salary** | Always provided | Often missing | Usually provided ✅ |
| **Job Description** | HTML in API | Scrape HTML page | Build from data ⚠️ |
| **Work Policy** | Boolean | Structured field | Structured field ✅ |
| **Location** | Simple array | Nested hierarchy | Nested hierarchy |
| **Requests per Job** | 1 request | 2 requests | 2 requests (search + detail) |
| **Status Filtering** | Not needed | Not needed | REQUIRED ⚠️ |
| **Parsing Complexity** | Low | High | Medium |

---

## 🎯 **Pagination Logic**

Glints uses a simple `hasMore` boolean field:

```python
response = {
    "data": {
        "searchJobsV3": {
            "hasMore": true,  # ← Check this field
            "jobsInPage": [...]
        }
    }
}
```

**Loop Logic:**
```python
page_num = 1

while True:
    jobs, has_more = glints_client.fetch_page(page_num)
    
    if not jobs:
        break
    
    # Process jobs...
    
    if not has_more:
        break  # No more pages
    
    page_num += 1
```

---

## ⚠️ **Important Considerations**

### 1. **Status Filtering (CRITICAL)**
- **ALWAYS** check `status === "OPEN"` before processing
- Do this in the transformer, not in the client
- Return `None` from transformer if status is not OPEN
- Handle `None` return value in scraper service

### 2. **GraphQL Query Complexity**
- The GraphQL query is long but complete
- Includes all necessary fragments
- Do not modify unless API changes

### 3. **Rate Limiting**
- Glints requires **1 request per page** (simpler than JobStreet)
- Add 1-second delays between pages
- Respect Google Sheets rate limits

### 4. **No HTML Scraping**
- Unlike JobStreet, Glints provides complete data in one request
- Job description is constructed from structured data
- No need for BeautifulSoup parsing

### 5. **Salary Data**
- Usually provided (better than JobStreet)
- Always in `salaries` array
- Use first item (salaryType: "BASIC")

---

## 📊 **Data Quality Comparison**

| **Field** | **Data Quality** | **Notes** |
|-----------|-----------------|-----------|
| Job ID | ✅ Excellent | UUID format, always present |
| Title | ✅ Excellent | Always present |
| Company | ✅ Excellent | Always present with industry |
| Location | ✅ Excellent | Hierarchical, detailed |
| Salary | 🟡 Good | Usually present, sometimes hidden |
| Education | ✅ Excellent | Standardized format |
| Experience | ✅ Excellent | Min/Max years provided |
| Skills | ✅ Excellent | Detailed with mustHave flag |
| Description | 🟡 Constructed | Not provided, built from data |
| Work Policy | ✅ Excellent | Clear options |
| Job Type | ✅ Excellent | Standardized |
| Status | ✅ Excellent | Critical for filtering |

---

## 🎯 **Summary**

| **Component** | **Purpose** | **Output** |
|--------------|-------------|------------|
| **GlintsClient** | Fetch job data via GraphQL | `List[Dict]` - Complete job objects |
| **GlintsTransformer** | Filter, normalize & map fields | `List[str]` or `None` - Row data |
| **Status Filter** | Skip non-OPEN jobs | Early return if not OPEN |
| **Location Parser** | Extract from hierarchy | Province and city strings |
| **Description Builder** | Construct HTML from data | Structured HTML string |
| **SheetsClient** | Store in Google Sheets | Appended row with duplicate check |
| **RateLimiter** | Respect API quotas | Automatic delays when needed |

**Total Fields Extracted:** 20 columns per job  
**Normalization Applied:** Education, Experience, Work Arrangement, Job Type  
**HTML Construction:** Built from structured data (no scraping)  
**Status Filtering:** Required - only OPEN jobs  
**Pagination:** Simple hasMore boolean  
**Requests per Job:** 1 (most efficient!)

---

## 🔑 **Key Advantages of Glints**

1. ✅ **Single Request** - Complete data in one GraphQL call
2. ✅ **Structured Data** - All fields in clean format
3. ✅ **Status Field** - Easy filtering of active jobs
4. ✅ **Rich Metadata** - Skills, education, experience all structured
5. ✅ **No HTML Parsing** - Faster and more reliable
6. ✅ **GraphQL Benefits** - Request exactly what you need
7. ✅ **Better Salary Data** - Usually available

---

## 📖 **API Documentation Reference**

**GraphQL Query Fields Used:**
- Job: id, title, status, type, workArrangementOption, educationLevel
- Company: id, name, logo, industry
- Location: Hierarchical with parents
- Salary: minAmount, maxAmount, CurrencyCode
- Skills: skill.name, mustHave
- Experience: minYearsOfExperience, maxYearsOfExperience
- Category: hierarchicalJobCategory
- Pagination: hasMore, page, pageSize

**Status Values:**
- `OPEN` - Active (✅ scrape)
- `CLOSED` - Inactive (❌ skip)
- `DRAFT` - Not published (❌ skip)
