# Code Review — nexjob-scrapper

**Date:** 2026-02-23  
**Reviewer:** GitHub Copilot  
**Scope:** Full project deep dive — structure, standardization, bugs, efficiency

---

## Project Structure

```
nexjob-scrapper/
├── main.py                          # Entry point
├── src/
│   ├── config/settings.py           # All env var config
│   ├── clients/
│   │   ├── base_storage_client.py   # ABC for storage backends
│   │   ├── supabase_client.py       # Supabase storage
│   │   ├── sheets_client.py         # Google Sheets storage
│   │   ├── loker/loker_client.py    # Loker.id REST client
│   │   ├── jobstreet/               # JobStreet REST + HTML scrape
│   │   ├── glints/glints_client.py  # Glints GraphQL (curl_cffi)
│   │   ├── karir/karir_client.py    # Karir.com REST client
│   │   └── linkedin/                # Stub, not implemented
│   ├── transformers/
│   │   ├── field_mappers.py         # Centralized normalizers
│   │   ├── loker_transformer.py
│   │   ├── jobstreet_transformer.py
│   │   ├── glints_transformer.py
│   │   ├── karir_transformer.py
│   │   └── content_cleaner.py       # HTML cleaner for JobStreet
│   ├── services/scraper_service.py  # Full orchestration (~890 lines)
│   └── utils/
│       ├── retry.py                 # Exponential backoff
│       └── rate_limiter.py          # Sheets API quota manager
```

---

## What's Good

| Area | Assessment |
|---|---|
| **Architecture** | Clean separation of concerns — clients, transformers, storage, orchestration are all distinct layers |
| **ABC for storage** | `BaseStorageClient` properly abstracts Supabase vs Sheets with a contract |
| **FieldMappers** | Centralized normalization is correct — one source of truth for experience, job_type, education |
| **Retry utility** | Solid exponential backoff, reusable |
| **Settings** | All config from env, with `validate()` catching missing required vars early |
| **Duplicate detection** | In-memory set of `(job_source, source_id)` is fast and correct |
| **Parallel workers** | Independent threads per source make scheduling flexible |
| **Threading lock** | `self.lock` around `existing_ids` mutations is correct |

---

## Issues & Inefficiencies

### 🔴 High — Actual Bugs / Risks

**1. `settings.validate()` doesn't know about `enable_karir`**
The "at least one source enabled" check only checks Loker/JobStreet/Glints/LinkedIn. If only Karir is enabled it raises `ValueError`.

**2. `supabase_client.append_row` handles `internal_id` inconsistently**
`HEADERS` includes `internal_id` but only `LokerTransformer` populates it with `uuid.uuid4()`. `GlintsTransformer` and `KarirTransformer` omit it, silently relying on the DB default `gen_random_uuid()`. Loker rows carry a Python-generated UUID, others use the DB default — inconsistent behaviour across sources.

**3. `scraper_service.py` is ~890 lines — a God Object**
All orchestration logic for 4 sources lives in one class. `process_X_job`, `scrape_X_all_pages`, `X_worker` are repeated 4 times each with near-identical structure. A bug fix or behaviour change must be applied in 4 places.

**4. Karir detail calls are not retried**
`KarirClient.fetch_job_detail` uses a bare `requests.Session` with no retry wrapper, unlike `LokerClient` which uses `retry_request`. A transient HTTP 500 silently drops the job.

**5. `SupabaseClient.get_existing_ids` is a full table scan on every startup**
At 13,627 rows it loads `(job_source, source_id)` for every record into RAM. At 100k+ rows this becomes a slow startup and large memory allocation. There is no TTL or refresh — if the process restarts it re-scans everything.

---

### 🟡 Medium — Maintainability / Correctness

**6. Row format is a positional `List` — fragile**
Transformers return `[row.get(h, "") for h in headers]`. If `HEADERS` order in `SupabaseClient` ever changes, every transformer silently writes wrong data to wrong columns. A `dict` insert is safer (and the Supabase Python client supports it directly — `append_row` already builds a `dict` internally from the `List`).

**7. `KarirTransformer` strips `internal_id` entirely**
All other transformers include `internal_id` in the row dict. `KarirTransformer.transform_job` doesn't — this works by accident because `SupabaseClient.append_row` skips missing headers and the DB default fills it. No actual bug now, but diverges from the pattern.

