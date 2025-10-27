# Tee Time Notification System

This document describes the Kafka-based notification system that alerts users via email and SMS when their desired tee times become available.

## Overview

The notification system consists of three main components:

1. **Airflow DAG** - Continuously scrapes Bergen County Golf courses for available tee times (runs every 5 minutes)
2. **Kafka Consumer** - Processes new tee time search requests from users
3. **Periodic Matcher** - Regularly checks all active searches against the latest available tee times

## Architecture

```
┌─────────────────┐         ┌──────────────┐         ┌─────────────────┐
│   Airflow DAG   │ ─────> │ Tee Times DB  │ <───── │ Matcher Service │
│  (Scraper)      │         │  (Postgres)   │         │                 │
└─────────────────┘         └──────────────┘         └─────────────────┘
                                                              │
┌─────────────────┐         ┌──────────────┐                │
│  User Searches  │ ─────> │    Kafka      │ ──────────────┤
│   (FastAPI)     │         │   Topic       │                │
└─────────────────┘         └──────────────┘                │
                                                              ↓
                            ┌──────────────┐         ┌─────────────────┐
                            │ Notifications │ <───── │ Notifier        │
                            │ (Email + SMS) │         │ Consumer        │
                            └──────────────┘         └─────────────────┘
```

## How It Works

### 1. User Creates a Search Request

When a user submits a tee time search through the frontend:
- The request is saved to the `tee_time_searches` table
- A message is published to the Kafka topic `tee-time-searches`
- The request includes: course name, preferred dates, time range, and group size

### 2. Airflow Scrapes Available Tee Times

The Airflow DAG ([backend/airflow/dags/tee_time_checker_dag.py](backend/airflow/dags/tee_time_checker_dag.py)):
- Runs every 5 minutes
- Fetches available tee times for the next 7 days
- Saves tee times to the `tee_times` table in Postgres
- Marks tee times as available/unavailable based on API responses

### 3. Notifier Service Matches & Sends Notifications

The notifier service ([backend/kafka/consumers/tee_time_notifier_consumer.py](backend/kafka/consumers/tee_time_notifier_consumer.py)) runs in two modes:

#### A. Kafka Consumer Mode
- Listens to the `tee-time-searches` Kafka topic
- When a new search request arrives, immediately checks for matching tee times
- Sends notifications if matches are found

#### B. Periodic Matcher Mode
- Runs every 5 minutes (configurable via `MATCHER_CHECK_INTERVAL`)
- Checks ALL active search requests against the latest tee times
- Ensures notifications are sent even if the Kafka message was missed

### 4. Matching Logic

A tee time matches a search request if:
- ✅ Course name matches exactly
- ✅ Available spots >= requested group size
- ✅ Tee time is still available (`is_available = true`)
- ✅ Date matches one of the preferred dates
- ✅ Time falls within the preferred time range (if specified)

### 5. Notification Delivery

When a match is found:
- **Email** - HTML formatted email with tee time details sent via SMTP
- **SMS** - Short text message sent via Twilio
- A record is created in `tee_time_notifications` to prevent duplicate notifications

## Database Schema

### tee_time_searches
Stores user search requests.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| user_id | Integer | Foreign key to users table |
| course_name | String | Name of the golf course |
| preferred_dates | Text | JSON array of dates (YYYY-MM-DD) |
| preferred_time_start | String | UTC time in HH:MM format |
| preferred_time_end | String | UTC time in HH:MM format |
| group_size | Integer | Number of players (1-4) |
| status | String | pending, processing, completed, failed |

### tee_times
Stores available tee times (in Airflow database).

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| tee_time_id | String | Unique identifier |
| search_date | String | Date in "Day Mon DD YYYY" format |
| tee_off_time | String | Time in HH:MM format |
| course_name | String | Name of the course |
| available_spots | Integer | Number of available spots |
| is_available | Boolean | Whether the tee time is still available |

### tee_time_notifications
Tracks sent notifications to prevent duplicates.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| search_id | Integer | Foreign key to tee_time_searches |
| user_id | Integer | Foreign key to users |
| tee_time_id | String | Identifier of the tee time |
| email_sent | Boolean | Whether email was sent successfully |
| sms_sent | Boolean | Whether SMS was sent successfully |
| notification_sent_at | DateTime | When notification was sent |

