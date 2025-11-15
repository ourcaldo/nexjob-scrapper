-- Job Scraper Database Schema for Supabase
-- This schema creates a table to store scraped job postings from multiple sources
-- Compatible with PostgreSQL 12+

-- Create the job_scraper table
CREATE TABLE IF NOT EXISTS job_scraper (
    -- Primary key and unique identifiers
    id BIGSERIAL PRIMARY KEY,
    internal_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    source_id VARCHAR(255) NOT NULL,
    
    -- Job source and link
    job_source VARCHAR(100) NOT NULL,
    link TEXT NOT NULL,
    
    -- Company and job details
    company_name VARCHAR(500),
    job_category VARCHAR(255),
    title VARCHAR(500) NOT NULL,
    content TEXT,
    
    -- Location information
    province VARCHAR(255),
    city VARCHAR(255),
    
    -- Job requirements
    experience VARCHAR(100),
    job_type VARCHAR(100),
    level VARCHAR(100),
    salary_min BIGINT DEFAULT 0,
    salary_max BIGINT DEFAULT 0,
    education VARCHAR(100),
    work_policy VARCHAR(100),
    industry VARCHAR(255),
    gender VARCHAR(100),
    
    -- Additional metadata
    tags TEXT,
    status VARCHAR(50) DEFAULT 'active',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_source_job UNIQUE(job_source, source_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_job_scraper_source_id ON job_scraper(source_id);
CREATE INDEX IF NOT EXISTS idx_job_scraper_job_source ON job_scraper(job_source);
CREATE INDEX IF NOT EXISTS idx_job_scraper_status ON job_scraper(status);
CREATE INDEX IF NOT EXISTS idx_job_scraper_created_at ON job_scraper(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_job_scraper_company_name ON job_scraper(company_name);
CREATE INDEX IF NOT EXISTS idx_job_scraper_city ON job_scraper(city);
CREATE INDEX IF NOT EXISTS idx_job_scraper_province ON job_scraper(province);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a trigger to call the function
DROP TRIGGER IF EXISTS update_job_scraper_updated_at ON job_scraper;
CREATE TRIGGER update_job_scraper_updated_at
    BEFORE UPDATE ON job_scraper
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments to the table and columns for documentation
COMMENT ON TABLE job_scraper IS 'Stores job postings scraped from various job boards (Loker.id, JobStreet, Glints, etc.)';
COMMENT ON COLUMN job_scraper.internal_id IS 'Unique internal UUID for global tracking across all sources';
COMMENT ON COLUMN job_scraper.source_id IS 'Original job ID from the external source (used for duplicate detection)';
COMMENT ON COLUMN job_scraper.job_source IS 'Name of the job source platform (e.g., Loker.id, JobStreet, Glints)';
COMMENT ON COLUMN job_scraper.status IS 'Job posting status: active, inactive, expired, filled, etc.';
COMMENT ON COLUMN job_scraper.salary_min IS 'Minimum salary in Indonesian Rupiah (IDR)';
COMMENT ON COLUMN job_scraper.salary_max IS 'Maximum salary in Indonesian Rupiah (IDR)';
COMMENT ON COLUMN job_scraper.content IS 'Cleaned HTML job description';
COMMENT ON COLUMN job_scraper.tags IS 'Comma-separated combined tags for categorization';
