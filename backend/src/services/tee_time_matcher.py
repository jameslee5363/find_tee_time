"""Match tee times against saved searches."""
import json
import logging
from datetime import datetime, time
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker
import os

# Import models - need to handle both Airflow DAG model and FastAPI model
import sys
from pathlib import Path

# Add backend src to path
backend_src = Path(__file__).parent.parent
sys.path.insert(0, str(backend_src))

from database.models import User, TeeTimeSearch, TeeTimeNotification
from notifications import notification_service

logger = logging.getLogger(__name__)

# Airflow database connection (where tee_times table lives)
AIRFLOW_DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://airflow:airflow@postgres/airflow')

# FastAPI database connection (where user searches live)
FASTAPI_DATABASE_URL = os.getenv('FASTAPI_DATABASE_URL', AIRFLOW_DATABASE_URL)


class TeeTime:
    """Lightweight view of a tee_times row."""

    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.tee_time_id = kwargs.get('tee_time_id')
        self.search_date = kwargs.get('search_date')
        self.tee_off_time = kwargs.get('tee_off_time')
        self.tee_off_datetime = kwargs.get('tee_off_datetime')
        self.course_id = kwargs.get('course_id')
        self.course_name = kwargs.get('course_name')
        self.available_spots = kwargs.get('available_spots')
        self.max_players = kwargs.get('max_players')
        self.is_available = kwargs.get('is_available', True)
        self.rate_code = kwargs.get('rate_code')
        self.rate_name = kwargs.get('rate_name')
        self.rate_amount = kwargs.get('rate_amount')
        self.holes = kwargs.get('holes')
        self.booking_class = kwargs.get('booking_class')
        self.is_online_bookable = kwargs.get('is_online_bookable', True)
        self.raw_data = kwargs.get('raw_data')
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')


