from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from kafka import KafkaProducer
from sqlalchemy.orm import Session
import os
import json
import sys
from pathlib import Path

# Add src directory to path for local development
src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

try:
    # Try absolute imports first (for Docker)
    from api.schemas import (
        UserCreate, UserLogin, UserResponse, Token, ErrorResponse,
        TeeTimeSearchCreate, TeeTimeSearchResponse,
        TeeTimeNotificationResponse, NotificationAcknowledgeRequest
    )
    from database.database import get_db, init_db
    from database.models import User, TeeTimeSearch, TeeTimeNotification
    from core.security import (
        verify_password,
        get_password_hash,
        create_access_token,
        decode_access_token
    )
except ModuleNotFoundError:
    # Fall back to relative imports (for local development)
    from .schemas import (
        UserCreate, UserLogin, UserResponse, Token, ErrorResponse,
        TeeTimeSearchCreate, TeeTimeSearchResponse,
        TeeTimeNotificationResponse, NotificationAcknowledgeRequest
    )
    from ..database.database import get_db, init_db
    from ..database.models import User, TeeTimeSearch, TeeTimeNotification
    from ..core.security import (
        verify_password,
        get_password_hash,
        create_access_token,
        decode_access_token
    )

app = FastAPI(title="Tee Time Finder API")

# Security
security = HTTPBearer()

# Configure CORS - Allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")

@app.on_event("startup")
async def startup_event():
    # Initialize database
    try:
        init_db()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"⚠ Warning: Database initialization error: {e}")

    # Initialize Kafka producer (optional - gracefully handle if Kafka is not available)
    try:
        app.state.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            request_timeout_ms=5000,
            max_block_ms=5000
        )
        print("✓ Kafka producer initialized successfully")
    except Exception as e:
        print(f"⚠ Warning: Could not connect to Kafka: {e}")
        print("  API will still work, but /produce endpoint will fail")
        app.state.producer = None

@app.get("/")
def read_root():
    return {"message": "Hello from backend"}

@app.post("/produce")
async def produce_message(message: dict):
    # Send message to Kafka
    if app.state.producer is None:
        return {"status": "Error: Kafka producer not available", "error": True}

    try:
        app.state.producer.send("my-topic", value=str(message).encode('utf-8'))
        return {"status": "Message sent"}
    except Exception as e:
        return {"status": f"Error sending message: {str(e)}", "error": True}


# Authentication Endpoints

@app.post("/api/auth/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        phone_number=user_data.phone_number,
        password_hash=hashed_password,
        first_name=user_data.first_name,
        last_name=user_data.last_name
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Create access token
    access_token = create_access_token(data={"sub": new_user.email, "user_id": new_user.id})

    # Return token and user data
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(new_user)
    }


@app.post("/api/auth/login", response_model=Token)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Login an existing user."""
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    # Create access token
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id})

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from token."""
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    return user


@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user information."""
    return UserResponse.model_validate(current_user)


# Tee Time Search Endpoints

@app.post("/api/tee-times/search", response_model=TeeTimeSearchResponse, status_code=status.HTTP_201_CREATED)
async def create_tee_time_search(
    search_data: TeeTimeSearchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new tee time search request. Times should be provided in UTC format."""
    # Create new search request
    new_search = TeeTimeSearch(
        user_id=current_user.id,
        course_name=search_data.course_name,
        preferred_dates=json.dumps(search_data.preferred_dates),
        preferred_time_start=search_data.preferred_time_start,
        preferred_time_end=search_data.preferred_time_end,
        group_size=search_data.group_size,
        status="pending"
    )

    db.add(new_search)
    db.commit()
    db.refresh(new_search)

    # Send to Kafka if available (for future processing)
    if app.state.producer is not None:
        try:
            kafka_message = {
                "search_id": new_search.id,
                "user_id": current_user.id,
                "course_name": search_data.course_name,
                "preferred_dates": search_data.preferred_dates,
                "preferred_time_start": search_data.preferred_time_start,
                "preferred_time_end": search_data.preferred_time_end,
                "group_size": search_data.group_size
            }
            app.state.producer.send(
                "tee-time-searches",
                value=json.dumps(kafka_message).encode('utf-8')
            )
            print(f"Sent tee time search {new_search.id} to Kafka")
        except Exception as e:
            print(f"Failed to send to Kafka: {e}")
            # Continue even if Kafka fails

    return TeeTimeSearchResponse.model_validate(new_search)


