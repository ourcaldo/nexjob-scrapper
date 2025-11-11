# Transformers

The transformers module is responsible for converting raw job data from various sources into a standardized format that can be stored in Google Sheets.

## Overview

Each job source (Loker.id, JobStreet, LinkedIn, etc.) has its own unique data structure and field names. The transformers normalize this data into a consistent format with standardized field values.

## Architecture

We use a **separate transformer for each source** approach. This provides:
- **Clean separation**: Changes to one source won't affect others
- **Easy testing**: Each transformer can be tested independently
- **Easy extension**: Adding new sources is straightforward
- **Clear code flow**: Obvious which transformer handles which source

## File Structure

```
src/transformers/
├── __init__.py
├── README.md                    # This file
├── content_cleaner.py          # Shared HTML cleaning utility
├── loker_transformer.py        # Loker.id specific transformer
└── jobstreet_transformer.py    # JobStreet specific transformer
```

## Components

### content_cleaner.py
Shared utility for cleaning HTML content. Used by all transformers to:
- Remove HTML tags
- Convert HTML entities to text
- Clean up whitespace
- Normalize text formatting

### loker_transformer.py
Transforms Loker.id job data from their API format.

**Input:** Single API response with complete job data

**Key transformations:**
- Education normalization: `"Sarjana / S1"` → `"S1"`
- Salary range extraction: `"Rp.4 – 5 Juta"` → `(4000000, 5000000)`
- Experience normalization: `"2-3 Tahun"` → `"3-5 Tahun"`
- Work policy conversion: `is_remote: true` → `"Remote Working"`
- HTML content cleaning
- Source tagging: `"Loker.id"`

### jobstreet_transformer.py
Transforms JobStreet job data from combined API + HTML scraping.

**Input:** Combined data (search API + detailed HTML scrape)

**Key transformations:**
- Job ID extraction from multiple possible locations
- Company name extraction from nested structure
- Location parsing from `seoHierarchy` (province/city)
- Work arrangement mapping: `"On-site"` → `"On-site Working"`
- Job level inference from title keywords
- Pre-extracted education/experience from HTML
- Salary parsing (often empty)
- HTML content cleaning
- Source tagging: `"JobStreet"`

## How It Works

### Loker.id Flow
```python
# In ScraperService:
jobs_data, has_more = self.loker_client.fetch_page(page_num)

for job in jobs_data:
    headers = self.sheets_client.get_headers()
    row_data = self.loker_transformer.transform_job(job, headers)
    self.sheets_client.append_row(row_data)
```

### JobStreet Flow
```python
# In ScraperService:
jobs_data, has_more, total = self.jobstreet_client.fetch_search_page(page_num)

for job in jobs_data:
    job_id = extract_job_id(job)
    job_detail = self.jobstreet_client.fetch_job_detail(job_id)
    combined_job = {**job, **job_detail}
    
    headers = self.sheets_client.get_headers()
    row_data = self.jobstreet_transformer.transform_job(combined_job, headers)
    self.sheets_client.append_row(row_data)
```

## Key Differences Between Transformers

| Aspect | LokerTransformer | JobStreetTransformer |
|--------|------------------|---------------------|
| Input | Single API response | Combined (API + HTML) |
| Education | Normalizes from API field | Uses pre-extracted from HTML |
| Experience | Normalizes from API field | Uses pre-extracted from HTML |
| Salary | Always provided, needs mapping | Often empty, needs parsing |
| Location | Simple array | Nested seoHierarchy |
| Work Policy | Boolean → text | Structured object → text |
| Job Level | Direct from API | Inferred from title |

## Usage in ScraperService

### Initialization
```python
def __init__(self, settings: Settings):
    self.loker_client = LokerClient(...)
    self.jobstreet_client = JobStreetClient(...)
    
    # Initialize transformers
    self.loker_transformer = LokerTransformer()
    self.jobstreet_transformer = JobStreetTransformer()
```

### Processing Methods
```python
def process_loker_job(self, job: dict) -> bool:
    row_data = self.loker_transformer.transform_job(job, headers)
    # ...

def process_jobstreet_job(self, job: dict) -> bool:
    row_data = self.jobstreet_transformer.transform_job(job, headers)
    # ...
```

## Adding a New Source

To add support for a new job source (e.g., LinkedIn):

1. **Create transformer file**: `src/transformers/linkedin_transformer.py`
```python
from typing import Dict, Any, List
from src.transformers.content_cleaner import ContentCleaner

class LinkedInTransformer:
    def __init__(self):
        self.content_cleaner = ContentCleaner()
    
    def transform_job(self, job: Dict[str, Any], headers: List[str]) -> List[str]:
        # Transform LinkedIn-specific fields
        # Return list matching headers
        pass
```

2. **Initialize in ScraperService**: `src/services/scraper_service.py`
```python
def __init__(self, settings: Settings):
    # ...
    self.linkedin_transformer = LinkedInTransformer()
```

3. **Create processing method**: `src/services/scraper_service.py`
```python
def process_linkedin_job(self, job: dict) -> bool:
    headers = self.sheets_client.get_headers()
    row_data = self.linkedin_transformer.transform_job(job, headers)
    return self.sheets_client.append_row(row_data)
```

4. **Create scraping method**: `src/services/scraper_service.py`
```python
def scrape_linkedin_all_pages(self) -> int:
    # Implement LinkedIn scraping logic
    pass
```

## Testing

Each transformer can be tested independently:

```python
# Test Loker transformer
from src.transformers.loker_transformer import LokerTransformer

loker_transformer = LokerTransformer()
headers = ["id", "sumber_lowongan", "company_name", ...]
row_data = loker_transformer.transform_job(loker_job_data, headers)
print(row_data)

# Test JobStreet transformer
from src.transformers.jobstreet_transformer import JobStreetTransformer

jobstreet_transformer = JobStreetTransformer()
row_data = jobstreet_transformer.transform_job(jobstreet_job_data, headers)
print(row_data)
```

## Related Documentation

- Client implementations: `src/clients/`
- Service orchestration: `src/services/scraper_service.py`
- Configuration: `src/config/settings.py`
