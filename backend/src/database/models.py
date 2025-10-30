"""
Database models for the application.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"


class TeeTimeSearch(Base):
    """Model for storing tee time search requests. All times stored in Eastern Time."""
    __tablename__ = "tee_time_searches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    course_name = Column(Text, nullable=False)  # JSON string of course name(s)
    preferred_dates = Column(Text, nullable=False)  # JSON string of date strings (YYYY-MM-DD)
    preferred_time_start = Column(String(10))  # Eastern Time in HH:MM format
    preferred_time_end = Column(String(10))  # Eastern Time in HH:MM format
    group_size = Column(Integer, nullable=False)
    status = Column(String(50), default="pending", index=True)  # pending, processing, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<TeeTimeSearch(id={self.id}, course={self.course_name}, user_id={self.user_id})>"


class TeeTimeNotification(Base):
    """Model for tracking sent notifications about available tee times."""
    __tablename__ = "tee_time_notifications"

    id = Column(Integer, primary_key=True, index=True)
    search_id = Column(Integer, ForeignKey("tee_time_searches.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    tee_time_id = Column(String(100), nullable=False, index=True)  # From tee_times table

    # Notification details
    course_name = Column(String(255), nullable=False)
    tee_off_date = Column(String(50), nullable=False)
    tee_off_time = Column(String(20), nullable=False)
    available_spots = Column(Integer, nullable=False)

    # Notification status
    email_sent = Column(Boolean, default=False)
    notification_sent_at = Column(DateTime(timezone=True), server_default=func.now())
    user_acknowledged = Column(Boolean, default=False)
    user_action = Column(String(50))  # 'booked', 'keep_searching', 'no_longer_available'

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<TeeTimeNotification(id={self.id}, search_id={self.search_id}, user_id={self.user_id})>"
