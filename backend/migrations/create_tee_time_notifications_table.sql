-- Create tee_time_notifications table for tracking sent notifications
-- Prevents duplicate notifications from being sent to users

CREATE TABLE IF NOT EXISTS tee_time_notifications (
    id SERIAL PRIMARY KEY,
    search_id INTEGER NOT NULL REFERENCES tee_time_searches(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tee_time_id VARCHAR(100) NOT NULL,  -- From tee_times table in Airflow database

    -- Notification details
    course_name VARCHAR(255) NOT NULL,
    tee_off_date VARCHAR(50) NOT NULL,
    tee_off_time VARCHAR(20) NOT NULL,
    available_spots INTEGER NOT NULL,

    -- Notification status
    email_sent BOOLEAN DEFAULT FALSE,
    notification_sent_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_tee_time_notifications_search_id ON tee_time_notifications(search_id);
CREATE INDEX IF NOT EXISTS idx_tee_time_notifications_user_id ON tee_time_notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_tee_time_notifications_tee_time_id ON tee_time_notifications(tee_time_id);

-- Create unique constraint to prevent duplicate notifications for same search and tee time
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_search_tee_time
    ON tee_time_notifications(search_id, tee_time_id);