class TeeTimeMatcherService:
    """Coordinate tee time matching and notifications."""

    def __init__(self):
        # Create engine for Airflow DB (tee_times table)
        self.airflow_engine = create_engine(AIRFLOW_DATABASE_URL)

        # Create engine for FastAPI DB (user searches, notifications)
        self.fastapi_engine = create_engine(FASTAPI_DATABASE_URL)

        self.AirflowSession = sessionmaker(bind=self.airflow_engine)
        self.FastAPISession = sessionmaker(bind=self.fastapi_engine)

    def parse_time(self, time_str: str) -> Optional[time]:
        """Return a time object for an HH:MM or HH:MM:SS string."""
        if not time_str:
            return None
        try:
            # Handle various time formats
            # Strip any whitespace
            time_str = time_str.strip()

            # If it contains a 'T' (ISO format like "2025-10-26T14:50:00"), extract just the time part
            if 'T' in time_str:
                time_str = time_str.split('T')[1]

            # Remove 'Z' or timezone info if present
            if 'Z' in time_str:
                time_str = time_str.split('Z')[0]
            if '+' in time_str:
                time_str = time_str.split('+')[0]
            if '-' in time_str and time_str.count(':') >= 2:
                # This might be timezone offset like -05:00
                time_str = time_str.rsplit('-', 1)[0]

            # Split by colon
            parts = time_str.split(':')
            if len(parts) < 2:
                logger.warning(f"Time string '{time_str}' doesn't have enough parts")
                return None

            # Parse hour and minute (ignore seconds if present)
            hour = int(parts[0])
            minute = int(parts[1])

            return time(hour=hour, minute=minute)
        except Exception as e:
            logger.warning(f"Failed to parse time '{time_str}': {e}")
            return None

    def parse_date(self, date_str: str) -> Optional[datetime]:
        """Return a datetime parsed from accepted tee time formats."""
        if not date_str:
            return None

        # Try different formats
        formats = [
            "%Y-%m-%d",  # 2024-10-26
            "%a %b %d %Y",  # Sat Oct 26 2024
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        logger.warning(f"Failed to parse date '{date_str}'")
        return None

    # All times are now in Eastern Time - no conversion needed

    def matches_search_criteria(
        self,
        tee_time: TeeTime,
        search: TeeTimeSearch
    ) -> bool:
        """Return True if the tee time satisfies the search filters."""
        # Parse course names from JSON
        try:
            course_names = json.loads(search.course_name)
        except (json.JSONDecodeError, TypeError):
            logger.error(f"Failed to parse course_name for search {search.id}")
            return False

        # Check if tee time course matches any of the selected courses
        if tee_time.course_name not in course_names:
            return False

        # Check if tee time has enough spots for group
        if tee_time.available_spots < search.group_size:
            return False

        # Check if tee time is still available
        if not tee_time.is_available:
            return False

        # Check date match
        try:
            preferred_dates = json.loads(search.preferred_dates)
        except (json.JSONDecodeError, TypeError):
            logger.error(f"Failed to parse preferred_dates for search {search.id}")
            return False

        # Parse tee time date
        tee_time_date = self.parse_date(tee_time.search_date)
        if not tee_time_date:
            return False

        # Check if any preferred date matches
        date_matches = False
        for date_str in preferred_dates:
            search_date = self.parse_date(date_str)
            if search_date and search_date.date() == tee_time_date.date():
                date_matches = True
                break

        if not date_matches:
            return False

        # Check time range (if specified)
        if search.preferred_time_start or search.preferred_time_end:
            # Both tee times and user searches are in Eastern Time - compare directly
            tee_off_time = self.parse_time(tee_time.tee_off_time)

            if not tee_off_time:
                logger.warning(f"Could not parse tee off time '{tee_time.tee_off_time}'")
                return False

            # Compare with user's Eastern Time preferences
            if search.preferred_time_start:
                start_time = self.parse_time(search.preferred_time_start)
                if start_time and tee_off_time < start_time:
                    logger.debug(
                        f"Tee time {tee_time.tee_off_time} is before start time {search.preferred_time_start}"
                    )
                    return False

            if search.preferred_time_end:
                end_time = self.parse_time(search.preferred_time_end)
                if end_time and tee_off_time > end_time:
                    logger.debug(
                        f"Tee time {tee_time.tee_off_time} is after end time {search.preferred_time_end}"
                    )
                    return False

        return True

    def has_notification_been_sent(
        self,
        session: Session,
        search_id: int,
        tee_time_id: str
    ) -> bool:
        """Return True if this search/tee time pair already triggered a notification."""
        notification = session.query(TeeTimeNotification).filter(
            and_(
                TeeTimeNotification.search_id == search_id,
                TeeTimeNotification.tee_time_id == tee_time_id
            )
        ).first()

        return notification is not None

    def send_notification(
        self,
        session: Session,
        search: TeeTimeSearch,
        user: User,
        tee_time: TeeTime
    ) -> bool:
        """Send a single-match email and record the event."""
        # Tee time is already in Eastern Time - use as-is
        tee_off_time_et = tee_time.tee_off_time

        # Send email notification
        result = notification_service.send_tee_time_notification(
            user_email=user.email,
            user_name=user.first_name,
            course_name=tee_time.course_name,
            tee_off_date=tee_time.search_date,
            tee_off_time=tee_off_time_et,
            available_spots=tee_time.available_spots,
            group_size=search.group_size
        )

        # Record notification in database
        notification = TeeTimeNotification(
            search_id=search.id,
            user_id=user.id,
            tee_time_id=tee_time.tee_time_id,
            course_name=tee_time.course_name,
            tee_off_date=tee_time.search_date,
            tee_off_time=tee_off_time_et,
            available_spots=tee_time.available_spots,
            email_sent=result['email_sent']
        )

        session.add(notification)
        session.commit()

        logger.info(
            f"Sent notification to user {user.id} for tee time {tee_time.tee_time_id} "
            f"(email: {result['email_sent']})"
        )

        return result['email_sent']

    def send_batched_notification(
        self,
        session: Session,
        search: TeeTimeSearch,
        user: User,
        tee_times: List[TeeTime]
    ) -> bool:
        """Send one email covering multiple matching tee times."""
        if not tee_times:
            return False

        # Prepare list of tee times for email
        tee_time_list = []
        for tee_time in tee_times:
            # Tee time is already in Eastern Time - use as-is
            tee_time_list.append({
                'course_name': tee_time.course_name,
                'tee_off_date': tee_time.search_date,
                'tee_off_time': tee_time.tee_off_time,
                'available_spots': tee_time.available_spots
            })

        # Send batched email notification
        result = notification_service.send_batched_tee_time_notification(
            user_email=user.email,
            user_name=user.first_name,
            search_id=search.id,
            tee_times=tee_time_list,
            group_size=search.group_size
        )

        # Record each notification in database
        for tee_time in tee_times:
            # Tee time is already in Eastern Time - use as-is
            notification = TeeTimeNotification(
                search_id=search.id,
                user_id=user.id,
                tee_time_id=tee_time.tee_time_id,
                course_name=tee_time.course_name,
                tee_off_date=tee_time.search_date,
                tee_off_time=tee_time.tee_off_time,
                available_spots=tee_time.available_spots,
                email_sent=result['email_sent']
            )
            session.add(notification)

        session.commit()

        logger.info(
            f"Sent batched notification to user {user.id} with {len(tee_times)} tee time(s) "
            f"for search {search.id} (email: {result['email_sent']})"
        )

        return result['email_sent']

    def process_search_matches(self, search_id: Optional[int] = None) -> Dict:
        """Process active searches and send notifications for new matches."""
        fastapi_session = self.FastAPISession()
        airflow_session = self.AirflowSession()

        try:
            # Get active searches (exclude cancelled and completed)
            query = fastapi_session.query(TeeTimeSearch).filter(
                TeeTimeSearch.status.in_(['pending', 'processing', 'found_keep_searching'])
            )

            if search_id:
                query = query.filter(TeeTimeSearch.id == search_id)

            searches = query.all()

            logger.info(f"Processing {len(searches)} active search(es)")

            stats = {
                'searches_processed': 0,
                'matches_found': 0,
                'notifications_sent': 0,
                'notifications_failed': 0
            }

            for search in searches:
                stats['searches_processed'] += 1

                # Get user info
                user = fastapi_session.query(User).filter(User.id == search.user_id).first()
                if not user:
                    logger.warning(f"User {search.user_id} not found for search {search.id}")
                    continue

                # Query available tee times from Airflow database
                query_sql = """
                    SELECT *
                    FROM tee_times
                    WHERE is_available = true
                    AND available_spots > 0
                    AND tee_off_datetime >= NOW()
                    ORDER BY tee_off_datetime
                """

                result = airflow_session.execute(query_sql)
                rows = result.fetchall()

                logger.info(f"Found {len(rows)} available tee times to check against search {search.id}")

                # Collect all matching tee times for this search
                matching_tee_times = []

                # Check each tee time against search criteria
                for row in rows:
                    # Convert row to TeeTime object
                    tee_time = TeeTime(**dict(row._mapping))

                    # Check if it matches
                    if self.matches_search_criteria(tee_time, search):
                        # Check if we've already sent notification for this combo
                        if self.has_notification_been_sent(fastapi_session, search.id, tee_time.tee_time_id):
                            logger.info(
                                f"Notification already sent for search {search.id} "
                                f"and tee time {tee_time.tee_time_id}"
                            )
                            continue

                        matching_tee_times.append(tee_time)
                        stats['matches_found'] += 1

                # If we found any new matches, send ONE email with all of them
                if matching_tee_times:
                    logger.info(
                        f"Found {len(matching_tee_times)} new matching tee time(s) for search {search.id}"
                    )

                    # Send batched notification
                    if self.send_batched_notification(fastapi_session, search, user, matching_tee_times):
                        stats['notifications_sent'] += 1
                    else:
                        stats['notifications_failed'] += 1

            logger.info(f"Processing complete: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error processing search matches: {e}")
            raise
        finally:
            fastapi_session.close()
            airflow_session.close()


# Create singleton instance
tee_time_matcher = TeeTimeMatcherService()
