# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] — 2025-07

### Added — Karir.com Integration

- **`src/clients/karir/karir_client.py`** — New HTTP client for Karir.com REST API
  - `fetch_page(offset)` — POST `/v2/search/opportunities` with keyword `""`, returns up to 20 jobs per page
  - `fetch_job_detail(opportunity_id)` — POST `/v1/opportunity/detail`, retrieves full job content
  - `PAGE_SIZE = 20` class attribute (read by scraper service to advance offset)
  - All detail fetches wrapped with `retry_request` for resilience
  - No proxy required (Karir.com is an open API)

- **`src/clients/karir/__init__.py`** — Package init exposing `KarirClient`

- **`src/transformers/karir_transformer.py`** — Transformer mapping Karir.com raw data to universal schema
  - `internal_id` generated via `uuid.uuid4()` (consistent with all other transformers)
  - `_experience_years_to_range(years)` — converts raw integer (e.g. `1`) to experience band string
  - `_map_work_policy(workplace_type)` — maps Karir workplace codes to standard `work_policy` values
  - `job_type`: "Tidak Disebutkan" normalized → `"Full Time"` via `FieldMappers.normalize_job_type()`
  - `education`: `degrees[0]` passed through `FieldMappers.normalize_education()`
  - `content`: concatenated HTML from `responsibilities` + `requirements`
  - No `status` field set (DB default `active` handles it)

- **`src/config/settings.py`** — Added Karir.com config fields
  - `enable_karir: bool` — default `True`
  - `max_pages_karir: int` — default `0` (unlimited)
  - `validate()` updated — `enable_karir` included in "at least one source enabled" check

- **`.env`** — Added `ENABLE_KARIR=true`, `MAX_PAGES_KARIR=0`

- **`src/services/scraper_service.py`** — Full Karir.com orchestration wiring
  - `process_karir_job(job, detail)` — deduplication + transform + store for a single job
  - `scrape_karir_all_pages()` — pagination loop using `KarirClient.fetch_page` + `fetch_job_detail`
  - `karir_worker()` — thread entry point for parallel mode
  - `run_once()` — now calls `scrape_karir_all_pages()` when `enable_karir` is True
  - `run_once_parallel()` — Karir worker added, `max_workers` bumped to 4
  - `run_continuous()` — Karir included in continuous loop

---

### Fixed — Audit Findings (from `docs/CODE_REVIEW.md`)

- **`src/services/scraper_service.py`**
  - `offset += self.karir_client.PAGE_SIZE` — was hardcoded `20`, now uses class attribute
  - Detail-fetch failure log now includes both `title` and `company_name`
  - Docstrings cleaned — removed stale "Google Sheets" references

- **`src/transformers/loker_transformer.py`**
  - Salary fields returned as `int` directly, removed unnecessary `str()` wrapping

- **`src/config/settings.py`**
  - `validate()` — `enable_karir` now counted in multi-source check (was silently ignored)

---

### Added — Documentation

- **`docs/CODE_REVIEW.md`** — Full deep-dive audit report
  - High / Medium / Low findings with status (Fixed / Rejected / Deferred)
  - Architecture notes: transformer vs FieldMappers, scrape-to-DB flow
  - Real-case example: job id `1400774` raw → transformed → stored values

- **`README.md`** — Updated to reflect current project state
  - Intro updated: now mentions 4 sources + Supabase as primary backend
  - "Current Sources" section: added ✅ Glints and ✅ Karir.com entries
  - "Data Flow & Orchestration" section fully rewritten:
    - ASCII pipeline diagram (6 steps: Fetch → Dedup → Transform → Store → Track → Sleep)
    - Universal DB schema field reference table
    - Source-by-source comparison table (protocol, auth, proxy, HTTP library, pagination type)
    - Explanation of why `curl_cffi` is used for Glints (Cloudflare TLS fingerprinting)
  - Config table: added `ENABLE_KARIR`, `MAX_PAGES_KARIR`, `ENABLE_GLINTS`, `MAX_PAGES_GLINTS` rows
  - "Future Enhancements": removed already-completed items (JobStreet, Glints, PostgreSQL/Supabase)

- **`CHANGELOG.md`** — This file (initial creation)

---

## [0.4.0] — 2025-07 (commit `84554f9`)

### Added
- Glints integration via `curl_cffi` with Chrome 120 TLS impersonation to bypass Cloudflare
- `retry_request` utility in `src/utils/` for resilient HTTP calls
- `FieldMappers` standardization across all transformers (`field_mappers.py`)
- `.dockerignore` to exclude secrets and caches from Docker builds

### Fixed
- Various field mapping inconsistencies across Loker.id, JobStreet, Glints transformers

---

## [0.3.0] — 2025 (commit `c1378e3`)

### Added
- Docker + Docker Compose support for Coolify deployment
- `Dockerfile` and `docker-compose.yaml`

---

## [0.2.0] — 2025 (commit `a920910`)

### Changed
- Reorganized project: removed Replit-specific files, moved documentation to `docs/`

---

## [0.1.x] — 2025 (commits `e1a7935` – `4083f54`)

### Added
- JobStreet integration (REST API + HTML scraping)
- Supabase (PostgreSQL) as primary storage backend
- Parallel scraping mode (`SCRAPE_MODE=parallel`)
- Duplicate prevention across storage backends
- Education/experience/job-type field normalization
- HTML content cleaning for job descriptions
- Rate limiting for Google Sheets API quota compliance

### Changed
- Standardized diploma education levels to single fallback value
- Unified experience, job type, and education fields across all sources

---

## [0.1.0] — Initial Release

### Added
- Loker.id scraping via REST API
- Google Sheets storage backend
- Basic data normalization (salary, education, experience)
- Continuous operation mode with configurable interval
- Proxy support for IP rotation
