# 🔍 Loker.id Orchestration Deep Dive

Complete guide to understanding how we scrape, extract, transform, and store job data from Loker.id.

---

## 📊 **Data Flow Overview**

```
┌─────────────────────────────────────────────────────────────────────┐
│                    LOKER.ID API ENDPOINT                            │
│  https://www.loker.id/cari-lowongan-kerja/page/{N}?_data           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ Raw JSON Response
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      LOKER CLIENT                                   │
│  • Fetches paginated job listings                                  │
│  • Handles 404 (no more pages)                                     │
│  • Returns: List[Dict] - Array of job objects                      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ job: Dict[str, Any]
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   JOB TRANSFORMER                                   │
│  1. Extract raw fields from API response                           │
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

## 🎯 **What We Extract from Loker.id API**

### Raw API Response Structure

Each job in the API response (`response.json()["jobs"]`) contains:

```json
{
  "id": 12345,
  "title": "Software Engineer",
  "company_name": "PT Tech Indonesia",
  "category": "Information Technology",
  "education": "Sarjana / S1",
  "job_experience": "2-3 Tahun",
  "job_type": "Full Time",
  "job_salary": "Rp.4 – 5 Juta",
  "is_remote": false,
  "gender": "Laki-laki/Perempuan",
  "content": "<h4>Job Description</h4><p>We are looking for...</p>",
  "level": {
    "name": "Mid Level"
  },
  "tag": {
    "name": "Backend Development"
  },
  "locations": [
    {"name": "DKI Jakarta"},
    {"name": "Jakarta Selatan"}
  ],
  "industries": [
    {"name": "Information Technology"}
  ]
}
```

---

## 🔄 **Field-by-Field Extraction & Mapping**

### 1. **Basic Identification Fields**

| **Field** | **Source** | **Transformation** | **Output Column** |
|-----------|------------|-------------------|------------------|
| Job ID | `job["id"]` | Convert to string | `id` |
| Source | Hardcoded | Always "Loker.id" | `sumber_lowongan` |
| Direct Link | `job["id"]` | Build URL: `https://www.loker.id/cari-lowongan-kerja?jobid={id}` | `link` |

**Code:**
```python
"id": str(job["id"])
"sumber_lowongan": "Loker.id"
"link": f"https://www.loker.id/cari-lowongan-kerja?jobid={job['id']}"
```

---

### 2. **Company & Job Title**

| **Field** | **Source** | **Transformation** | **Output Column** |
|-----------|------------|-------------------|------------------|
| Company Name | `job["company_name"]` | Direct copy | `company_name` |
| Job Title | `job["title"]` | Direct copy | `title` |
| Category | `job["category"]` | Direct copy | `kategori_pekerjaan` |

**Code:**
```python
"company_name": job["company_name"]
"title": job["title"]
"kategori_pekerjaan": job.get("category", "")
```

---

### 3. **Education Level (NORMALIZED)** ✨

**Raw Values from API:**
- "SMA / SMK / STM"
- "Diploma/D1/D2/D3"
- "Sarjana / S1"
- "Master / S2"
- "Doctor / S3"

**Normalization Mapping:**
```python
{
    "SMA / SMK / STM": "SMA/SMK/Sederajat",
    "D1": "D1",
    "D2": "D2", 
    "D3": "D3",
    "D4": "D4",
    "Diploma/D1/D2/D3": "D1",  # Range fallback
    "D1-D4": "D1",              # Range fallback
    "DIPLOMA": "D1",            # Generic fallback
    "Sarjana / S1": "S1",
    "Master / S2": "S2",
    "Doctor / S3": "S3"
}
# Default: "SMA/SMK/Sederajat"
```

**Example:**
- Input: `"D3"` → Output: `"D3"` (specific level)
- Input: `"Diploma/D1/D2/D3"` → Output: `"D1"` (range fallback)
- Input: `"Sarjana / S1"` → Output: `"S1"`
- Input: `"SMA / SMK / STM"` → Output: `"SMA/SMK/Sederajat"`

---

### 4. **Salary Range (EXTRACTED AS INTEGERS)** 💰

**Raw Values from API:**
- "Rp.1 – 2 Juta"
- "Rp.3 – 4 Juta"
- "Rp.4 – 5 Juta"
- "Rp.5 – 6 Juta"
- "Negosiasi"