## Configuration

### Environment Variables

Create a `.env` file in the `backend/` directory with the following variables:

```bash
# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Use App Password for Gmail
FROM_EMAIL=your-email@gmail.com

# Twilio Configuration
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Notifier Configuration
NOTIFIER_MODE=both  # consumer, periodic, or both
MATCHER_CHECK_INTERVAL=300  # Seconds (default: 5 minutes)
```

### Setting Up Email Notifications

**For Gmail:**
1. Enable 2-factor authentication on your Google account
2. Generate an App Password: https://support.google.com/accounts/answer/185833
3. Use the App Password as `SMTP_PASSWORD`

**For other email providers:**
- Update `SMTP_HOST` and `SMTP_PORT` accordingly
- Check your provider's SMTP settings

### Setting Up SMS Notifications

1. Sign up for a Twilio account: https://www.twilio.com/
2. Get a Twilio phone number
3. Copy your Account SID and Auth Token from the Twilio console
4. Set the environment variables

## Deployment

### Using Docker Compose

The notifier service is already configured in [backend/docker-compose.app.yml](backend/docker-compose.app.yml):

```bash
# Start all services including the notifier
cd backend
docker-compose -f docker-compose.app.yml up -d

# View notifier logs
docker logs -f tee-time-notifier

# Restart notifier after config changes
docker-compose -f docker-compose.app.yml restart tee-time-notifier
```

### Manual Deployment

```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run in consumer mode only
NOTIFIER_MODE=consumer python kafka/consumers/tee_time_notifier_consumer.py

# Run in periodic mode only
NOTIFIER_MODE=periodic python kafka/consumers/tee_time_notifier_consumer.py

# Run both modes (recommended)
NOTIFIER_MODE=both python kafka/consumers/tee_time_notifier_consumer.py
```

## Monitoring

### Logs

The notifier service logs all important events:
- New search requests received
- Matches found
- Notifications sent (with success/failure status)
- Errors and warnings

```bash
# View logs
docker logs -f tee-time-notifier

# Filter for matches
docker logs tee-time-notifier | grep "Match found"

# Filter for sent notifications
docker logs tee-time-notifier | grep "notification sent"
```

### Database Queries

Check notification history:
```sql
-- See all notifications sent
SELECT * FROM tee_time_notifications ORDER BY created_at DESC LIMIT 20;

-- Count notifications per user
SELECT user_id, COUNT(*) as notification_count
FROM tee_time_notifications
GROUP BY user_id
ORDER BY notification_count DESC;

-- Check active searches
SELECT * FROM tee_time_searches WHERE status IN ('pending', 'processing');
```

## Troubleshooting

### Notifications Not Being Sent

1. **Check Kafka connection:**
   ```bash
   docker logs tee-time-notifier | grep "Kafka"
   ```

2. **Verify email credentials:**
   - Test SMTP connection manually
   - Check for authentication errors in logs

3. **Verify Twilio credentials:**
   - Ensure phone number includes country code (+1 for US)
   - Check Twilio account balance

4. **Check database connectivity:**
   ```bash
   docker logs tee-time-notifier | grep "database"
   ```

### Duplicate Notifications

The system prevents duplicates by:
- Tracking sent notifications in `tee_time_notifications` table
- Checking before sending each notification
- Using unique combination of (search_id, tee_time_id)

If duplicates occur:
- Check database constraints
- Review notifier logs for errors

### Performance Issues

If the notifier is slow:
- Increase `MATCHER_CHECK_INTERVAL` to reduce frequency
- Check database query performance
- Monitor system resources (CPU, memory)

## Future Enhancements

Potential improvements:
- [ ] Add web push notifications
- [ ] Implement notification preferences (email only, SMS only, both)
- [ ] Add notification throttling to prevent spam
- [ ] Support multiple notification templates
- [ ] Add notification scheduling (quiet hours)
- [ ] Implement retry logic for failed notifications
- [ ] Add metrics and analytics dashboard

## API Integration

The system automatically sends tee time search requests to Kafka when users submit the form through the FastAPI endpoint:

```python
POST /api/tee-times/search
```

See [backend/src/api/main.py:192-235](backend/src/api/main.py#L192-L235) for implementation details.
