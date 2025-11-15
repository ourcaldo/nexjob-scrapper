# Job Scraper - Multi-Source Job Aggregation System

## Overview
This is a production-ready Python-based web scraper built with microservice architecture that automatically collects job postings from multiple sources (Loker.id, JobStreet, and Glints) and stores them in either **Google Sheets** or **Supabase (PostgreSQL)**. The scraper runs continuously with 60-minute intervals between scraping cycles.

For complete documentation, see **[README.md](README.md)**

## Project Structure (Multi-Source Architecture)
```
src/
├── config/
│   ├── settings.py               # Configuration loader
│   ├── service-account.json      # Google credentials (git-ignored)
│   └── service-account.json.example  # Template file
├── clients/
│   ├── loker/                    # Loker.id source
│   │   └── loker_client.py       # Loker.id API client
│   ├── jobstreet/                # JobStreet source
│   │   └── jobstreet_client.py   # JobStreet API + HTML scraper
│   ├── glints/                   # Glints source
│   │   ├── glints_client.py      # Glints GraphQL API client
│   │   └── GLINTS_ORCHESTRATION.md  # Complete Glints documentation
│   ├── linkedin/                 # LinkedIn source (future)
│   ├── base_storage_client.py    # Storage backend abstraction
│   ├── sheets_client.py          # Google Sheets storage backend
│   └── supabase_client.py        # Supabase (PostgreSQL) storage backend
├── services/
│   └── scraper_service.py        # Main orchestration service
├── transformers/
│   ├── loker_transformer.py      # Loker.id data transformation
│   ├── jobstreet_transformer.py  # JobStreet data transformation
│   ├── glints_transformer.py     # Glints data transformation
│   └── content_cleaner.py        # HTML content cleaning
└── utils/
    └── rate_limiter.py           # API rate limiting utility

main.py                           # Application entry point
requirements.txt                  # Python dependencies
```

## Features
- **Flexible Storage**: Choose between Google Sheets (simple) or Supabase (scalable database)
- Automatic pagination until no more jobs are found (404 response)
- Duplicate prevention by checking existing job IDs
- Rate limiting to respect API limits
- Data cleaning and normalization (education, salary, experience levels)
- HTML content parsing and formatting
- Continuous operation with 60-minute intervals
- **Status tracking** (active, filled, expired) when using Supabase
- Optional proxy support

## Architecture Highlights

### Microservice Design
- **Separation of Concerns**: Each module has a single, well-defined responsibility
- **Dependency Injection**: Services receive dependencies through constructors
- **Reusable Components**: Rate limiter, transformers, and clients can be used independently
- **Professional Logging**: Uses Python's logging framework instead of print statements
- **Type Safety**: Type hints throughout for better code quality

### Key Components

**Settings (config/settings.py)**
- Centralized configuration management
- Environment variable loading
- Proxy configuration builder
- Configuration validation

**LokerClient (clients/loker_client.py)**
- Fetches job pages from Loker.id API
- Handles HTTP requests with optional proxy support
- Timeout and error handling

**Storage Clients (clients/)**
- **BaseStorageClient**: Abstract interface for storage backends
- **SheetsClient**: Google Sheets connection and authentication, read/write with rate limiting
- **SupabaseClient**: PostgreSQL database operations with status tracking
- Duplicate detection via existing ID lookup across all backends

**JobTransformer (transformers/job_transformer.py)**
- Normalizes education, salary, experience, work policy
- Builds structured job dictionaries
- Maps data to Google Sheets columns

**ContentCleaner (transformers/content_cleaner.py)**
- Cleans raw HTML job descriptions
- Converts to structured format (headings, lists, paragraphs)
- Removes duplicates and formats consistently

**RateLimiter (utils/rate_limiter.py)**
- Enforces Google Sheets API quotas
- Tracks read/write requests per minute
- Prevents API ban with automatic delays

**ScraperService (services/scraper_service.py)**
- Orchestrates the entire scraping workflow
- Coordinates all components
- Handles pagination and continuous operation

## Recent Changes