**8. `glints_client.py` uses `curl_cffi` but others use `requests` — no shared session abstraction**
This is a functional necessity (Cloudflare bypass) but there is no comment or doc explaining why Glints cannot use standard `requests`. Future maintainers will be confused.

**9. No job expiry / deactivation mechanism**
There is no way to mark old jobs as expired or filled. Jobs posted in 2024 remain `status='active'` in Supabase indefinitely. Loker.id and Karir.com both return expiry timestamps (`expires_at`) that could drive an automated deactivation pass.

**10. `PAGE_DELAY_SECONDS` is shared across all sources**
Loker, JobStreet, Glints, and Karir all sleep the same `page_delay_seconds` between pages. Glints needs longer waits (Cloudflare-protected), while Karir.com needs almost none (open API). Per-source delay settings would be more appropriate.

---

### 🟢 Low — Style / Minor

**11. `scraper_service.py` docstrings still reference "Google Sheets"**
Several method docstrings say "stores in Google Sheets" even though Supabase is now the primary backend.

**12. `LokerTransformer.transform_job` stringifies salaries unnecessarily**
Returns `str(salary_min)` → `"1000000"`. `SupabaseClient.append_row` then casts it back to `int`. Unnecessary round-trip.

**13. Karir.com `_PAGE_SIZE = 20` constant is duplicated**
Defined as `_PAGE_SIZE = 20` in `karir_client.py` but `scraper_service.py` hardcodes `offset += 20`. If the constant changes, the offset increment won't update automatically.

**14. Missing job context when Karir detail fetch fails**
`logger.warning(f"Could not fetch detail for Karir.com job {job_id}, skipping")` — doesn't log the job title or company name. Other sources log more context on failure.

---

## Architecture Concepts

### transformer vs field_mappers.py

They solve two different problems:

**`field_mappers.py`** — knows nothing about any platform. It only normalizes a *value* to the universal standard:
- `"PENUH WAKTU"` → `"Full Time"`
- `"3-5 Tahun"` → `"Mid Level"`
- `"SARJANA"` → `"S1"`

**Individual transformers** — know everything about *one platform's raw data shape*: what the fields are named, how they are nested, how salary is encoded, how to build the HTML content. They extract the raw value from the platform's response, then call `FieldMappers` to normalize it.

**transformer = extraction + assembly. FieldMappers = normalization.**

### Scrape → Database Flow

```
1. FETCH (Client)
   KarirClient.fetch_page(offset=0)
   └─→ POST /v2/search/opportunities
   └─→ Returns: list of 20 job dicts

2. DETAIL FETCH (Client)
   KarirClient.fetch_job_detail(job_id)
   └─→ POST /v1/opportunity/detail
   └─→ Returns: full detail dict

3. DUPLICATE CHECK (ScraperService)
   job_key = ("Karir.com", "1400774")
   if job_key in self.existing_ids → skip
   └─→ existing_ids loaded from DB at startup

4. TRANSFORM (KarirTransformer)
   transform_job(list_job, detail, headers)
   ├─→ Extract raw fields from both dicts
   ├─→ FieldMappers.normalize_job_type("Tidak Disebutkan") → "Full Time"
   ├─→ FieldMappers.normalize_education("S1") → "S1"
   ├─→ FieldMappers.normalize_experience("1-3 Tahun") → "Junior"
   └─→ Returns: ordered List matching HEADERS column order

5. STORE (SupabaseClient)
   append_row(row_data)
   ├─→ Maps List back to dict using HEADERS
   └─→ INSERT into job_scraper table

6. TRACK
   existing_ids.add(("Karir.com", "1400774"))
   └─→ In-memory set updated so same job isn't re-inserted this run
```

---

## Summary Verdict

The project is **well-structured and functional** for its current scope. The layered architecture (clients → transformers → service → storage), ABC contract, centralized FieldMappers, and retry utility are all correct patterns.

The two biggest real risks are:

1. **God Object in `scraper_service.py`** — scaling to 5+ portals will make it unmaintainable
2. **Full table scan on startup** — will become a real bottleneck beyond ~50k rows

Everything else is refinement. The codebase is production-ready at current scale but should be refactored before adding significantly more portals.
