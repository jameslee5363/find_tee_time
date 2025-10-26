# Find Tee Time - Full Stack Application

A full-stack application with React frontend and FastAPI backend, integrated with Kafka and Airflow.

## Architecture

- **Frontend**: React + TypeScript (runs on port 3000)
- **Backend**: FastAPI (runs on port 8000)
- **Message Queue**: Kafka
- **Workflow**: Apache Airflow

## Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

## Quick Start with Docker

### Running Both Frontend and Backend

```bash
# Build and start both containers
docker-compose up --build

# Run in detached mode
docker-compose up -d

# View logs
docker-compose logs -f

# Stop containers
docker-compose down
```

The application will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Running Full Stack with Airflow and Kafka

```bash
# Navigate to backend directory
cd backend

# Start the full stack (Airflow, Kafka, FastAPI)
docker-compose -f docker-compose.app.yml up -d

# Then in project root, start the frontend
cd ..
docker-compose up frontend
```

This will start:
- Airflow Webserver: http://localhost:8081
- FastAPI Backend: http://localhost:8000
- React Frontend: http://localhost:3000

## Development

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build

# Run tests
npm test
```

### Backend Development

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI server
cd src
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### GET /
Returns a welcome message from the API.

**Response:**
```json
{
  "message": "FastAPI with Kafka and Airflow"
}
```

### POST /produce
Sends a message to Kafka.

**Request Body:**
```json
{
  "text": "Your message here"
}
```

**Response:**
```json
{
  "status": "Message sent"
}
```

## Docker Configuration

### Frontend Dockerfile
- Multi-stage build for optimized production image
- Uses nginx to serve static files
- Custom nginx configuration for React Router support

### Backend Dockerfile
- Python 3.11 slim base image
- Non-root user for security
- Hot-reload enabled for development

### Docker Compose
- Separate services for frontend and backend
- Shared network for inter-container communication
- Volume mounting for development hot-reload

## Environment Variables

### Frontend (.env)
```
REACT_APP_API_URL=http://localhost:8000
```

### Backend
```
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
DATABASE_URL=postgresql://airflow:airflow@postgres/airflow
PYTHONPATH=/app/src
```

## Project Structure

```
.
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main React component
│   │   └── ...
│   ├── Dockerfile           # Frontend Docker configuration
│   ├── nginx.conf           # Nginx configuration
│   └── package.json
├── backend/
│   ├── src/
│   │   └── api/
│   │       └── main.py      # FastAPI application
│   ├── Dockerfile.fastapi   # Backend Docker configuration
│   ├── docker-compose.app.yml  # Full stack orchestration
│   └── requirements.txt
└── docker-compose.yml       # Frontend + Backend only
```

## Features

### Frontend
- ✅ TypeScript for type safety
- ✅ Connects to FastAPI backend
- ✅ Displays backend status
- ✅ Send messages to Kafka via API
- ✅ Error handling and loading states
- ✅ Dockerized with nginx

### Backend
- ✅ FastAPI with async support
- ✅ CORS configured for frontend
- ✅ Kafka producer integration
- ✅ Docker support with hot-reload
- ✅ PostgreSQL database connection
- ✅ Airflow integration