### 2025-11-15 - Supabase Storage Backend Support
- **Flexible Storage Architecture**: Added support for Supabase as an alternative to Google Sheets
  - **Storage Abstraction Layer**: Created `BaseStorageClient` interface for pluggable storage backends
  - **Supabase Client**: Full PostgreSQL database support with automatic indexing
  - **Status Column**: Track job lifecycle (active, filled, expired, archived) - Supabase only
  - **Factory Pattern**: Automatic client selection based on `STORAGE_BACKEND` env variable
- **New Components**:
  - `base_storage_client.py`: Abstract interface for storage backends
  - `supabase_client.py`: Supabase PostgreSQL implementation
  - `supabase/schema.sql`: Complete database schema with indexes
  - `supabase/README.md`: Comprehensive Supabase setup guide
- **Environment Variables**:
  - `STORAGE_BACKEND` - Choose "google_sheets" or "supabase" (default: google_sheets)
  - `SUPABASE_URL` - Supabase project URL
  - `SUPABASE_KEY` - Supabase API key
  - `SUPABASE_SERVICE_ROLE_KEY` - Optional service role key for admin operations
- **Updated Components**:
  - Refactored `SheetsClient` to implement `BaseStorageClient` interface
  - Updated `ScraperService` to use factory pattern for storage client creation
  - Enhanced `settings.py` with storage backend validation

### 2025-11-12 - Glints Integration with Two-Step GraphQL API
- **Complete Glints Support**: Added full integration with Glints job platform
  - **Two-Step API Architecture**: 
    - Step 1: Search API (`searchJobsV3`) - Fetches paginated job list
    - Step 2: Detail API (`getJobDetailsById`) - Fetches complete job details for each job
  - **Status Filtering**: Only processes jobs with `status === "OPEN"`
  - **DraftJS Description Parsing**: Converts Glints' JSON descriptions to HTML
  - **Robust Error Handling**: Graceful fallback when detail fetch fails
- **New Components**:
  - `GlintsClient`: GraphQL API client with dual endpoints
  - `GlintsTransformer`: Data normalization with education, experience, and work arrangement mapping
  - `GLINTS_ORCHESTRATION.md`: Complete technical documentation
- **Environment Variables**:
  - `ENABLE_GLINTS` - Enable/disable Glints scraping (default: true)
  - `MAX_PAGES_GLINTS` - Limit pages to scrape (default: 10, 0 = unlimited)

### 2025-11-11 - Google Sheets Column Structure Enhancement
- **Dual-ID System**: Added two-column ID tracking
  - `internal_id` (Column A): Auto-generated UUID for universal unique tracking
  - `source_id` (Column B): Original job ID from source for duplicate prevention
- **English Column Headers**: Translated all column names from Indonesian to English
  - `sumber_lowongan` → `job_source`
  - `kategori_pekerjaan` → `job_category`
  - `lokasi_provinsi` → `province`
  - `lokasi_kota` → `city`
  - `pengalaman` → `experience`
  - `tipe_pekerjaan` → `job_type`
  - `pendidikan` → `education`
  - `kebijakan_kerja` → `work_policy`
  - `tag` → `tags`
- **Total Columns**: Increased from 19 to 20 columns
- **Updated Components**:
  - LokerTransformer: Added uuid import and new column mapping
  - JobStreetTransformer: Added uuid import and new column mapping
  - SheetsClient: Updated duplicate detection to read from column B (source_id)
  - README.md: Updated with new column structure documentation

### 2025-11-11 - Architecture Improvements
- **Major Refactor**: Transformed monolithic script into microservice architecture
- Separated concerns into dedicated modules (clients, transformers, services, utils)
- **Multi-Source Architecture**: Reorganized clients by source (loker/, linkedin/, etc.)
- **Credentials Loading**: Changed from environment variable to JSON file loading
  - Credentials now loaded from `src/config/service-account.json`
  - File is git-ignored for security
  - Example file provided at `src/config/service-account.json.example`
- Added professional logging framework
- Improved error handling with try-catch blocks
- Fixed edge case bug in experience mapping
- Made all components independently testable
- Added comprehensive docstrings

## Required Configuration

### Service Account File (Required)
- Place your Google Service Account JSON file at `src/config/service-account.json`
- Copy from `src/config/service-account.json.example` as a template
- This file is automatically git-ignored for security

### Environment Variables

#### Storage Backend (Required):
- `STORAGE_BACKEND` - Choose "google_sheets" or "supabase" (default: google_sheets)