**Extraction to Min/Max (in Rupiah):**
```python
"Rp.1 – 2 Juta" → salary_min: 1000000, salary_max: 2000000
"Rp.2 – 3 Juta" → salary_min: 2000000, salary_max: 3000000
"Rp.3 – 4 Juta" → salary_min: 3000000, salary_max: 4000000
"Rp.4 – 5 Juta" → salary_min: 4000000, salary_max: 5000000
"Rp.5 – 6 Juta" → salary_min: 5000000, salary_max: 6000000
"Rp.6 – 7 Juta" → salary_min: 6000000, salary_max: 7000000
"Rp.7 – 8 Juta" → salary_min: 7000000, salary_max: 8000000
"Rp.8 – 9 Juta" → salary_min: 8000000, salary_max: 9000000
"Rp.9 – 10 Juta" → salary_min: 9000000, salary_max: 10000000
"Rp.10 – 15 Juta" → salary_min: 10000000, salary_max: 15000000
"Rp.15 – 20 Juta" → salary_min: 15000000, salary_max: 20000000
"Rp.20 – 25 Juta" → salary_min: 20000000, salary_max: 25000000
"Negosiasi" → salary_min: 0, salary_max: 0
# Default (unknown): salary_min: 0, salary_max: 0
```

**Example:**
- Input: `"Rp.4 – 5 Juta"` → Output: `salary_min: 4000000, salary_max: 5000000`
- Input: `"Negosiasi"` → Output: `salary_min: 0, salary_max: 0`

---

### 5. **Experience Level (NORMALIZED)** 📈

**Raw Values from API:**
- "1-2 Tahun"
- "2-3 Tahun"
- "3-4 Tahun"
- "5-6 Tahun"
- "10-15 Tahun"
- etc.

**Normalization Logic:**
```python
"1-2 Tahun" → "1-3 Tahun"
"2-3 Tahun", "3-4 Tahun", "4-5 Tahun" → "3-5 Tahun"
"5-6 Tahun", "6-10 Tahun", "7-10 Tahun" → "5-10 Tahun"
Any experience > 10 years → "Lebih dari 10 Tahun"
# Default: "1-3 Tahun"
```

**Example:**
- Input: `"2-3 Tahun"` → Output: `"3-5 Tahun"`
- Input: `"15-20 Tahun"` → Output: `"Lebih dari 10 Tahun"`

---

### 6. **Work Policy (NORMALIZED)** 🏠

**Raw Value:** `is_remote` (boolean)

**Mapping:**
```python
True → "Remote Working"
False → "On-site Working"
```

---

### 7. **Location Fields** 📍

**Source:** `job["locations"]` (array)

```python
# locations[0] = Province
# locations[1] = City/District
"lokasi_provinsi": job["locations"][0]["name"] if job.get("locations") else ""
"lokasi_kota": job["locations"][1]["name"] if len(locations) > 1 else ""
```

**Example:**
```python
locations = [
    {"name": "DKI Jakarta"},      # Province → lokasi_provinsi
    {"name": "Jakarta Selatan"}   # City → lokasi_kota
]
```

---

### 8. **Job Content (CLEANED HTML)** 📝

**Source:** `job["content"]` (raw HTML string)

**Cleaning Process (ContentCleaner):**

#### Step 1: HTML Unescaping & Parsing
```python
soup = BeautifulSoup(html.unescape(raw_html), "html.parser")
```

#### Step 2: Normalize Headings
```python
# Convert all <h4> to <h2> for consistency
for h4 in soup.find_all("h4"):
    h4.name = "h2"
```

#### Step 3: Extract & Format Content
- **Headings (`<h2>`)**: Extract text, remove duplicates
- **Paragraphs (`<p>`, `<div>`)**: 
  - Detect if content is a list (numbered or bulleted)
  - Format as `<ol>` for numbered lists
  - Format as `<ul>` for bullet lists
  - Regular text becomes `<p>` tags

#### Step 4: Remove Duplicates
```python
seen = set()  # Track seen content to avoid duplicates
```

**Example Input:**
```html
<h4>Job Description</h4>
<p>We are looking for a talented developer.</p>
<div>
1. Experience with Python
2. Knowledge of Django
3. Strong communication skills
</div>
```

**Example Output:**
```html
<h2>Job Description</h2>
<p>We are looking for a talented developer.</p>
<ol>
<li>Experience with Python</li>
<li>Knowledge of Django</li>
<li>Strong communication skills</li>
</ol>
```

---

### 9. **Other Fields**

| **Field** | **Source** | **Transformation** |
|-----------|------------|-------------------|
| Job Type | `job["job_type"]` | Direct copy (e.g., "Full Time", "Part Time") |
| Job Level | `job["level"]["name"]` | Direct copy (e.g., "Entry Level", "Senior") |
| Industry | `job["industries"][0]["name"]` | First industry from array |
| Gender | `job["gender"]` | Direct copy (e.g., "Laki-laki/Perempuan") |

---

### 10. **Tags (COMBINED)** 🏷️

**Source:** Multiple fields combined

**Logic:**
```python
tag_items = []
if job.get("category"):
    tag_items.append(job["category"])              # e.g., "IT"
if pendidikan:
    tag_items.append(pendidikan)                    # e.g., "S1"
if job.get("level"):
    tag_items.append(job["level"]["name"])          # e.g., "Mid Level"
if job.get("tag"):
    tag_items.append(job["tag"]["name"])            # e.g., "Backend Development"
if kebijakan_kerja:
    tag_items.append(kebijakan_kerja)               # e.g., "On-site Working"

tag_combined = ", ".join(tag_items)
```

