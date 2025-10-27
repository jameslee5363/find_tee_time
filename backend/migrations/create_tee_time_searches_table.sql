-- Create tee_time_searches table for storing user search requests
-- All times are stored in UTC format

CREATE TABLE IF NOT EXISTS tee_time_searches (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_name VARCHAR(255) NOT NULL,
    preferred_dates TEXT NOT NULL,  -- JSON string of date strings (YYYY-MM-DD)
    preferred_time_start VARCHAR(10),  -- UTC time in HH:MM format
    preferred_time_end VARCHAR(10),  -- UTC time in HH:MM format
    group_size INTEGER NOT NULL CHECK (group_size >= 1 AND group_size <= 4),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_tee_time_searches_user_id ON tee_time_searches(user_id);
CREATE INDEX IF NOT EXISTS idx_tee_time_searches_course_name ON tee_time_searches(course_name);
CREATE INDEX IF NOT EXISTS idx_tee_time_searches_status ON tee_time_searches(status);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_tee_time_searches_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_tee_time_searches_updated_at
    BEFORE UPDATE ON tee_time_searches
    FOR EACH ROW
    EXECUTE FUNCTION update_tee_time_searches_updated_at();
