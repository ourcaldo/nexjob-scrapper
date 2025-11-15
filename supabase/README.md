# Supabase Database Setup

This directory contains the database schema and setup instructions for using Supabase as the storage backend for the Job Scraper service.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Database Schema](#database-schema)
- [Status Column](#status-column)
- [Querying Data](#querying-data)
- [Troubleshooting](#troubleshooting)

## Overview

The Job Scraper can use **Supabase** (PostgreSQL database) as an alternative to Google Sheets for storing scraped job records. Supabase offers:

- **Better performance** for large datasets (10,000+ jobs)
- **Advanced querying** with SQL
- **Built-in indexing** for faster searches
- **RESTful API** and real-time subscriptions
- **Row-level security** (RLS) for data protection
- **Automatic backups** and point-in-time recovery

## Prerequisites

1. **Supabase Account**: Sign up at [supabase.com](https://supabase.com) (free tier available)
2. **Supabase Project**: Create a new project in your Supabase dashboard
3. **Database Access**: Note your project URL and API keys

## Setup Instructions

### Step 1: Create a Supabase Project

1. Go to [app.supabase.com](https://app.supabase.com)
2. Click **"New Project"**
3. Fill in project details:
   - **Name**: Job Scraper (or your preferred name)
   - **Database Password**: Create a strong password
   - **Region**: Choose closest to your location
4. Click **"Create new project"** (takes ~2 minutes to provision)

### Step 2: Get Your Credentials

1. Once your project is ready, go to **Settings** → **API**
2. Copy the following credentials:
   - **Project URL** (e.g., `https://xyzcompany.supabase.co`)
   - **anon/public key** (starts with `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`)
   - (Optional) **service_role key** for admin operations

### Step 3: Run the Database Schema

1. In your Supabase dashboard, go to **SQL Editor**
2. Click **"New Query"**
3. Copy the entire contents of `schema.sql` from this directory
4. Paste it into the SQL editor
5. Click **"Run"** or press `Ctrl+Enter`
6. You should see: `Success. No rows returned`

**Alternative method using Supabase CLI:**
```bash
# Install Supabase CLI
npm install -g supabase

# Login to Supabase
supabase login

# Link to your project
supabase link --project-ref your-project-ref

# Run the migration
supabase db push
```

### Step 4: Configure Environment Variables

1. Open your `.env` file (or create from `.env.example`)
2. Set the storage backend to Supabase:
   ```bash
   STORAGE_BACKEND=supabase
   ```
3. Add your Supabase credentials:
   ```bash
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key-here
   ```

### Step 5: Verify the Setup

Run the scraper to test:
```bash
python main.py
```

Expected output:
```
2025-11-15 10:00:00 - INFO - Initializing Job Scraper Service...
2025-11-15 10:00:00 - INFO - Using Supabase storage backend
2025-11-15 10:00:01 - INFO - Successfully connected to Supabase
2025-11-15 10:00:01 - INFO - Found 0 existing jobs in database
...
```

## Database Schema

### Table: `job_scraper`

The `job_scraper` table stores all scraped job postings with the following structure:

| Column Name | Data Type | Nullable | Default | Description |
|------------|-----------|----------|---------|-------------|
| `id` | BIGSERIAL | NO | AUTO | Primary key (auto-increment) |
| `internal_id` | UUID | NO | gen_random_uuid() | Unique internal UUID for tracking |
| `source_id` | VARCHAR(255) | NO | - | Job ID from external source |
| `job_source` | VARCHAR(100) | NO | - | Source platform name |
| `link` | TEXT | NO | - | Direct URL to job posting |
| `company_name` | VARCHAR(500) | YES | - | Company name |
| `job_category` | VARCHAR(255) | YES | - | Job category/department |
| `title` | VARCHAR(500) | NO | - | Job title |
| `content` | TEXT | YES | - | Cleaned HTML job description |
| `province` | VARCHAR(255) | YES | - | Province/State |
| `city` | VARCHAR(255) | YES | - | City/District |
| `experience` | VARCHAR(100) | YES | - | Experience level (normalized) |
| `job_type` | VARCHAR(100) | YES | - | Job type (Full Time, Part Time, etc.) |
| `level` | VARCHAR(100) | YES | - | Job level (Entry, Mid, Senior) |
| `salary_min` | BIGINT | YES | 0 | Minimum salary in IDR |
| `salary_max` | BIGINT | YES | 0 | Maximum salary in IDR |
| `education` | VARCHAR(100) | YES | - | Education requirement |
| `work_policy` | VARCHAR(100) | YES | - | Work policy (Remote, On-site, Hybrid) |
| `industry` | VARCHAR(255) | YES | - | Industry sector |
| `gender` | VARCHAR(100) | YES | - | Gender requirement |
| `tags` | TEXT | YES | - | Comma-separated tags |
| `status` | VARCHAR(50) | YES | 'active' | **NEW**: Job posting status |
| `created_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Record creation timestamp |
| `updated_at` | TIMESTAMP | NO | CURRENT_TIMESTAMP | Last update timestamp |

### Unique Constraints

- `internal_id` must be unique across all records
- Combination of `(job_source, source_id)` must be unique to prevent duplicates

### Indexes

The schema creates the following indexes for optimal performance:

- `idx_job_scraper_source_id` - Fast lookups by source ID
- `idx_job_scraper_job_source` - Filter by job source
- `idx_job_scraper_status` - Filter by status
- `idx_job_scraper_created_at` - Sort by date (descending)
- `idx_job_scraper_company_name` - Search by company
- `idx_job_scraper_city` - Filter by location
- `idx_job_scraper_province` - Filter by province

## Status Column

The **`status`** column is a new field that tracks the current state of each job posting. This is **unique to Supabase** and not available in the Google Sheets implementation.

### Status Values

| Status | Description | Use Case |
|--------|-------------|----------|
| `active` | Job is currently open (default) | Newly scraped jobs |
| `inactive` | Job is no longer active | Marked as closed by scraper or admin |
| `expired` | Job posting has expired | Based on expiry date logic |
| `filled` | Position has been filled | Updated manually or via integration |
| `pending` | Job awaiting review/approval | Quality control workflow |
| `archived` | Old job kept for historical data | Data retention policy |

### Using Status in Queries

**Get only active jobs:**
```sql
SELECT * FROM job_scraper WHERE status = 'active';
```

**Count jobs by status:**
```sql
SELECT status, COUNT(*) as count 
FROM job_scraper 
GROUP BY status;
```

**Update a job status:**
```sql
UPDATE job_scraper 
SET status = 'filled' 
WHERE source_id = '12345' AND job_source = 'Loker.id';
```

**Archive old inactive jobs:**
```sql
UPDATE job_scraper 
SET status = 'archived' 
WHERE status = 'inactive' 
AND created_at < NOW() - INTERVAL '90 days';
```

## Querying Data

### Common Queries

**Get recent jobs:**
```sql
SELECT title, company_name, city, salary_min, salary_max, created_at
FROM job_scraper
WHERE status = 'active'
ORDER BY created_at DESC
LIMIT 100;
```

**Search by location:**
```sql
SELECT *
FROM job_scraper
WHERE city ILIKE '%Jakarta%'
AND status = 'active'
ORDER BY created_at DESC;
```

**Filter by salary range:**
```sql
SELECT title, company_name, salary_min, salary_max
FROM job_scraper
WHERE salary_min >= 5000000
AND salary_max <= 15000000
AND status = 'active';
```

**Jobs by source:**
```sql
SELECT job_source, COUNT(*) as total_jobs
FROM job_scraper
GROUP BY job_source
ORDER BY total_jobs DESC;
```

**Duplicate check (used by scraper):**
```sql
SELECT source_id
FROM job_scraper
WHERE job_source = 'Loker.id'
AND source_id IN ('12345', '12346', '12347');
```

### Using Supabase Dashboard

1. Go to **Table Editor** in your Supabase dashboard
2. Select the `job_scraper` table
3. Use the built-in filters and search
4. Export data as CSV if needed

## Troubleshooting

### Issue: "relation 'job_scraper' does not exist"

**Solution:** The schema hasn't been created yet. Run the SQL from `schema.sql` in the SQL Editor.

### Issue: "duplicate key value violates unique constraint"

**Solution:** A job with the same `(job_source, source_id)` already exists. The scraper automatically handles this by checking for duplicates before inserting.

### Issue: "permission denied for table job_scraper"

**Solution:** 
1. Make sure you're using the correct API key
2. Check Row Level Security (RLS) policies:
   ```sql
   -- Disable RLS for testing (not recommended for production)
   ALTER TABLE job_scraper DISABLE ROW LEVEL SECURITY;
   ```

### Issue: Slow queries

**Solution:** 
1. Verify indexes are created (run schema.sql again)
2. Add more specific indexes if needed:
   ```sql
   CREATE INDEX idx_custom ON job_scraper(column_name);
   ```

### Issue: Connection timeout

**Solution:**
1. Check your internet connection
2. Verify SUPABASE_URL and SUPABASE_KEY are correct
3. Check Supabase project status in dashboard

## Migration from Google Sheets

If you're migrating from Google Sheets to Supabase:

1. **Export your Google Sheet** as CSV
2. **Use Supabase Table Editor** to import CSV:
   - Go to Table Editor → job_scraper
   - Click "Import data via spreadsheet"
   - Upload your CSV file
   - Map columns correctly
3. **Verify data** after import
4. **Update .env** to use Supabase

## Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Supabase Python Client](https://github.com/supabase/supabase-py)

## Support

For issues specific to this implementation, refer to the main project README or create an issue in the repository.
