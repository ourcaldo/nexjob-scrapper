# Transformer Implementation Guide

## ✅ Completed: Separate Transformers for Each Source

We've successfully implemented the **separate transformer approach** for handling multiple job sources.

---

## 📁 New File Structure

```
src/transformers/
├── __init__.py
├── content_cleaner.py           # Shared HTML cleaning utility
├── job_transformer.py           # OLD - deprecated, keep for backward compatibility
├── loker_transformer.py         # NEW - Loker.id specific transformer
└── jobstreet_transformer.py     # NEW - JobStreet specific transformer
```

---

## 🔄 How It Works

### **1. Loker.id Flow**

```python
# In ScraperService:

# Step 1: Fetch raw data from API
jobs_data, has_more = self.loker_client.fetch_page(page_num)

# Step 2: Transform using Loker-specific transformer
for job in jobs_data:
    headers = self.sheets_client.get_headers()
    row_data = self.loker_transformer.transform_job(job, headers)  # 🎯 Loker transformer
    self.sheets_client.append_row(row_data)
```

**What the LokerTransformer does:**
- ✅ Maps Loker.id API fields to Google Sheets columns
- ✅ Normalizes education: `"Sarjana / S1"` → `"S1"`
- ✅ Extracts salary range: `"Rp.4 – 5 Juta"` → `(4000000, 5000000)`
- ✅ Normalizes experience: `"2-3 Tahun"` → `"3-5 Tahun"`
- ✅ Converts boolean to text: `is_remote: true` → `"Remote Working"`
- ✅ Cleans HTML content
- ✅ Sets source: `"Loker.id"`

---

### **2. JobStreet Flow**

```python
# In ScraperService:

# Step 1: Fetch basic data from search API
jobs_data, has_more, total = self.jobstreet_client.fetch_search_page(page_num)

for job in jobs_data:
    job_id = extract_job_id(job)
    
    # Step 2: Fetch detailed data by scraping HTML
    job_detail = self.jobstreet_client.fetch_job_detail(job_id)
    # Returns: {content: "...", pendidikan: "S1", pengalaman: "1-3 Tahun", gender: "..."}
    
    # Step 3: Merge search API data + HTML data
    combined_job = {**job, **job_detail}
    
    # Step 4: Transform using JobStreet-specific transformer
    headers = self.sheets_client.get_headers()
    row_data = self.jobstreet_transformer.transform_job(combined_job, headers)  # 🎯 JobStreet transformer
    self.sheets_client.append_row(row_data)
```

**What the JobStreetTransformer does:**
- ✅ Extracts job ID from two possible locations
- ✅ Extracts company name from nested structure
- ✅ Parses `seoHierarchy` for location (province/city)
- ✅ Maps work arrangements: `"On-site"` → `"On-site Working"`
- ✅ Infers job level from title keywords
- ✅ Uses pre-extracted education/experience from HTML (already normalized by client)
- ✅ Parses salary if available (often empty)
- ✅ Cleans HTML content
- ✅ Sets source: `"JobStreet"`

---

## 🎯 Key Differences

| **Aspect** | **LokerTransformer** | **JobStreetTransformer** |
|-----------|---------------------|-------------------------|
| **Input** | Single API response | Combined (API + HTML) |
| **Education** | Normalizes from API field | Uses pre-extracted from HTML |
| **Experience** | Normalizes from API field | Uses pre-extracted from HTML |
| **Salary** | Always provided, needs mapping | Often empty, needs parsing |
| **Location** | Simple array | Nested seoHierarchy |
| **Work Policy** | Boolean → text | Structured object → text |
| **Job Level** | Direct from API | Inferred from title |

---

## 📋 ScraperService Updates

### **Initialization**
```python
def __init__(self, settings: Settings):
    # Two clients
    self.loker_client = LokerClient(...)
    self.jobstreet_client = JobStreetClient(...)
    
    # Two transformers
    self.loker_transformer = LokerTransformer()
    self.jobstreet_transformer = JobStreetTransformer()
```

### **Processing Methods**
```python
# Separate processing methods for each source
def process_loker_job(self, job: dict) -> bool:
    row_data = self.loker_transformer.transform_job(job, headers)
    # ...

def process_jobstreet_job(self, job: dict) -> bool:
    row_data = self.jobstreet_transformer.transform_job(job, headers)
    # ...
```

### **Scraping Methods**
```python
# Separate scraping methods for each source
def scrape_loker_all_pages(self) -> int:
    # Scrapes all Loker.id pages
    # ...

def scrape_jobstreet_all_pages(self, max_pages: int = 10) -> int:
    # Scrapes JobStreet with HTML detail fetching
    # Includes 2-second delay between HTML requests
    # ...
```

---

## 🚀 How to Use

### **Current Setup (Loker.id only)**
```python
# In main.py - already configured
scraper = ScraperService(settings)
scraper.run_continuous()  # Scrapes Loker.id automatically
```

### **Enable JobStreet Scraping**
```python
# In scraper_service.py, update run_once():
def run_once(self) -> int:
    total_new_jobs = 0
    
    # Scrape Loker.id
    loker_jobs = self.scrape_loker_all_pages()
    total_new_jobs += loker_jobs
    
    # Enable JobStreet (currently commented out)
    jobstreet_jobs = self.scrape_jobstreet_all_pages(max_pages=5)  # Test with 5 pages
    total_new_jobs += jobstreet_jobs
    
    return total_new_jobs
```

---

## ✨ Benefits of This Approach

### 1. **Clean Separation**
Each transformer handles one source. Changes to Loker.id won't affect JobStreet.

### 2. **Easy to Test**
```python
# Test Loker transformer
loker_transformer = LokerTransformer()
row_data = loker_transformer.transform_job(loker_job, headers)

# Test JobStreet transformer  
jobstreet_transformer = JobStreetTransformer()
row_data = jobstreet_transformer.transform_job(jobstreet_job, headers)
```

### 3. **Easy to Extend**
Add LinkedIn later:
```python
# Create new file
src/transformers/linkedin_transformer.py

# In scraper_service.py
self.linkedin_transformer = LinkedInTransformer()

def process_linkedin_job(self, job: dict) -> bool:
    row_data = self.linkedin_transformer.transform_job(job, headers)
    # ...
```

### 4. **Clear Code Flow**
```python
# Very clear which transformer handles which source
Loker.id job → LokerTransformer → Google Sheets
JobStreet job → JobStreetTransformer → Google Sheets
LinkedIn job → LinkedInTransformer → Google Sheets
```

---

## 🔍 Code Locations

| **Component** | **File** | **Purpose** |
|--------------|----------|-------------|
| Loker Transformer | `src/transformers/loker_transformer.py` | Transform Loker.id jobs |
| JobStreet Transformer | `src/transformers/jobstreet_transformer.py` | Transform JobStreet jobs |
| Content Cleaner | `src/transformers/content_cleaner.py` | Shared HTML cleaning (used by both) |
| Loker Client | `src/clients/loker/loker_client.py` | Fetch Loker.id jobs |
| JobStreet Client | `src/clients/jobstreet/jobstreet_client.py` | Fetch + scrape JobStreet jobs |
| Scraper Service | `src/services/scraper_service.py` | Orchestrate all sources |

---

## 📝 Summary

✅ **Implemented:** Separate transformer for each source  
✅ **LokerTransformer:** Handles Loker.id API format  
✅ **JobStreetTransformer:** Handles JobStreet API + HTML format  
✅ **ScraperService:** Updated to use both transformers  
✅ **Ready to extend:** Easy to add more sources (LinkedIn, Indeed, etc.)

The architecture is now clean, maintainable, and scalable! 🎉