**Example Output:**
```
"Information Technology, S1, Mid Level, Backend Development, On-site Working"
```

---

## 📋 **Final Google Sheets Columns**

The final row data contains these columns (in order):

1. **id** - Job ID
2. **sumber_lowongan** - Always "Loker.id"
3. **link** - Direct URL to job posting
4. **company_name** - Company name
5. **kategori_pekerjaan** - Job category
6. **title** - Job title
7. **content** - Cleaned HTML description
8. **lokasi_provinsi** - Province
9. **lokasi_kota** - City/District
10. **pengalaman** - Normalized experience level
11. **tipe_pekerjaan** - Job type (Full Time, Part Time, etc.)
12. **level** - Job level (Entry, Mid, Senior)
13. **salary_min** - Minimum salary in Rupiah (integer)
14. **salary_max** - Maximum salary in Rupiah (integer)
15. **pendidikan** - Normalized education requirement
16. **kebijakan_kerja** - Work policy (Remote/On-site)
17. **industry** - Industry sector
18. **gender** - Gender requirement
19. **tag** - Combined tags

---

## 🔁 **Complete Orchestration Flow**

### ScraperService.run_once()

```python
1. Initialize Sheets Client
   └─→ Load service account credentials
   └─→ Connect to Google Sheets
   └─→ Load existing job IDs (for duplicate detection)

2. Scrape All Pages
   page_num = 1
   WHILE True:
       ├─→ LokerClient.fetch_page(page_num)
       │   └─→ GET https://www.loker.id/cari-lowongan-kerja/page/{page_num}?_data
       │   └─→ Returns: jobs[] array
       │
       ├─→ FOR each job in jobs[]:
       │   │
       │   ├─→ Check if job["id"] already exists
       │   │   └─→ If exists: SKIP
       │   │   └─→ If new: CONTINUE
       │   │
       │   ├─→ JobTransformer.transform_job(job, headers)
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
       │       └─→ Add job ID to existing_ids set
       │
       ├─→ Sleep 1 second (page_delay)
       └─→ page_num++

3. Wait 60 minutes before next cycle
```

---

## ⚙️ **Key Features**

### Duplicate Prevention
```python
# Before processing:
existing_ids = self.sheets_client.get_existing_ids()  # Get all IDs from column C

# For each job:
if str(job["id"]) in existing_ids:
    return False  # Skip duplicate
```

### Rate Limiting
```python
# Google Sheets API quotas:
- Read: 300 requests/minute
- Write: 60 requests/minute
- Total: 500 requests/100 seconds

# Automatically enforced by RateLimiter
```

### Pagination
```python
# Keep fetching pages until:
- API returns 404 (no more pages)
- API returns empty jobs array
```

---

## 📊 **Data Normalization Benefits**

### Why We Normalize?

1. **Consistency**: API returns varied formats → We store unified formats
2. **Searchability**: Standardized values make filtering easier
3. **Analytics**: Clean data enables better insights
4. **UI/UX**: Standardized tags improve user experience

### Example Normalization Impact

**Before (Raw API):**
```
Education: "SMA / SMK / STM", "Diploma/D1/D2/D3", "Sarjana / S1"
Salary: "Rp.1 – 2 Juta", "Rp.3 – 4 Juta", "Rp.4 – 5 Juta"
Experience: "1-2 Tahun", "2-3 Tahun", "3-4 Tahun", "4-5 Tahun"
```

**After (Normalized):**
```
Education: "SMA/SMK", "D1-D4", "S1"
Salary: "Rp. 1-2 Juta", "Rp. 3-5 Juta", "Lebih dari Rp. 5 Juta"
Experience: "1-3 Tahun", "3-5 Tahun"
```

**Result:** From 12+ possible values → 3-5 standardized categories

---

## 🎯 **Summary**

| **Component** | **Purpose** | **Output** |
|--------------|-------------|------------|
| **LokerClient** | Fetch raw job data from API | `List[Dict]` - Array of job objects |
| **JobTransformer** | Normalize & map fields | `List[str]` - Row data for spreadsheet |
| **ContentCleaner** | Clean HTML descriptions | Clean, formatted HTML string |
| **SheetsClient** | Store in Google Sheets | Appended row with duplicate check |
| **RateLimiter** | Respect API quotas | Automatic delays when needed |

**Total Fields Extracted:** 18 columns per job
**Normalization Applied:** Education, Salary, Experience, Work Policy
**HTML Cleaning:** Automatic formatting of lists and headings
**Duplicate Detection:** By job ID (column C)
**Pagination:** Automatic until no more results
