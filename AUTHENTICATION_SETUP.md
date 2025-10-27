# Authentication System Setup Guide

This guide will help you set up and run the beautiful login and registration system for the Tee Time Finder application.

## Overview

The authentication system includes:
- **Backend**: FastAPI with JWT authentication, PostgreSQL database
- **Frontend**: React with TypeScript, beautiful animated UI
- **Features**: User registration with email/phone, login, protected routes

---

## Prerequisites

- Docker and Docker Compose (already configured)
- Node.js 16+ and npm
- Python 3.11+

---

## Quick Start

### 1. Start the Backend Services

First, start the PostgreSQL database and FastAPI backend:

```bash
cd backend
docker-compose -f docker-compose.app.yml up -d postgres
```

Wait for PostgreSQL to be ready (about 10 seconds), then run the database migration:

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run the migration to create the users table
python migrations/run_migrations.py
```

### 2. Start the FastAPI Backend

```bash
# Start the FastAPI server
cd backend
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

The backend API will be available at: http://localhost:8000

You can view the API documentation at: http://localhost:8000/docs

### 3. Start the Frontend

In a new terminal:

```bash
cd frontend
npm install  # Dependencies already installed
npm start
```

The frontend will be available at: http://localhost:3000

---

## Usage

### Accessing the Application

1. Open your browser and navigate to: http://localhost:3000
2. You'll be redirected to the login page
3. Click "Create one now" to register a new account
4. Fill in the registration form:
   - **Email**: Your email address (required)
   - **Phone Number**: Your phone number (required, formatted automatically)
   - **Password**: At least 8 characters (required)
   - **First Name & Last Name**: Optional
5. Click "Create Account"
6. You'll be automatically logged in and redirected to the dashboard

### API Endpoints

The following authentication endpoints are available:

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login with email and password
- `GET /api/auth/me` - Get current user information (requires authentication)

---

## Database Schema

The `users` table includes the following fields:

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Project Structure

### Backend Structure

```
backend/
├── src/
│   ├── api/
│   │   ├── main.py          # FastAPI app with auth endpoints
│   │   └── schemas.py       # Pydantic schemas for validation
│   ├── database/
│   │   ├── models.py        # SQLAlchemy User model
│   │   └── database.py      # Database configuration
│   └── core/
│       └── security.py      # Password hashing & JWT utilities
├── migrations/
│   ├── create_users_table.sql
│   └── run_migrations.py
└── requirements.txt
```

### Frontend Structure

```
frontend/
├── src/
│   ├── pages/
│   │   ├── Login.tsx        # Beautiful login page
│   │   ├── Register.tsx     # Beautiful registration page
│   │   └── Dashboard.tsx    # User dashboard
│   ├── services/
│   │   ├── api.ts          # Axios instance with interceptors
│   │   └── auth.ts         # Authentication service
│   ├── styles/
│   │   ├── Auth.css        # Animated auth page styles
│   │   └── Dashboard.css   # Dashboard styles
│   └── App.tsx             # Main app with routing
└── package.json
```

---

## Features

### Beautiful UI Design
- Animated gradient background with floating shapes
- Glassmorphism card design
- Smooth transitions and hover effects
- Responsive design for mobile and desktop
- Loading states and error handling
- Auto-formatted phone number input

### Security Features
- Password hashing with bcrypt
- JWT token-based authentication
- Protected routes
- Automatic token refresh on API calls
- Session persistence with localStorage

### Form Validation
- Email format validation
- Phone number validation (minimum 10 digits)
- Password strength (minimum 8 characters)
- Password confirmation matching
- Real-time error feedback

---

## Environment Variables

### Backend (.env)

Add the following to your backend `.env` file:

```env
# Database
DATABASE_URL=postgresql://airflow:airflow@localhost:5432/airflow

# JWT Configuration
JWT_SECRET_KEY=your-secret-key-change-this-in-production
```

### Frontend (.env)

The frontend already has:

```env
REACT_APP_API_URL=http://localhost:8000
```

---

## Testing the Authentication

### Test Registration

1. Navigate to http://localhost:3000/register
2. Fill in the form with test data:
   - Email: test@example.com
   - Phone: (555) 123-4567
   - Password: password123
   - First Name: Test
   - Last Name: User
3. Click "Create Account"
4. You should be redirected to the dashboard

### Test Login

1. Logout from the dashboard
2. Navigate to http://localhost:3000/login
3. Enter your credentials:
   - Email: test@example.com
   - Password: password123
4. Click "Sign In"
5. You should be redirected to the dashboard

### Test Protected Routes

1. While logged out, try to access: http://localhost:3000/dashboard
2. You should be automatically redirected to the login page
3. After logging in, you can access the dashboard

---

## Troubleshooting

### Backend Issues

**Issue**: Migration fails with "connection refused"
```bash
# Solution: Make sure PostgreSQL is running
docker-compose -f docker-compose.app.yml up -d postgres
# Wait 10 seconds, then retry the migration
```

**Issue**: Import errors in FastAPI
```bash
# Solution: Make sure all dependencies are installed
pip install -r backend/requirements.txt
```

### Frontend Issues

**Issue**: "Module not found" errors
```bash
# Solution: Reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Issue**: API calls failing
```bash
# Solution: Check that the backend is running on port 8000
curl http://localhost:8000/
# Should return: {"message": "Hello from backend"}
```

### Database Issues

**Issue**: "relation users does not exist"
```bash
# Solution: Run the migration
cd backend
python migrations/run_migrations.py
```

---

## Next Steps

1. **Add Email Verification**: Implement email verification for new users
2. **Password Reset**: Add forgot password functionality
3. **OAuth Integration**: Add Google/Facebook login
4. **Profile Management**: Allow users to update their information
5. **Two-Factor Authentication**: Add 2FA for enhanced security

---

## Screenshots

### Login Page
- Beautiful gradient background with animated shapes
- Clean, modern form design
- Smooth animations and transitions

### Registration Page
- Two-column layout for name fields
- Auto-formatted phone number input
- Real-time password validation
- Confirmation password check

### Dashboard
- User profile information
- Account status badges
- Feature cards with hover effects
- Responsive navigation bar

---

## API Documentation

Once the backend is running, visit http://localhost:8000/docs for interactive API documentation with Swagger UI.

---

## Support

For issues or questions, please check:
1. This README
2. API documentation at http://localhost:8000/docs
3. Browser console for frontend errors
4. Backend logs in the terminal

---

**Enjoy your beautiful authentication system!**