#### Google Sheets (Required if using Google Sheets):
- `GOOGLE_SHEETS_URL` - Full URL to the Google Sheets spreadsheet

#### Supabase (Required if using Supabase):
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase anon/public API key
- `SUPABASE_SERVICE_ROLE_KEY` - Optional service role key for admin operations

#### Optional - General:
- `SERVICE_ACCOUNT_PATH` - Custom path to service account JSON (default: `src/config/service-account.json`)
- `PROXY_USERNAME` - Proxy authentication username
- `PROXY_PASSWORD` - Proxy authentication password
- `PROXY_HOST` - Proxy server hostname (default: la.residential.rayobyte.com)
- `PROXY_PORT` - Proxy server port (default: 8000)

#### Optional - Source Control:
- `ENABLE_LOKER` - Enable Loker.id scraping (default: true)
- `ENABLE_JOBSTREET` - Enable JobStreet scraping (default: false)
- `ENABLE_GLINTS` - Enable Glints scraping (default: true)
- `MAX_PAGES_LOKER` - Max pages for Loker.id (default: 0 = unlimited)
- `MAX_PAGES_JOBSTREET` - Max pages for JobStreet (default: 10)
- `MAX_PAGES_GLINTS` - Max pages for Glints (default: 10)

## Setup Instructions

### 1. Google Sheets API Setup
1. Create a Google Cloud project
2. Enable Google Sheets API and Google Drive API
3. Create a service account and download the JSON credentials
4. Share your Google Sheet with the service account email

### 2. Add Service Account Credentials
1. Copy `src/config/service-account.json.example` to `src/config/service-account.json`
2. Replace the contents with your actual Google Service Account JSON
3. The file is automatically git-ignored for security

### 3. Configure Environment Variables
Set the following in Replit Secrets or .env file:
- `GOOGLE_SHEETS_URL` - The full URL of your Google Sheets spreadsheet

### 4. Optional Proxy Configuration
If you want to use proxies (recommended for production to avoid rate limiting):
- Set `PROXY_USERNAME` and `PROXY_PASSWORD`
- Optionally customize `PROXY_HOST` and `PROXY_PORT`

## Running the Scraper

```bash
python main.py
```

The scraper will automatically:
1. Connect to Google Sheets
2. Scrape all available job pages from Loker.id
3. Check for duplicates and only add new jobs
4. Wait 60 minutes before the next cycle
5. Continue indefinitely until stopped

## Data Collected (20 Columns)

### Current Google Sheets Structure
```
internal_id | source_id | job_source | link | company_name | job_category | title | content | province | city | experience | job_type | level | salary_min | salary_max | education | work_policy | industry | gender | tags
```

Each job record includes:
- **internal_id**: Auto-generated UUID for universal tracking
- **source_id**: Original job ID from the source (for duplicate detection)
- **job_source**: Platform name (Loker.id, JobStreet, etc.)
- **link**: Direct URL to job posting
- **company_name**: Employer name
- **job_category**: Job category/field
- **title**: Job title
- **content**: Full job description (cleaned HTML)
- **province**: Location province/state
- **city**: Location city/district
- **experience**: Experience requirements (normalized)
- **job_type**: Employment type (Full Time, Part Time, etc.)
- **level**: Job level (Entry, Mid, Senior, etc.)
- **salary_min**: Minimum salary in Rupiah
- **salary_max**: Maximum salary in Rupiah
- **education**: Education requirement (normalized: SMA/SMK, D1-D4, S1, S2, S3)
- **work_policy**: Work arrangement (Remote, On-site, Hybrid)
- **industry**: Industry sector
- **gender**: Gender requirement
- **tags**: Combined tags (comma-separated)

## Rate Limiting
The scraper implements strict rate limiting to comply with API quotas:
- Google Sheets Read: 290 requests per minute
- Google Sheets Write: 55 requests per minute
- Loker.id: 1 request per second
- 1 second delay between page requests
- 1 second delay between sheet writes

## Dependencies
- Python 3.11+
- requests - HTTP requests
- beautifulsoup4 - HTML parsing
- gspread - Google Sheets API
- oauth2client - Google authentication

## Notes
- The scraper runs continuously until manually stopped
- Graceful shutdown on SIGINT/SIGTERM signals
- All credentials must be stored in environment variables
- Never commit credential files to version control