@app.get("/api/tee-times/search", response_model=list[TeeTimeSearchResponse])
async def get_user_searches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all tee time searches for the current user."""
    searches = db.query(TeeTimeSearch).filter(
        TeeTimeSearch.user_id == current_user.id
    ).order_by(TeeTimeSearch.created_at.desc()).all()

    return [TeeTimeSearchResponse.model_validate(search) for search in searches]


@app.get("/api/tee-times/search/{search_id}", response_model=TeeTimeSearchResponse)
async def get_search_by_id(
    search_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific tee time search by ID."""
    search = db.query(TeeTimeSearch).filter(
        TeeTimeSearch.id == search_id,
        TeeTimeSearch.user_id == current_user.id
    ).first()

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found"
        )

    return TeeTimeSearchResponse.model_validate(search)


@app.delete("/api/tee-times/search/{search_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_search(
    search_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel/delete a tee time search request."""
    search = db.query(TeeTimeSearch).filter(
        TeeTimeSearch.id == search_id,
        TeeTimeSearch.user_id == current_user.id
    ).first()

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found"
        )

    db.delete(search)
    db.commit()
    return None


@app.patch("/api/tee-times/search/{search_id}/status", response_model=TeeTimeSearchResponse)
async def update_search_status(
    search_id: int,
    new_status: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the status of a tee time search.
    Valid statuses: pending, processing, completed, cancelled, found_keep_searching
    """
    valid_statuses = ["pending", "processing", "completed", "cancelled", "found_keep_searching"]

    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    search = db.query(TeeTimeSearch).filter(
        TeeTimeSearch.id == search_id,
        TeeTimeSearch.user_id == current_user.id
    ).first()

    if not search:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Search not found"
        )

    search.status = new_status
    db.commit()
    db.refresh(search)

    return TeeTimeSearchResponse.model_validate(search)

# Notification Endpoints

@app.get("/api/notifications/unacknowledged", response_model=list[TeeTimeNotificationResponse])
async def get_unacknowledged_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all unacknowledged notifications for the current user."""
    notifications = db.query(TeeTimeNotification).filter(
        TeeTimeNotification.user_id == current_user.id,
        TeeTimeNotification.user_acknowledged == False,
        TeeTimeNotification.email_sent == True
    ).order_by(TeeTimeNotification.notification_sent_at.desc()).all()

    return [TeeTimeNotificationResponse.model_validate(notif) for notif in notifications]


@app.post("/api/notifications/acknowledge")
async def acknowledge_notifications(
    request: NotificationAcknowledgeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Acknowledge notifications and take action on the associated search.
    Actions:
    - 'booked': Mark search as completed (user booked the tee time)
    - 'keep_searching': Keep search active with status 'found_keep_searching'
    - 'no_longer_available': Keep search active (continue searching)
    """
    # Get notifications
    notifications = db.query(TeeTimeNotification).filter(
        TeeTimeNotification.id.in_(request.notification_ids),
        TeeTimeNotification.user_id == current_user.id
    ).all()

    if not notifications:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notifications not found"
        )

    # Mark notifications as acknowledged
    for notification in notifications:
        notification.user_acknowledged = True
        notification.user_action = request.action

    # Update search status based on action
    search_ids = list(set([n.search_id for n in notifications]))
    
    for search_id in search_ids:
        search = db.query(TeeTimeSearch).filter(TeeTimeSearch.id == search_id).first()
        if search:
            if request.action == 'booked':
                # User booked the tee time, cancel the search
                search.status = 'completed'
            elif request.action == 'keep_searching':
                # Keep searching with status indicating tee time was found
                search.status = 'found_keep_searching'
            elif request.action == 'no_longer_available':
                # Tee time no longer available, keep searching
                search.status = 'pending'

    db.commit()

    return {
        "success": True,
        "message": f"Acknowledged {len(notifications)} notification(s)",
        "action_taken": request.action
    }
