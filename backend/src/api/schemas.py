"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
import re

class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    phone_number: str
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    @validator('phone_number')
    def validate_phone(cls, v):
        # Remove any non-digit characters
        cleaned = re.sub(r'\D', '', v)
        if len(cleaned) < 10:
            raise ValueError('Phone number must be at least 10 digits')
        return cleaned

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password is too long (max 72 bytes)')
        return v

class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    email: str
    phone_number: str
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    """Schema for authentication token."""
    access_token: str
    token_type: str
    user: UserResponse

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str


class TeeTimeSearchCreate(BaseModel):
    """Schema for creating a tee time search request."""
    course_names: List[str]  # List of course names
    preferred_dates: List[str]  # List of dates in YYYY-MM-DD format
    preferred_time_start: Optional[str] = None  # Eastern Time in HH:MM format
    preferred_time_end: Optional[str] = None  # Eastern Time in HH:MM format
    group_size: int

    @validator('course_names')
    def validate_course_names(cls, v):
        valid_courses = [
            "Valley Brook 18",
            "Darlington 18",
            "Soldier Hill 18",
            "Overpeck 18",
            "Rockleigh R/W 18",
            "Orchard Hills",
            "Darlington Back 9",
            "Rockleigh Back 9",
            "Valley Brook 9",
            "Rockleigh Blue 9",
            "Soldier Hill Back 9",
            "Overpeck Back 9"
        ]
        if not v or len(v) == 0:
            raise ValueError('At least one course name is required')

        # Validate each course name
        for course in v:
            if course.strip() not in valid_courses:
                raise ValueError(f'Invalid course name: {course}. Must be one of: {", ".join(valid_courses)}')

        return [c.strip() for c in v]

    @validator('preferred_dates')
    def validate_dates(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one preferred date is required')
        # Validate date format
        for date_str in v:
            try:
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                raise ValueError(f'Invalid date format: {date_str}. Use YYYY-MM-DD format')
        return v

    @validator('preferred_time_start', 'preferred_time_end')
    def validate_time(cls, v):
        if v is None or v == '':
            return None  # Convert empty strings to None
        # Validate time format HH:MM
        time_pattern = re.compile(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
        if not time_pattern.match(v):
            raise ValueError(f'Invalid time format: {v}. Use HH:MM format (00:00 to 23:59)')
        return v

    @validator('group_size')
    def validate_group_size(cls, v):
        if v < 1:
            raise ValueError('Group size must be at least 1')
        if v > 4:
            raise ValueError('Group size cannot exceed 4')
        return v


class TeeTimeSearchResponse(BaseModel):
    """Schema for tee time search response."""
    id: int
    user_id: int
    course_name: str
    preferred_dates: str  # JSON string
    preferred_time_start: Optional[str]
    preferred_time_end: Optional[str]
    group_size: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TeeTimeNotificationResponse(BaseModel):
    """Schema for tee time notification response."""
    id: int
    search_id: int
    user_id: int
    tee_time_id: str
    course_name: str
    tee_off_date: str
    tee_off_time: str
    available_spots: int
    email_sent: bool
    notification_sent_at: datetime
    user_acknowledged: bool
    user_action: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationAcknowledgeRequest(BaseModel):
    """Schema for acknowledging notifications."""
    notification_ids: List[int]
    action: str  # 'booked', 'keep_searching', 'no_longer_available'

    @validator('action')
    def validate_action(cls, v):
        valid_actions = ['booked', 'keep_searching', 'no_longer_available']
        if v not in valid_actions:
            raise ValueError(f'Invalid action. Must be one of: {", ".join(valid_actions)}')
        return v
