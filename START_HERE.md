# Quick Start Guide

Your authentication system is ready to use. The SQLAlchemy dependency conflict has been resolved, and the database is configured.

---

## Start the Application

### 1. Start Backend (FastAPI)

```bash
cd /Users/jameslee/Desktop/find_tee_time/backend
python3 -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: **http://localhost:8000**

API docs at: **http://localhost:8000/docs**

### 2. Start Frontend (React) - In a New Terminal

```bash
cd /Users/jameslee/Desktop/find_tee_time/frontend
npm start
```

Frontend will be available at: **http://localhost:3000**

---

## Database Info

- **PostgreSQL**: Running in Docker on port **5433**
- **Users table**: Already created
- **Connection**: `postgresql://airflow:airflow@localhost:5433/airflow`

---

## Test the App

1. Open http://localhost:3000
2. Click "Create one now" to register
3. Fill in:
   - Email: test@example.com
   - Phone: (555) 123-4567
   - Password: password123
4. You'll be logged in and redirected to the dashboard!

---

## What's Been Fixed

- SQLAlchemy downgraded to 1.4.51 (compatible with Airflow)
- PostgreSQL port changed to 5433 (avoiding conflicts)
- Database configuration updated
- Pydantic schemas updated for SQLAlchemy 1.4
- Users table created successfully

---

## Troubleshooting

**Backend won't start?**
```bash
# Make sure PostgreSQL is running
cd backend
docker-compose -f docker-compose.app.yml ps postgres

# Should show "Up" status
```

**Can't connect to database?**
```bash
# Test connection directly
docker-compose -f docker-compose.app.yml exec postgres psql -U airflow -d airflow -c "SELECT * FROM users;"
```

**Port conflicts?**
- Backend runs on port 8000
- Frontend runs on port 3000
- PostgreSQL runs on port 5433

---

## API Endpoints

- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `GET /api/auth/me` - Get current user (requires token)

---


