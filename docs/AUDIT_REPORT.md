# nexjob-scrapper — Full Audit Report

**Date:** 2026-02-23  
**Scope:** Full codebase review — all clients, transformers, services, config, and infrastructure  
**Sources Active:** Loker.id · JobStreet · Glints  

---

## Priority Levels

| Level | Meaning |
|-------|---------|
| **C** | Critical — breaks the system, deployment fails, or silent data corruption |
| **H** | High — significant bug that produces wrong output or silently skips data |
| **M** | Medium — functional degradation, edge-case failures, or data quality issues |
| **L** | Low — minor code quality, misleading logs, or outdated artefacts |
| **E** | Enhancement — new features or architectural improvements |

---

## Issues Tracker

| Code | Level | Issue | File Path | Status |
|------|-------|-------|-----------|--------|
| C-001 | **C** | `requirements.txt` has every package listed 3–6 times with mixed pinned/unpinned versions. `pip install -r requirements.txt` installs conflicting versions and may silently downgrade packages, breaking the runtime. | `requirements.txt` | ✅ Resolved |
| C-002 | **C** | `Dockerfile` installs dependencies from the broken `requirements.txt` — Docker builds will inherit the duplicate/conflict problem from C-001, potentially producing unpredictable container environments. | `Dockerfile` | ✅ Resolved |
| C-003 | **C** | `pyproject.toml` is missing `supabase`, `python-dotenv`, and `beautifulsoup4` from its `dependencies` list. Any install via `uv` or PEP 517 tooling will produce a broken environment that crashes at import time. | `pyproject.toml` | ✅ Resolved |
| H-001 | **H** | `SheetsClient.get_existing_ids()` hardcodes column positions: `col_values(2)` = source_id, `col_values(3)` = job_source. If the Google Sheet columns are ever reordered, renamed, or a new leading column is inserted, deduplication silently fails and every job gets re-inserted as a duplicate on every run. | `src/clients/sheets_client.py` | ⏭️ Skipped |
| H-002 | ~~**H**~~ → **L** | `LokerClient.fetch_page()` always returns `has_more=True` regardless of API response, but this is not actually a bug. Loker.id has no `has_more` field in its API response. Pagination termination is fully handled by the service layer's `if not jobs_data: break` guard, which fires correctly on both HTTP 404 (`None`) and empty `jobs: []` responses. The hardcoded `True` is misleading but harmless. Downgraded to L. | `src/clients/loker/loker_client.py` | ⬇️ Downgraded to L |
| H-003 | **H** | `JobStreetClient._extract_experience()` — the `fresh graduate` detection branch returns `"1-3 Tahun"`, which is **identical** to the final default `return "1-3 Tahun"`. The branch is therefore dead code. | `src/clients/jobstreet/jobstreet_client.py` | ⏭️ Skipped (JobStreet deferred) |
| H-004 | **H** | `JobStreetClient._extract_education()` calls `soup.get_text().upper()` and scans the **entire page** for education keywords instead of scoping to the `jobAdDetails` element like the other extraction methods do. | `src/clients/jobstreet/jobstreet_client.py` | ⏭️ Skipped (JobStreet deferred) |
| H-005 | **H** | In `parallel` mode, `run_once_parallel()` calls `initialize_storage_client()` internally, which resets `self.existing_ids` if storage was already initialized by `run_continuous()`, causing all previously-processed jobs to appear as new duplicates. | `src/services/scraper_service.py` | ✅ Resolved |
| H-006 | **H** | `GlintsTransformer.transform_job()` hardcodes `"gender": "Laki-laki/Perempuan"` for every Glints job. The Glints detail GraphQL query explicitly returns a `gender` field which is fetched but completely ignored. | `src/transformers/glints_transformer.py` | ✅ Resolved |
| M-001 | **M** | No HTTP retry logic exists in any client (`LokerClient`, `JobStreetClient`, `GlintsClient`). A single transient network error (timeout, 503, connection reset) causes the job or page to be permanently skipped for the entire run. With `SCRAPE_INTERVAL_SECONDS=3600`, popular jobs posted and missed in one run may be filled before the next run — resulting in silent permanent data loss. | `src/clients/loker/loker_client.py`, `src/clients/jobstreet/jobstreet_client.py`, `src/clients/glints/glints_client.py` | ✅ Resolved |
| M-002 | **M** | `LokerTransformer.transform_job()` builds province from `job["locations"][0]["parent"]["name"]`. The conditional guard checks `job["locations"][0].get("parent")` but then immediately accesses `["name"]` as a direct key — if `parent` is an empty dict `{}` (valid JSON but no `name` key), this raises a `KeyError` and the job fails to process. | `src/transformers/loker_transformer.py` | ✅ Resolved |
| M-003 | **M** | `GlintsTransformer.parse_json_description()` uses a bare `except:` clause which catches **all** exceptions including `SystemExit` and `KeyboardInterrupt`. This can mask serious errors, interfere with graceful shutdown, and makes debugging impossible. | `src/transformers/glints_transformer.py` | ✅ Resolved |
| M-004 | **M** | `ContentCleaner.clean_html()` numbered list detection heuristic (`is_numbered = all(line[:1].isdigit() or ...)`) is fragile. A single paragraph where every line happens to start with a digit (e.g., salary ranges like "3-5 million", "10 working days") will be mis-classified as an ordered list. Conversely, a genuine 1-item list is also mis-classified because `all()` returns `True` for a single non-digit item. | `src/transformers/content_cleaner.py` | ✅ Resolved |
| M-005 | **M** | `JobStreetTransformer.infer_job_level()` and `GlintsTransformer.infer_job_level()` use different inference logic. JobStreet uses title keyword matching only; Glints additionally uses `maxYearsOfExperience`. The same "Software Engineer" job posted on both platforms will likely have different `level` values, producing inconsistent data in the database. | `src/transformers/jobstreet_transformer.py`, `src/transformers/glints_transformer.py` | ⏭️ Skipped (JobStreet deferred) |
| M-006 | **M** | `SupabaseClient.get_existing_ids()` loads **all** `(job_source, source_id)` pairs into memory on startup. At scale (100,000+ jobs), this initial load will be slow and consume significant memory. There is no timeout or progress indicator for this bulk query. | `src/clients/supabase_client.py` | ⏭️ Deferred |
| M-007 | **M** | `ScraperService.scrape_jobstreet_all_pages()` calls `time.sleep(2)` after every single job detail fetch. With `MAX_PAGES_JOBSTREET=0` (unlimited) this means roughly 2 seconds × 30 jobs/page × N pages — for 57,000+ available jobs this adds over 38 hours of artificial delay per run, making a full crawl practically impossible. | `src/services/scraper_service.py` | ⏭️ Skipped (JobStreet deferred) |
| L-001 | **L** | `requirements.txt` has 18 lines for only 5 unique packages. Should be replaced with a clean, pinned file that matches `pyproject.toml`. | `requirements.txt` | ✅ Resolved (see C-001) |
| L-002 | **L** | `SheetsClient.__init__()` has a default `worksheet_name="Loker.id"` which is an outdated leftover. The actual default everywhere else (`.env.example`, `settings.py`) is `"Jobs"`. | `src/clients/sheets_client.py` | ✅ Resolved |
| L-003 | **L** | `GlintsTransformer` imports `logging` inside a `try/except` block at module level — a pattern not used by any other module. If this import ever fails (it can't in any Python ≥ 2.7), `logger` would silently be `None` and all log calls would be skipped rather than raising an error. | `src/transformers/glints_transformer.py` | ✅ Resolved |
| L-004 | **L** | No `.dockerignore` file exists. Every `docker build` copies the entire repo into the image including `.git/` history, `docs/`, `images/`, `uv.lock`, etc. This inflates image size unnecessarily. | Root directory | ✅ Resolved |
| L-005 | **L** | `docker-compose.yaml` has no `volumes` declaration for log output. In production, container logs are ephemeral — all scraping history is lost when the container is recreated. | `docker-compose.yaml` | ✅ Resolved |
| L-006 | **L** | `LokerClient.fetch_page()` logs `"No more pages at page {n}"` when it receives HTTP 404. This message is misleading — it could also indicate a real 404 error rather than pagination exhaustion. A more accurate message would be `"Page {n} not found — end of results"`. | `src/clients/loker/loker_client.py` | ✅ Resolved |
| L-007 | **L** | `src/clients/linkedin/__init__.py` exists but contains no implementation. `ENABLE_LINKEDIN` is a real config flag that does nothing when set to `true` — it could mislead operators into thinking LinkedIn scraping is active. | `src/clients/linkedin/__init__.py` | ✅ Resolved |
| L-008 | **L** | `pyproject.toml` still has `name = "repl-nix-workspace"` and `description = "Add your description here"` — leftover Replit scaffold metadata, not reflecting the actual project. | `pyproject.toml` | ✅ Resolved (see C-003) |
| L-009 | **L** | `GlintsClient` GraphQL query strings (`DETAIL_QUERY`, `GRAPHQL_QUERY`) are stored as multi-line class attributes. If either query needs to be updated, it requires editing deeply-indented strings inside the class body. Externalizing them to `.graphql` files or a `queries/` module would make them easier to maintain and test. | `src/clients/glints/glints_client.py` | ⏭️ Deferred |

---

## Detailed Findings by Level

---

### 🔴 Critical (C)

#### C-001 — Broken `requirements.txt`

The file contains 18 lines but only 5 unique packages. The same packages appear multiple times, with a mix of pinned and unpinned versions:

```
gspread==6.2.1      ← pinned
gspread              ← unpinned (will install latest, possibly newer/different)
python-dotenv        ← appears 6 times
supabase             ← appears twice, never pinned
```

**Risk:** `pip install -r requirements.txt` in CI/CD or Docker will resolve dependency conflicts unpredictably. The pinned `gspread==6.2.1` and the unpinned `gspread` entry conflict — depending on resolver order, a different version may be installed.

**Fix:** Replace the file with one clean entry per package, all pinned to specific versions.

---

#### C-002 — Docker Image Broken by C-001

`Dockerfile` line 6: `RUN pip install --no-cache-dir -r requirements.txt`

Any Docker build inherits the duplicate and version-conflict problem in `requirements.txt`. The container may boot with wrong package versions and fail at runtime with import errors.

**Fix:** Resolve C-001 first, then update Dockerfile to use the clean `requirements.txt` or switch to `uv sync` using `pyproject.toml`.

---

#### C-003 — `pyproject.toml` Missing Core Dependencies

Current `pyproject.toml` dependencies:
```toml
dependencies = [
    "beautifulsoup4>=4.14.2",   ← present
    "gspread>=6.2.1",           ← present
    "oauth2client>=4.1.3",      ← present
    "requests>=2.32.5",         ← present
]
```

**Missing:**
- `supabase` — required for `STORAGE_BACKEND=supabase` (the active production config)
- `python-dotenv` — required by `settings.py` to load `.env`
- `lxml` or `html5lib` — recommended BeautifulSoup parser

Any developer using `uv`, `pip install -e .`, or PEP 517 tooling will get a broken environment that crashes immediately on `from dotenv import load_dotenv` or `from supabase import create_client`.

---

### 🟠 High (H)

#### H-001 — Google Sheets Deduplication Uses Hardcoded Column Indices

```python
# sheets_client.py line ~85
source_ids = self.sheet.col_values(2)[1:]  # Column B hardcoded
job_sources = self.sheet.col_values(3)[1:] # Column C hardcoded
```

The transformer outputs data by matching against `headers` (dynamic column names read from row 1), but the duplicate check bypasses this and directly reads columns B and C. If the sheet is modified to add a column before column B (e.g., a `serial_number` column), deduplication reads the wrong data and every job will be re-inserted on every run.

**Fix:** Read the header row, find the index of `source_id` and `job_source` columns by name, and use those indices.

---

#### H-002 — Loker.id Pagination Never Terminates Safely

```python
# loker_client.py
return jobs, True  # has_more is ALWAYS True
```

The scrape loop in `scraper_service.py` only exits via:
1. HTTP 404 response from the API
2. Empty `jobs_data` list

There is no check for whether `jobs` actually contains new data vs. already-seen data, and there's no maximum-page guard when `MAX_PAGES_LOKER=0`. If Loker's API behaviour ever changes to return `{"jobs": []}` with HTTP 200 on the final page instead of 404, the while-loop runs forever.

---

#### H-003 — Fresh Graduate Detection is Dead Code

```python
# jobstreet_client.py _extract_experience()
if re.search(r"fresh\s+graduate", text, re.IGNORECASE):
    return "1-3 Tahun"   # ← same as default below

return "1-3 Tahun"  # Default
```

Both return `"1-3 Tahun"`. Removing the fresh graduate branch changes nothing. This indicates the intended behaviour (perhaps returning `"0-2 Tahun"` or `"Entry Level"` for fresh graduates) was never implemented.

---

#### H-004 — Education Extraction Scans Entire Page (False Positives)

```python
# jobstreet_client.py _extract_education()
text = soup.get_text().upper()
# ... checks for "S1", "D3", etc. anywhere in text
```

Job pages contain company headers, skill tags, sidebar navigation, and related job listings — all of which get included in `.get_text()`. A job for "S1 Operations Director" will match `S1` from the title. A description mentioning "D3 data pipeline" will match `D3`.

**Fix:** Scope the education keyword search to the `data-automation="jobAdDetails"` section only (already extracted as `content` in `_extract_job_description()`), not the entire page.

---

#### H-005 — Double Initialization Risk in Parallel Mode

`run_continuous()` → `initialize_storage_client()` ← storage + existing_ids loaded  
Then worker threads call `scrape_*_all_pages()` indirectly through `run_once_parallel()` which calls `initialize_storage_client()` again — **resetting** `self.existing_ids` to a fresh database snapshot, discarding all in-memory dedup state from the current run.

---

#### H-006 — Glints Gender Field Ignored

```python
# glints_transformer.py transform_job()
"gender": "Laki-laki/Perempuan",   # Always hardcoded
```

The Glints `DETAIL_QUERY` fetches `gender` from the API. The `detail` dict is available in `transform_job()` at `job.get("detail", {})`. The field is fetched but thrown away — all Glints jobs are stored with the generic "no restriction" gender value regardless of what the posting actually specifies.

---

### 🟡 Medium (M)

#### M-001 — No HTTP Retry Logic

All three clients make HTTP requests with no retry on failure. Network issues (timeout, 429, 503) cause permanent data loss for that job/page in the current run cycle. The clients should use `tenacity` or a manual retry loop with exponential backoff (e.g., 3 attempts, 1s/2s/4s delays).

---

#### M-002 — Loker Province KeyError on Missing `name`

```python
# loker_transformer.py
"province": job["locations"][0]["parent"]["name"] if job.get("locations") 
            and job["locations"][0].get("parent") else "",
```

If `job["locations"][0]["parent"]` is an empty dict `{}` (not `None`), `get("parent")` returns `{}` which is truthy, so the ternary evaluates `job["locations"][0]["parent"]["name"]` — raising `KeyError: 'name'`.

---

#### M-003 — Bare `except:` in Glints Description Parser

```python
# glints_transformer.py
try:
    import json
    desc_data = json.loads(description_json)
    ...
except:            # ← catches EVERYTHING
    return description_json
```

This catches `KeyboardInterrupt`, `SystemExit`, and any other exception. A Ctrl+C during Glints scraping will be swallowed here, making the process unresponsive to shutdown signals.

---

#### M-004 — Fragile HTML List Detection in ContentCleaner

```python
is_numbered = all(
    line[:1].isdigit() or line.lstrip().startswith(("-", "•")) for line in lines
)
```

Edge cases that break this:
- **Single-item list:** `all(...)` over a single element that starts with a letter returns `False` correctly, but a single element starting with a number returns `True` and wraps it in `<ol>` incorrectly.
- **Salary paragraphs:** A responsibility section like `"3-5 million IDR, 10 days annual leave, 2 health allowances"` would have lines starting with digits and be classified as an ordered list.

---

#### M-005 — Inconsistent Job Level Inference Across Sources

| Source | Logic |
|--------|-------|
| JobStreet | Title keywords only: `senior/manager/lead` → Senior; `director/head/chief` → Management; `junior/entry/trainee` → Entry; default → Mid |
| Glints | Title keywords first; then `maxYearsOfExperience <= 2` → Entry; `<= 5` → Mid; `> 5` → Senior |

The same job titled "Software Engineer" with 3 years experience will be `Mid Level` on Glints but `Mid Level` on JobStreet (accidental agreement). However "Senior Software Engineer" with `maxYearsOfExperience=1` on Glints maps to `Senior Level` by title but `Entry Level` by years — the title branch wins because it's checked first, but the inconsistency between sources is never reconciled.

---

#### M-006 — Full ID Set Loaded Into Memory at Startup

`SupabaseClient.get_existing_ids()` fetches all `(job_source, source_id)` tuples in pages of 1,000. At 100,000 jobs this is 100 API calls before scraping even begins. Each call is synchronous, and there is no timeout guard. If the Supabase connection drops during this process, the function returns an empty set — causing ALL existing jobs to be re-processed and hitting the `UNIQUE(job_source, source_id)` constraint on insert, which logs errors for every single job.

---

#### M-007 — JobStreet 2-Second Per-Job Delay Makes Full Crawl Impractical

```python
# scraper_service.py scrape_jobstreet_all_pages()
time.sleep(2)  # After every job detail fetch
```

With `MAX_PAGES_JOBSTREET=0`:
- ~57,000 available jobs ÷ 30 per page = ~1,900 pages
- 30 jobs × 2 seconds = 60 seconds per page minimum
- Total: ~31 hours per full crawl, plus API call time

The 1-hour `SCRAPE_INTERVAL_SECONDS` means the next run starts before the current one finishes. Over time, worker threads pile up and exhaust memory/connections.

---

### 🔵 Low (L)

#### L-001 — `requirements.txt` Duplication

18 lines for 5 packages. See C-001 for the critical impact; separately, the file itself is unmaintainable.

#### L-002 — Outdated Default Worksheet Name

`SheetsClient` defaults to `worksheet_name="Loker.id"` but every other reference to this default (settings.py, .env.example) uses `"Jobs"`.

#### L-003 — Abnormal `logging` Import Pattern in GlintsTransformer

```python
# glints_transformer.py top of file
logger = None
try:
    import logging
    logger = logging.getLogger(__name__)
except:
    pass
```

This is the only module in the codebase that does this. `import logging` never raises an exception in any Python environment. All other modules import normally.

#### L-004 — No `.dockerignore`

Docker build context includes `.git/` (entire version history), `images/`, `docs/`, `uv.lock`, `*.md` files. Can add 10–50 MB to the image unnecessarily.

#### L-005 — No Log Volume in Docker Compose

Container logs are ephemeral. When `docker compose down` is run, all scraping history is lost. There is no `volumes:` mapping to persist logs to the host.

#### L-006 — Misleading Loker Pagination Log Message

```python
logger.info(f"No more pages at page {page_num}")
```
This fires when the API returns HTTP 404. The message implies no data was found, but this is the normal/expected end-of-pages signal — it should say something like `"Reached end of Loker.id results at page {n}"`.

#### L-007 — LinkedIn Stub Can Mislead Operators

`ENABLE_LINKEDIN` is a real config key with default `false`. If an operator switches it to `true`, nothing happens (no source is added, no warning is logged). The service should raise a `NotImplementedError` or log a clear warning when `enable_linkedin=True`.

#### L-008 — Stale `pyproject.toml` Metadata

`name = "repl-nix-workspace"` and `description = "Add your description here"` are Replit scaffold defaults. Should be updated to reflect the actual project.

#### L-009 — GraphQL Queries Inline as Class Attributes

`GlintsClient.DETAIL_QUERY` and `GlintsClient.GRAPHQL_QUERY` are large multi-line strings embedded directly in the class. They are hard to diff, hard to test independently, and cannot be loaded by any GraphQL IDE tooling.

---

### 🟢 Enhancements (E)

| Code | Enhancement | Benefit |
|------|-------------|---------|
| E-001 | **Implement LinkedIn scraper** — the folder, `__init__.py`, and settings flag already exist. Implementing `LinkedInClient` and `LinkedInTransformer` would immediately enable a new high-value source. | More job coverage |
| E-002 | **Add exponential backoff retry** — wrap all HTTP calls with 3-attempt retry (1s, 2s, 4s) using `tenacity` or a simple loop. | Eliminates transient data loss |
| E-003 | **Automated job status expiry** — add a separate daily task that re-checks all `active` jobs older than N days against the source API and marks them `expired`/`filled` in Supabase. | Keeps data fresh |
| E-004 | **Search filters per source** — add env vars like `LOKER_KEYWORDS`, `GLINTS_LOCATION_FILTER`, `JOBSTREET_CATEGORY_FILTER` to focus scraping on specific job types or regions. | Reduces noise, improves relevance |
| E-005 | **Metrics & statistics per run** — log a structured summary at end of each run: jobs found / jobs new / jobs skipped (duplicate) / jobs failed per source. Optionally write to Supabase `scraper_runs` table. | Observability |
| E-006 | **Error/completion notifications** — send a webhook (Slack, Discord, Telegram) or email on fatal errors or daily run completion with the stats from E-005. | Proactive monitoring |
| E-007 | **Data validation layer** — before `append_row()`, validate that `title`, `company_name`, `link`, and `source_id` are non-empty. Reject and log malformed records instead of inserting empty rows. | Data quality |
| E-008 | **Location normalization dictionary** — build a mapping of common Indonesian city/province name variants to canonical forms (e.g., `"Jaksel"` → `"Jakarta Selatan"`, `"DKI"` → `"DKI Jakarta"`). Apply to all three sources during transform. | Consistent geo data |
| E-009 | **Lazy ID loading / bloom filter** — replace the full in-memory ID set with a Bloom filter or lazy DB check on insert. Reduces startup time and memory at scale. | Performance at scale |
| E-010 | **Rate limiting for Supabase** — the current `RateLimiter` is only wired to `SheetsClient`. Supabase has its own rate limits (especially on the free tier). Add configurable insert throttling for the Supabase backend. | Avoids Supabase 429 errors |
| E-011 | **Add unit tests** — `FieldMappers`, `ContentCleaner`, `LokerTransformer`, and the salary/education parsers are pure functions that are straightforward to test with `pytest`. | Regression safety |
| E-012 | **Add more job sources** — Kalibrr, Karir.com, Indeed Indonesia. The `BaseStorageClient` abstraction makes adding new sources well-defined. | Coverage |
| E-013 | **Configurable per-source scrape intervals** — currently all sources share `SCRAPE_INTERVAL_SECONDS`. Loker.id may need hourly updates while Glints may only need daily. | Efficiency |
| E-014 | **File log handler** — add a `RotatingFileHandler` alongside the console handler so logs survive container restarts even without a volume mount. | Operational visibility |
| E-015 | **`uv` lock file** — `uv.lock` already exists which is great. But `Dockerfile` still uses `pip`. Switching to `uv sync --frozen` in the Dockerfile would respect the lockfile and guarantee reproducible builds. | Build reproducibility |

---

## Summary

| Level | Count |
|-------|-------|
| Critical (C) | 3 |
| High (H) | 6 |
| Medium (M) | 7 |
| Low (L) | 9 |
| Enhancement (E) | 15 |
| **Total** | **40** |

### Recommended Fix Order (Quick Wins First)

1. **C-001 + C-003** — Fix `requirements.txt` and `pyproject.toml` (30 min, no logic changes)
2. **C-002** — Update Dockerfile to use clean deps (5 min)
3. **H-006** — Fix Glints gender field (5 min, one-line change)
4. **M-002** — Fix Loker province KeyError (5 min)
5. **M-003** — Replace bare `except:` with `except Exception as e:` (10 min)
6. **L-002** — Fix SheetsClient default worksheet name (2 min)
7. **L-004** — Add `.dockerignore` (5 min)
8. **H-003** — Fix fresh graduate dead code / assign correct return value (5 min)
9. **M-007** — Make JobStreet per-job delay configurable via env var (10 min)
10. **H-004** — Scope education extraction to job details section only (20 min)
