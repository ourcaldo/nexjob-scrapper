# Job Scraper - Multi-Source Job Aggregation System

A production-ready Python-based job scraping service built with microservice architecture that automatically collects job postings from multiple sources (starting with Loker.id) and stores them in **Google Sheets** or **Supabase (PostgreSQL)** with intelligent data normalization and deduplication.

---

## 📋 Table of Contents

- [Introduction](#introduction)
- [Architecture Overview](#architecture-overview)
- [Key Features](#key-features)
- [Storage Backends](#storage-backends)
- [Project Structure](#project-structure)
- [Technical Stack](#technical-stack)
- [Setup Guide](#setup-guide)
- [Environment Configuration](#environment-configuration)
- [Google Sheets Configuration](#google-sheets-configuration)
- [Supabase Configuration](#supabase-configuration)
- [How to Use](#how-to-use)
- [Data Flow & Orchestration](#data-flow--orchestration)
- [Configuration Options](#configuration-options)
- [Adding New Job Sources](#adding-new-job-sources)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Introduction

This job scraper is designed as a **scalable, multi-source aggregation system** that collects job postings from various platforms and stores them in your choice of **Google Sheets** or **Supabase (PostgreSQL)**. The system features:

- **Flexible Storage**: Choose between Google Sheets (simple setup) or Supabase (scalable database)
- **Microservice Architecture**: Modular design with clear separation of concerns
- **Multi-Source Ready**: Easily extensible to support LinkedIn, Indeed, JobStreet, etc.
- **Intelligent Data Normalization**: Standardizes education levels, salary ranges, and experience requirements
- **Duplicate Prevention**: Automatic deduplication based on job IDs
- **Rate Limiting**: Built-in protection against API quota violations
- **HTML Content Cleaning**: Converts messy job descriptions into clean, structured HTML
- **Continuous Operation**: Runs 24/7 with configurable scraping intervals
- **Status Tracking**: Track job posting lifecycle (active, filled, expired, etc.) when using Supabase

### Current Sources
- ✅ **Loker.id** - Fully implemented with 20 data points per job
- ✅ **JobStreet** - Fully implemented with 20 data points per job (API + HTML scraping)
- 🔜 **LinkedIn** - Architecture ready, awaiting implementation

---

## 🏗️ Architecture Overview

### System Design

![Scraper System Architecture](images/Scraper%20System%20Architecture_1762889086713.png)

### Component Responsibilities

| **Component** | **Responsibility** | **Key Functions** |
|--------------|-------------------|------------------|
| **Settings** | Configuration management | Load credentials, validate config, manage env vars |
| **LokerClient** | API interaction | Fetch job listings, handle pagination, proxy support |
| **StorageClient** | Data persistence (abstraction) | Google Sheets or Supabase backend for storing jobs |
| **SheetsClient** | Google Sheets I/O | Authentication, read/write operations, duplicate check |
| **SupabaseClient** | Supabase I/O | Database connection, SQL operations, duplicate check |
| **JobTransformer** | Data normalization | Map education, salary, experience to standard formats |
| **ContentCleaner** | HTML processing | Clean job descriptions, format lists, remove duplicates |
| **RateLimiter** | API quota management | Track requests, enforce limits, automatic delays |
| **ScraperService** | Workflow orchestration | Coordinate components, manage continuous operation |

---

## ✨ Key Features

### 1. **Multi-Source Architecture**
Designed from the ground up to support multiple job platforms:

```
src/clients/
├── loker/                  # Loker.id implementation
├── linkedin/               # Ready for LinkedIn integration
├── indeed/                 # Ready for Indeed integration
├── base_storage_client.py  # Storage backend abstraction
├── sheets_client.py        # Google Sheets storage backend
└── supabase_client.py      # Supabase (PostgreSQL) storage backend
```

### 2. **Intelligent Data Normalization**

**Education Levels:**
```
"SMA / SMK / STM"      → "SMA/SMK"
"Diploma/D1/D2/D3"     → "D1-D4"
"Sarjana / S1"         → "S1"
```

**Salary Ranges (as integers):**
```
"Rp.4 – 5 Juta"  → salary_min: 4000000, salary_max: 5000000
"Rp.10 – 15 Juta" → salary_min: 10000000, salary_max: 15000000
"Negosiasi"      → salary_min: 0, salary_max: 0
```

**Experience Levels:**
```
"1-2 Tahun"      → "1-3 Tahun"
"2-3 Tahun"      → "3-5 Tahun"
"15-20 Tahun"    → "Lebih dari 10 Tahun"
```

### 3. **Flexible Storage Backends**
Choose the storage solution that fits your needs:

**Google Sheets**
- Quick setup, no database required
- Great for small to medium datasets (< 10,000 jobs)
- Easy to view and share
- Manual data manipulation with spreadsheet tools

**Supabase (PostgreSQL)**
- Scalable for large datasets (100,000+ jobs)
- Advanced SQL queries and analytics
- Built-in indexing for fast searches
- **Status tracking** (active, filled, expired, etc.)
- Real-time updates and API access
- Automatic backups

### 4. **Parallel Execution Mode**
Choose how to scrape multiple job sources:

**Sequential Mode (Default - Safer)**
- Sources scraped one after another (A → B → C)
- Lower resource usage
- Easier to debug
- Recommended for beginners

**Parallel Mode (Faster)**
- All enabled sources scraped simultaneously (A + B + C)
- 2-3x faster execution
- Higher resource usage
- Uses ThreadPoolExecutor with up to 3 concurrent threads
- Thread-safe duplicate prevention
- Recommended for production with stable configuration

**Configuration:**
```bash
# .env file
SCRAPE_MODE=sequential  # or "parallel"
```

### 5. **Duplicate Prevention**
- Fetches existing job IDs from storage on startup
- Maintains in-memory set for fast lookups
- Skips jobs that already exist (by ID)

### 5. **HTML Content Cleaning**
Converts messy job descriptions into clean, structured HTML:

**Input:**
```html
<h4>Job Description</h4>
<p>We are looking for...</p>
<div>
1. Experience with Python
2. Knowledge of Django
</div>
```

**Output:**
```html
<h2>Job Description</h2>
<p>We are looking for...</p>
<ol>
<li>Experience with Python</li>
<li>Knowledge of Django</li>
</ol>
```

### 6. **Rate Limiting Protection**
```python
Google Sheets API Quotas (when using Google Sheets):
- Read: 300 requests/minute
- Write: 60 requests/minute
- Total: 500 requests/100 seconds

Automatic enforcement with delays when limits approached
```

---

## 💾 Storage Backends

The Job Scraper supports two storage backends. Choose the one that best fits your needs:

### Comparison Table

| Feature | **Google Sheets** | **Supabase** |
|---------|------------------|--------------|
| **Setup Complexity** | Easy (service account + spreadsheet) | Moderate (Supabase account + SQL setup) |
| **Best For** | Small projects, quick demos, sharing data | Production, large datasets, analytics |
| **Scalability** | Up to ~10,000 rows | 100,000+ rows easily |
| **Query Performance** | Slower for large datasets | Fast with indexing |
| **Advanced Queries** | Limited (filter, sort) | Full SQL support |
| **Status Tracking** | ❌ Not available | ✅ Built-in status column |
| **Cost** | Free (Google Workspace limits) | Free tier available, pay as you grow |
| **Backup & Recovery** | Manual (version history) | Automatic (point-in-time recovery) |
| **Real-time Updates** | Limited | ✅ Built-in subscriptions |
| **API Access** | Google Sheets API | RESTful API + PostgreSQL |
| **Data Export** | CSV, Excel | CSV, SQL dump, API |

### When to Use Google Sheets

✅ **Perfect for:**
- Quick prototypes and demos
- Small to medium datasets (< 10,000 jobs)
- Teams that prefer spreadsheet interface
- Non-technical users who need to view data
- Projects without database infrastructure

### When to Use Supabase

✅ **Perfect for:**
- Production applications
- Large datasets (10,000+ jobs)
- Advanced analytics and reporting
- Integration with other services via API
- Projects requiring status tracking (active/filled/expired)
- Teams comfortable with SQL

---

## 📁 Project Structure

```
job-scraper/
├── src/
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py              # Configuration loader
│   │   ├── service-account.json     # Google credentials (git-ignored)
│   │   ├── service-account.json.example  # Template file
│   │   └── README.md                # Config setup guide
│   │
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── loker/                   # Loker.id source
│   │   │   ├── __init__.py
│   │   │   └── loker_client.py      # Loker.id API client
│   │   ├── linkedin/                # LinkedIn source (future)
│   │   │   └── __init__.py
│   │   └── sheets_client.py         # Shared Google Sheets client
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   └── scraper_service.py       # Main orchestration service
│   │
│   ├── transformers/
│   │   ├── __init__.py
│   │   ├── job_transformer.py       # Data normalization & mapping
│   │   └── content_cleaner.py       # HTML content cleaning
│   │
│   └── utils/
│       ├── __init__.py
│       └── rate_limiter.py          # API rate limiting utility
│
├── main.py                          # Application entry point
├── requirements.txt                 # Python dependencies
├── pyproject.toml                   # Project metadata
├── README.md                        # This file
├── LOKER_ORCHESTRATION.md           # Deep dive into Loker.id flow
└── SALARY_MAPPING_UPDATE.md         # Salary mapping documentation
```

---

## 🛠️ Technical Stack

### Core Dependencies
```
Python 3.11+
├── requests (2.32.5)        # HTTP requests to job APIs
├── beautifulsoup4 (4.14.2)  # HTML parsing & cleaning
├── gspread (6.2.1)          # Google Sheets API client
└── oauth2client (4.1.3)     # Google authentication
```

### Architecture Patterns
- **Dependency Injection**: Services receive dependencies through constructors
- **Single Responsibility**: Each module has one well-defined purpose
- **Strategy Pattern**: Interchangeable clients for different job sources
- **Factory Pattern**: Dynamic client creation based on source type

---

## 🚀 Setup Guide

### Prerequisites
1. Python 3.11 or higher
2. Google Cloud Project with Sheets API enabled
3. Google Service Account credentials
4. Google Sheet for storing job data

### Step 1: Clone & Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### Step 2: Google Cloud Setup

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one

2. **Enable APIs**
   - Enable Google Sheets API
   - Enable Google Drive API

3. **Create Service Account**
   - Go to "IAM & Admin" → "Service Accounts"
   - Click "Create Service Account"
   - Give it a name (e.g., "job-scraper")
   - Grant role: "Editor"

4. **Generate Credentials**
   - Click on the service account
   - Go to "Keys" tab
   - Click "Add Key" → "Create New Key"
   - Select "JSON" format
   - Download the JSON file

### Step 3: Configure Credentials

```bash
# Copy the example file
cp src/config/service-account.json.example src/config/service-account.json

# Replace the contents with your downloaded JSON credentials
# (The file is automatically git-ignored for security)
```

### Step 4: Create Google Sheet

1. Create a new Google Sheet
2. Copy the sheet URL
3. Share the sheet with your service account email (found in the JSON as `client_email`)
4. Give it "Editor" permissions

### Step 5: Set Environment Variables

Create a `.env` file or set environment variables:

```bash
# Required
GOOGLE_SHEETS_URL="https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"

# Optional (defaults to src/config/service-account.json)
SERVICE_ACCOUNT_PATH="src/config/service-account.json"

# Optional (for proxy support)
PROXY_USERNAME="your_username"
PROXY_PASSWORD="your_password"
PROXY_HOST="proxy.example.com"
PROXY_PORT="8000"
```

### Step 6: Run the Scraper

```bash
python main.py
```

**Expected Output:**
```
2025-11-11 16:59:10 - __main__ - INFO - Initializing Job Scraper Service...
2025-11-11 16:59:10 - src.services.scraper_service - INFO - Starting scraping at 2025-11-11 16:59:10
2025-11-11 16:59:10 - src.services.scraper_service - INFO - Starting scraping run...
2025-11-11 16:59:11 - src.clients.sheets_client - INFO - Successfully connected to Google Sheets worksheet: Loker.id
2025-11-11 16:59:11 - src.clients.sheets_client - INFO - Found 150 existing jobs in sheet
2025-11-11 16:59:12 - src.services.scraper_service - INFO - Scraping page 1...
2025-11-11 16:59:15 - src.services.scraper_service - INFO - Page 1 processed. Added 8 new jobs
...
```

---

## 📊 Google Sheets Configuration

### Required Column Headers

Your Google Sheet **MUST** have these exact column headers in the first row:

```
internal_id | source_id | job_source | link | company_name | job_category | title | content | province | city | experience | job_type | level | salary_min | salary_max | education | work_policy | industry | gender | tags
```

### Column Definitions

| **Column #** | **Header Name** | **Data Type** | **Description** | **Example** |
|-------------|----------------|---------------|-----------------|-------------|
| 1 | `internal_id` | UUID String | Unique internal ID (auto-generated) | "550e8400-e29b-41d4-a716-446655440000" |
| 2 | `source_id` | String | Job ID from external source | "12345" or "81990353" |
| 3 | `job_source` | String | Name of the job source | "Loker.id" or "JobStreet" |
| 4 | `link` | URL | Direct link to job posting | "https://www.loker.id/..." |
| 5 | `company_name` | String | Company name | "PT Tech Indonesia" |
| 6 | `job_category` | String | Job category | "Information Technology" |
| 7 | `title` | String | Job title | "Software Engineer" |
| 8 | `content` | HTML String | Cleaned job description | "&lt;h2&gt;Description&lt;/h2&gt;&lt;p&gt;..." |
| 9 | `province` | String | Province/State | "DKI Jakarta" or "Banten" |
| 10 | `city` | String | City/District | "Jakarta Selatan" or "Tangerang" |
| 11 | `experience` | String | Experience level (normalized) | "3-5 Tahun" |
| 12 | `job_type` | String | Job type | "Full Time" or "Part time" |
| 13 | `level` | String | Job level | "Mid Level" or "Senior Level" |
| 14 | `salary_min` | Integer (as string) | Minimum salary in Rupiah | "4000000" |
| 15 | `salary_max` | Integer (as string) | Maximum salary in Rupiah | "5000000" |
| 16 | `education` | String | Education requirement (normalized) | "S1" or "SMA/SMK" |
| 17 | `work_policy` | String | Work policy | "Remote Working" or "On-site Working" |
| 18 | `industry` | String | Industry sector | "Technology" |
| 19 | `gender` | String | Gender requirement | "Laki-laki/Perempuan" |
| 20 | `tags` | String | Combined tags (comma-separated) | "IT, S1, Mid Level, Backend" |

### ID System Explained

**Two-ID System for Better Tracking:**

1. **`internal_id`** (Column A): 
   - Automatically generated UUID by the scraper
   - Ensures global uniqueness across all sources
   - Used for internal documentation and tracking
   - Example: `"550e8400-e29b-41d4-a716-446655440000"`

2. **`source_id`** (Column B):
   - Original job ID from the source (Loker.id, JobStreet, etc.)
   - Used for duplicate detection (prevents re-scraping same job)
   - Source-specific, may overlap between different sources
   - Example: `"12345"` (Loker.id) or `"81990353"` (JobStreet)

**Why Two IDs?**
- `internal_id` = Universal unique identifier for our database
- `source_id` = Prevents duplicate entries from the same source

### Setting Up Your Sheet

**Option 1: Copy-Paste Headers**
```
Copy this line and paste it as the first row in your Google Sheet:

internal_id     source_id       job_source      link    company_name    job_category    title   content province        city    experience      job_type        level   salary_min      salary_max      education       work_policy     industry        gender  tags
```

**Option 2: Manual Entry**
1. Create a new Google Sheet
2. In row 1, enter the 20 column headers exactly as shown above (in English)
3. Make sure there are no typos or extra spaces
4. The scraper will map data to these columns automatically

### Important Notes

- ⚠️ **Column order matters** - The scraper maps data by column name matching
- ⚠️ **Case sensitive** - Use exact casing as shown (e.g., "salary_min" not "Salary_Min")
- ⚠️ **Use English headers** - All column names are now in English for better compatibility
- ⚠️ **No extra columns needed** - The scraper only writes to these 20 columns
- ✅ **Automatic ID generation** - `internal_id` is auto-generated as UUID
- ✅ **Duplicate prevention** - `source_id` is used to check for existing jobs
- ✅ **Automatic mapping** - The transformer uses `headers` from row 1 to map data
- ✅ **Flexible worksheet name** - Can be changed in code (default: "Loker.id")

---

## 🗄️ Supabase Configuration

Supabase provides a scalable PostgreSQL database with a modern developer experience. This section covers how to set up and use Supabase as your storage backend.

### Quick Setup

1. **Create a Supabase Project** (5 minutes)
   - Sign up at [supabase.com](https://supabase.com) (free tier available)
   - Create a new project
   - Note your project URL and API keys

2. **Run the SQL Schema** (2 minutes)
   - Go to SQL Editor in your Supabase dashboard
   - Copy and run the SQL from `supabase/schema.sql`
   - This creates the `job_scraper` table with all necessary columns

3. **Configure Environment Variables**
   - Set `STORAGE_BACKEND=supabase` in your `.env` file
   - Add your Supabase URL and API key

4. **Start Scraping**
   - Run `python main.py` - the scraper will automatically use Supabase

### Detailed Setup Instructions

For complete setup instructions, database schema details, and advanced usage, see:

**📂 [supabase/README.md](supabase/README.md)** - Comprehensive Supabase setup guide

The Supabase README includes:
- Step-by-step project creation
- Database schema explanation
- Status column usage guide
- Common SQL queries
- Troubleshooting tips
- Migration guide from Google Sheets

### Key Differences from Google Sheets

**Status Column (Supabase Only)**

Supabase includes a `status` column to track job lifecycle:
- `active` - Job is currently open (default for new jobs)
- `filled` - Position has been filled
- `expired` - Job posting has expired
- `inactive` - No longer active
- `archived` - Kept for historical data

**Example queries:**
```sql
-- Get only active jobs
SELECT * FROM job_scraper WHERE status = 'active';

-- Update job status
UPDATE job_scraper SET status = 'filled' WHERE source_id = '12345';

-- Count by status
SELECT status, COUNT(*) FROM job_scraper GROUP BY status;
```

**Timestamps**

Supabase automatically tracks:
- `created_at` - When the job was first scraped
- `updated_at` - Last modification time

**Advanced Querying**

```sql
-- Jobs posted in the last 7 days
SELECT * FROM job_scraper 
WHERE created_at > NOW() - INTERVAL '7 days'
AND status = 'active';

-- High-salary tech jobs in Jakarta
SELECT title, company_name, salary_min, salary_max
FROM job_scraper
WHERE city ILIKE '%Jakarta%'
AND salary_min >= 10000000
AND job_category ILIKE '%Technology%'
ORDER BY created_at DESC;
```

### Environment Variables for Supabase

```bash
# Storage backend selection
STORAGE_BACKEND=supabase

# Supabase credentials (required)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here

# Optional: Service role key for admin operations
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

---

## 📖 How to Use

### Basic Usage

**Start the scraper:**
```bash
python main.py
```

The scraper will:
1. Connect to your storage backend (Google Sheets or Supabase)
2. Load existing job IDs (for duplicate detection)
3. Scrape from all enabled sources (sequential or parallel mode)
4. Add new jobs to storage
5. Wait for configured interval (default: 60 minutes)
6. Repeat indefinitely

**Execution Modes:**
- **Sequential** (default): Sources scraped one after another
  - Loker.id → JobStreet → Glints
- **Parallel**: All sources scraped simultaneously
  - Loker.id + JobStreet + Glints at the same time
  - 2-3x faster execution
  
To enable parallel mode, set `SCRAPE_MODE=parallel` in your `.env` file.

### Stopping the Scraper

**Graceful shutdown:**
```bash
# Press Ctrl+C
# The scraper will finish the current job and exit cleanly
```

### Running Once (Manual Mode)

If you want to run a single scraping cycle:

```python
# Modify main.py temporarily:
if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    
    scraper = ScraperService(settings)
    scraper.run_once()  # Run once instead of run_continuous()
```

### Adjusting Scraping Interval

Edit `src/config/settings.py`:

```python
self.scrape_interval_seconds: int = 3600  # Default: 60 minutes

# Change to:
self.scrape_interval_seconds: int = 1800  # 30 minutes
self.scrape_interval_seconds: int = 7200  # 2 hours
```

---

## 🔄 Data Flow & Orchestration

### Complete Scraping Cycle

```
1. INITIALIZATION
   ├─→ Load service account credentials from JSON file
   ├─→ Connect to Google Sheets
   ├─→ Fetch existing job IDs from column C (id column)
   └─→ Create in-memory set for duplicate detection

2. SCRAPING LOOP (per page)
   ├─→ Fetch page from Loker.id API
   │   └─→ GET /cari-lowongan-kerja/page/{N}?_data
   │
   ├─→ FOR each job in response:
   │   │
   │   ├─→ Check if job ID exists in set
   │   │   └─→ If yes: SKIP (duplicate)
   │   │   └─→ If no: CONTINUE
   │   │
   │   ├─→ TRANSFORM job data:
   │   │   ├─→ Normalize education level
   │   │   ├─→ Extract salary min/max as integers
   │   │   ├─→ Normalize experience level
   │   │   ├─→ Convert remote boolean to text
   │   │   ├─→ Clean HTML content
   │   │   └─→ Build combined tags
   │   │
   │   └─→ APPEND to Google Sheets:
   │       ├─→ Check rate limit
   │       ├─→ Write row to sheet
   │       └─→ Add ID to in-memory set
   │
   ├─→ Sleep 1 second (page delay)
   └─→ Increment page number

3. COMPLETION
   ├─→ Log total new jobs added
   ├─→ Sleep 60 minutes
   └─→ REPEAT from step 2
```

### Detailed Data Transformation

**Raw API Job Object:**
```json
{
  "id": 12345,
  "title": "Software Engineer",
  "company_name": "PT Tech Indonesia",
  "education": "Sarjana / S1",
  "job_salary": "Rp.4 – 5 Juta",
  "job_experience": "2-3 Tahun",
  "is_remote": false,
  "locations": [
    {"name": "DKI Jakarta"},
    {"name": "Jakarta Selatan"}
  ]
}
```

**Transformed Row Data:**
```python
[
  "12345",                      # id
  "Loker.id",                   # sumber_lowongan
  "https://...",                # link
  "PT Tech Indonesia",          # company_name
  "Information Technology",     # kategori_pekerjaan
  "Software Engineer",          # title
  "<h2>Description</h2>...",    # content (cleaned HTML)
  "DKI Jakarta",                # lokasi_provinsi
  "Jakarta Selatan",            # lokasi_kota
  "3-5 Tahun",                  # pengalaman (normalized)
  "Full Time",                  # tipe_pekerjaan
  "Mid Level",                  # level
  "4000000",                    # salary_min
  "5000000",                    # salary_max
  "S1",                         # pendidikan (normalized)
  "On-site Working",            # kebijakan_kerja
  "Technology",                 # industry
  "Laki-laki/Perempuan",        # gender
  "IT, S1, Mid Level, Backend"  # tag (combined)
]
```

---

## ⚙️ Configuration Options

### Environment Variables

| **Variable** | **Required** | **Default** | **Description** |
|-------------|-------------|-------------|-----------------|
| `STORAGE_BACKEND` | ❌ No | `google_sheets` | Storage backend ("google_sheets" or "supabase") |
| `GOOGLE_SHEETS_URL` | ✅ If using Sheets | - | Full URL to Google Sheet |
| `SUPABASE_URL` | ✅ If using Supabase | - | Supabase project URL |
| `SUPABASE_KEY` | ✅ If using Supabase | - | Supabase API key |
| `SUPABASE_SERVICE_ROLE_KEY` | ❌ No | - | Supabase service role key (optional) |
| `SERVICE_ACCOUNT_PATH` | ❌ No | `src/config/service-account.json` | Path to Google credentials file |
| `SCRAPE_MODE` | ❌ No | `sequential` | Execution mode ("sequential" or "parallel") |
| `ENABLE_LOKER` | ❌ No | `true` | Enable/disable Loker.id scraping |
| `ENABLE_JOBSTREET` | ❌ No | `false` | Enable/disable JobStreet scraping |
| `ENABLE_GLINTS` | ❌ No | `true` | Enable/disable Glints scraping |
| `MAX_PAGES_LOKER` | ❌ No | `0` | Max pages for Loker.id (0 = unlimited) |
| `MAX_PAGES_JOBSTREET` | ❌ No | `10` | Max pages for JobStreet |
| `MAX_PAGES_GLINTS` | ❌ No | `10` | Max pages for Glints |
| `SCRAPE_INTERVAL_SECONDS` | ❌ No | `3600` | Time between scraping cycles (seconds) |
| `PROXY_USERNAME` | ❌ No | - | Proxy authentication username |
| `PROXY_PASSWORD` | ❌ No | - | Proxy authentication password |
| `PROXY_HOST` | ❌ No | `la.residential.rayobyte.com` | Proxy server hostname |
| `PROXY_PORT` | ❌ No | `8000` | Proxy server port |

### Rate Limit Settings

Edit `src/config/settings.py`:

```python
# Google Sheets API quotas
self.read_requests_per_minute: int = 300        # Max reads/minute
self.write_requests_per_minute: int = 60        # Max writes/minute
self.total_requests_per_100_seconds: int = 500  # Total quota per 100s

# Scraping behavior
self.scrape_interval_seconds: int = 3600  # Time between cycles (60 min)
self.page_delay_seconds: int = 1          # Delay between pages
self.request_timeout_seconds: int = 30    # HTTP timeout
```

---

## 🔌 Adding New Job Sources

The architecture is designed to make adding new sources straightforward:

### Step 1: Create Client Directory

```bash
mkdir src/clients/linkedin
touch src/clients/linkedin/__init__.py
touch src/clients/linkedin/linkedin_client.py
```

### Step 2: Implement Client

```python
# src/clients/linkedin/linkedin_client.py

import requests
from typing import Optional, Tuple, List, Dict, Any

class LinkedInClient:
    """Client for interacting with LinkedIn job API."""
    
    def __init__(self, api_key: str, timeout: int = 30):
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://api.linkedin.com/v2/jobs"
    
    def fetch_page(self, page_num: int) -> Tuple[Optional[List[Dict[str, Any]]], bool]:
        """
        Fetches a single page of job listings from LinkedIn.
        
        Returns:
            Tuple of (jobs_data, has_more)
        """
        # Your LinkedIn API implementation here
        pass
```

### Step 3: Create Transformer (if needed)

If LinkedIn has different data format, create a transformer:

```python
# src/transformers/linkedin_transformer.py

class LinkedInTransformer:
    """Transforms LinkedIn job data to standard format."""
    
    def transform_job(self, job: Dict[str, Any], headers: List[str]) -> List[str]:
        # Map LinkedIn fields to standard columns
        pass
```

### Step 4: Update Scraper Service

```python
# src/services/scraper_service.py

from src.clients.linkedin.linkedin_client import LinkedInClient

# In __init__:
self.linkedin_client = LinkedInClient(api_key=settings.linkedin_api_key)

# Add new scraping method:
def scrape_linkedin(self):
    # LinkedIn scraping logic
    pass
```

### Step 5: Update Configuration

```python
# src/config/settings.py

self.linkedin_api_key: str = os.getenv("LINKEDIN_API_KEY", "")
```

**That's it!** Your new source is integrated and ready to use.

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "Service account file not found"

**Problem:** Can't find `src/config/service-account.json`

**Solution:**
```bash
# Check file exists
ls -la src/config/service-account.json

# If not, copy from example
cp src/config/service-account.json.example src/config/service-account.json

# Then add your real credentials
```

#### 2. "Failed to connect to Google Sheets"

**Problem:** Authentication or permission error

**Solution:**
- Verify service account email has access to the sheet
- Check that both Google Sheets API and Drive API are enabled
- Ensure the JSON credentials are valid (not corrupted)
- Make sure the sheet URL is correct

#### 3. "No jobs added / All duplicates"

**Problem:** All jobs already exist in the sheet

**Solution:**
- This is normal if you've already scraped
- Delete some rows from the sheet to test
- Or wait for new jobs to be posted on Loker.id

#### 4. "Rate limit errors"

**Problem:** Hitting Google Sheets API quotas

**Solution:**
- Increase delays in `settings.py`
- Reduce scraping frequency
- The rate limiter should handle this automatically

#### 5. "Module not found" errors

**Problem:** Missing Python dependencies

**Solution:**
```bash
pip install -r requirements.txt
```

### Debug Mode

Enable detailed logging:

```python
# main.py
logging.basicConfig(
    level=logging.DEBUG,  # Change from INFO to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

---

## 📚 Additional Documentation

- **[LOKER_ORCHESTRATION.md](LOKER_ORCHESTRATION.md)** - Deep dive into Loker.id data flow
- **[SALARY_MAPPING_UPDATE.md](SALARY_MAPPING_UPDATE.md)** - Salary extraction documentation
- **[src/config/README.md](src/config/README.md)** - Credentials setup guide

---

## 📝 License

This project is for educational and personal use.

---

## 🤝 Contributing

To contribute:
1. Add new job sources following the architecture
2. Document your changes
3. Test thoroughly before deploying
4. Update this README if needed

---

## 🎯 Future Enhancements

- [ ] Add LinkedIn integration
- [ ] Add Indeed integration
- [ ] Add JobStreet integration
- [ ] Database support (PostgreSQL)
- [ ] Web dashboard for monitoring
- [ ] Email notifications for new jobs
- [ ] Advanced filtering by keywords
- [ ] Salary trend analytics
- [ ] Multi-sheet support (one per source)

---

**Built with ❤️ for automated job aggregation**
