import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import requests
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import BranchPythonOperator
from airflow.utils.dates import days_ago
from airflow.models import Variable
import logging
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert

# Configuration
TOKEN_CACHE_FILE = Path('/tmp/bergen_county_golf_token.json')
TEE_TIMES_OUTPUT_DIR = Path('/tmp/tee_times')

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://airflow:airflow@postgres/airflow')

# Database Models
Base = declarative_base()

class TeeTime(Base):
    __tablename__ = 'tee_times'

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Tee time identification
    tee_time_id = Column(String(100), unique=True, nullable=False)  # Unique ID from API
    search_date = Column(String(50), nullable=False)  # The date we searched for
    tee_off_time = Column(String(20), nullable=False)  # e.g., "08:30"
    tee_off_datetime = Column(DateTime, nullable=True)  # Parsed datetime

    # Course information
    course_id = Column(Integer, nullable=True)
    course_name = Column(String(200), nullable=True)

    # Availability
    available_spots = Column(Integer, nullable=True)
    max_players = Column(Integer, nullable=True)
    is_available = Column(Boolean, default=True)  # Track if tee time is still available

    # Pricing
    rate_code = Column(String(50), nullable=True)
    rate_name = Column(String(200), nullable=True)
    rate_amount = Column(Float, nullable=True)

    # Additional details
    holes = Column(Integer, nullable=True)  # 9 or 18
    booking_class = Column(String(50), nullable=True)
    is_online_bookable = Column(Boolean, default=True)

    # Raw data from API
    raw_data = Column(JSON, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<TeeTime(id={self.id}, date={self.search_date}, time={self.tee_off_time}, course={self.course_name})>"

# DAG Configuration
default_args = {
    'owner': 'golf-scheduler',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def ensure_database_schema():
    """Ensure database schema is up to date with migrations"""
    engine = create_engine(DATABASE_URL)

    try:
        with engine.connect() as conn:
            # Check if is_available column exists
            result = conn.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name='tee_times' AND column_name='is_available';
                """
            )

            if not result.fetchone():
                logging.warning("Column 'is_available' does not exist. Running migration...")

                # Add the column
                conn.execute(
                    """
                    ALTER TABLE tee_times
                    ADD COLUMN is_available BOOLEAN DEFAULT TRUE;
                    """
                )

                # Update existing records
                conn.execute(
                    """
                    UPDATE tee_times
                    SET is_available = TRUE
                    WHERE is_available IS NULL;
                    """
                )

                conn.commit()
                logging.info("Successfully added 'is_available' column")
            else:
                logging.info("Database schema is up to date")

    except Exception as e:
        logging.error(f"Failed to check/update database schema: {e}")
        # Don't raise - allow DAG to continue, as Base.metadata.create_all will handle it
    finally:
        engine.dispose()

class BergenCountyGolfClient:
    def __init__(self):
        self.session = requests.Session()
        self.base_url = "https://bergencountygolf.cps.golf"
        self.token = None
        self.token_expiry = None
        self.logger = logging.getLogger(__name__)
        
    def load_cached_token(self):
        """Load token from cache file if it exists and is valid"""
        if TOKEN_CACHE_FILE.exists():
            try:
                with open(TOKEN_CACHE_FILE, 'r') as f:
                    cache_data = json.load(f)
                    
                expiry_str = cache_data.get('expiry')
                if expiry_str:
                    expiry = datetime.fromisoformat(expiry_str)
                    # Check if token is still valid (with 5 minute buffer)
                    if datetime.now() < (expiry - timedelta(minutes=5)):
                        self.token = cache_data.get('token')
                        self.token_expiry = expiry
                        self.logger.info(f"Loaded valid token from cache, expires at {expiry}")
                        return True
                    else:
                        self.logger.info("Cached token is expired")
            except Exception as e:
                self.logger.warning(f"Failed to load cached token: {e}")
        return False
    
    def save_token_to_cache(self):
        """Save current token to cache file"""
        if self.token and self.token_expiry:
            cache_data = {
                'token': self.token,
                'expiry': self.token_expiry.isoformat(),
                'cached_at': datetime.now().isoformat()
            }
            try:
                with open(TOKEN_CACHE_FILE, 'w') as f:
                    json.dump(cache_data, f)
                self.logger.info(f"Saved token to cache, expires at {self.token_expiry}")
            except Exception as e:
                self.logger.warning(f"Failed to save token to cache: {e}")
    
    def login(self, username, password):
        """Login and get authentication token"""
        # First try to use cached token
        if self.load_cached_token():
            return True
            
        login_url = f"{self.base_url}/identityapi/connect/token"
        
        login_data = {
            'grant_type': 'password',
            'scope': 'openid profile onlinereservation sale inventory sh customer email recommend references',
            'username': username,
            'password': password,
            'client_id': 'js1',
            'client_secret': 'v4secret'
        }
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'client-id': 'onlineresweb',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Expires': 'Sat, 01 Jan 2000 00:00:00 GMT',
            'If-Modified-Since': '0',
            'Origin': 'https://bergencountygolf.cps.golf',
            'Pragma': 'no-cache',
            'Referer': 'https://bergencountygolf.cps.golf/onlineresweb/auth/login',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15',
            'x-apiKey': '8ea2914e-cac2-48a7-a3e5-e0f41350bf3a',
            'x-componentid': '1',
            'x-ismobile': 'false',
            'x-moduleid': '7',
            'x-productid': '1',
            'x-siteid': '7',
            'X-TerminalId': '3',
            'x-timezone-offset': '240',
            'x-timezoneid': 'America/New_York',
            'x-websiteid': '56da39c5-8293-4749-62b1-08daf5ccc931'
        }
        
        response = self.session.post(login_url, data=login_data, headers=headers)
        
        if response.status_code == 200:
            token_data = response.json()
            self.token = token_data.get('access_token')
            if self.token:
                expires_in = token_data.get('expires_in', 3600)
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                self.save_token_to_cache()  # Save to cache
                self.logger.info("Login successful!")
                return True
            else:
                self.logger.error("No access token in response")
                return False
        else:
            self.logger.error(f"Login failed: {response.status_code}")
            return False
    
    def is_token_valid(self):
        """Check if current token is still valid"""
        if not self.token or not self.token_expiry:
            return False
        return datetime.now() < (self.token_expiry - timedelta(minutes=1))
    
    def get_tee_times(self, search_date):
        """Get available tee times"""
        if not self.is_token_valid():
            self.logger.info("Token is not valid, need to re-authenticate")
            return None
            
        url = f"{self.base_url}/onlineres/onlineapi/api/v1/onlinereservation/TeeTimes"
        
        params = {
            "searchDate": search_date,
            "holes": 0,
            "numberOfPlayer": 0,
            "courseIds": "4,5,9,7,8,11,12,10,2,3,13,14",
            "searchTimeType": 0,
            "teeOffTimeMin": 0,
            "teeOffTimeMax": 23,
            "isChangeTeeOffTime": "true",
            "teeSheetSearchView": 5,
            "classCode": "R",
            "defaultOnlineRate": "N",
            "isUseCapacityPricing": "false",
            "memberStoreId": 1,
            "searchType": 1
        }
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json, text/plain, */*",
            "Authorization": f"Bearer {self.token}",
            "x-apiKey": "8ea2914e-cac2-48a7-a3e5-e0f41350bf3a",
            "x-componentid": "1",
            "x-ismobile": "false",
            "x-moduleid": "7",
            "x-productid": "1",
            "x-siteid": "7",
            "X-TerminalId": "3",
            "x-timezone-offset": "240",
            "x-timezoneid": "America/New_York",
            "x-websiteid": "56da39c5-8293-4749-62b1-08daf5ccc931"
        }
        
        response = self.session.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            # Token might be expired even though we checked
            self.logger.warning("Got 401 - token might be expired")
            self.token = None
            self.token_expiry = None
            return None
        else:
            self.logger.error(f"Failed to get tee times: {response.status_code}")
            return None

# Airflow Task Functions
def check_token_validity(**context):
    """Check if we have a valid cached token"""
    if TOKEN_CACHE_FILE.exists():
        try:
            with open(TOKEN_CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                expiry_str = cache_data.get('expiry')
                if expiry_str:
                    expiry = datetime.fromisoformat(expiry_str)
                    if datetime.now() < (expiry - timedelta(minutes=5)):
                        context['task_instance'].xcom_push(key='token_valid', value=True)
                        context['task_instance'].xcom_push(key='cached_token', value=cache_data['token'])
                        logging.info("Token is valid, skipping login")
                        return 'fetch_tee_times'
        except Exception as e:
            logging.warning(f"Error checking token: {e}")
    
    logging.info("Token invalid or missing, need to login")
    return 'authenticate'

def authenticate_task(**context):
    """Authenticate and get token"""
    # Get credentials from Airflow Variables (more secure than environment variables)
    try:
        username = Variable.get("GOLF_USERNAME")
        password = Variable.get("GOLF_PASSWORD")
    except:
        # Fallback to environment variables
        username = os.getenv('GOLF_USERNAME')
        password = os.getenv('GOLF_PASSWORD')
    
    if not username or not password:
        raise ValueError("Golf credentials not configured in Airflow Variables or environment")
    
    client = BergenCountyGolfClient()
    if client.login(username, password):
        context['task_instance'].xcom_push(key='token', value=client.token)
        context['task_instance'].xcom_push(key='token_expiry', value=client.token_expiry.isoformat())
        return True
    else:
        raise Exception("Failed to authenticate with golf system")

def fetch_tee_times_task(**context):
    """Fetch available tee times for all dates from today/tomorrow through 7 days out"""
    client = BergenCountyGolfClient()

    # Load token from cache or XCom
    if not client.load_cached_token():
        # Try to get from XCom if we just authenticated
        token = context['task_instance'].xcom_pull(key='token', task_ids='authenticate')
        if token:
            client.token = token
            token_expiry_str = context['task_instance'].xcom_pull(key='token_expiry', task_ids='authenticate')
            client.token_expiry = datetime.fromisoformat(token_expiry_str)
        else:
            raise Exception("No valid token available")

    # Determine date range based on current time
    now = datetime.now()
    current_hour = now.hour

    # If it's past 7:00 PM (19:00), start from today; otherwise start from tomorrow
    if current_hour >= 19:
        start_day = 1  # Tomorrow
        logging.info("It's past 7:00 PM - fetching tee times starting from today")
    else:
        start_day = 0  # Today
        logging.info("It's before 7:00 PM - fetching tee times starting from tomorrow")

    # Fetch tee times for all dates from start_day through 7 days from now
    all_tee_times = {}
    total_slots = 0

    for days_ahead in range(start_day, 8):  # 0-7 or 1-7 depending on time
        search_date = (now + timedelta(days=days_ahead)).strftime("%a %b %d %Y")
        logging.info(f"Fetching tee times for {search_date} ({days_ahead} days ahead)")

        tee_times = client.get_tee_times(search_date)

        if tee_times:
            all_tee_times[search_date] = tee_times

            # Count slots (API returns 'content' not 'data')
            if isinstance(tee_times, dict):
                slots = tee_times.get('content', tee_times.get('data', []))
                slot_count = len(slots)
                total_slots += slot_count
                logging.info(f"  Found {slot_count} tee times for {search_date}")
        else:
            logging.warning(f"  Failed to fetch tee times for {search_date}")
            all_tee_times[search_date] = None

    if all_tee_times:
        # Store results
        context['task_instance'].xcom_push(key='tee_times', value=all_tee_times)
        context['task_instance'].xcom_push(key='total_dates', value=len(all_tee_times))

        logging.info(f"Successfully fetched tee times for {len(all_tee_times)} dates with {total_slots} total slots")

        return all_tee_times
    else:
        raise Exception("Failed to fetch any tee times")

def process_tee_times_task(**context):
    """Process and analyze tee times"""
    all_tee_times = context['task_instance'].xcom_pull(key='tee_times', task_ids='fetch_tee_times')

    if not all_tee_times:
        logging.warning("No tee times data to process")
        return

    # Process the data (example: find morning times across all dates)
    morning_times = []

    for search_date, tee_times in all_tee_times.items():
        if not tee_times:
            continue

        # API returns 'content' not 'data'
        slots = tee_times.get('content', tee_times.get('data', [])) if isinstance(tee_times, dict) else []
        if slots:
            for slot in slots:
                # Extract time and check if it's morning (before noon)
                time_str = slot.get('startTime', slot.get('teeOffTime', ''))
                if time_str:
                    try:
                        hour = int(time_str.split(':')[0])
                        if hour < 12:
                            morning_times.append({
                                'date': search_date,
                                'time': time_str,
                                'course': slot.get('courseName', 'Unknown'),
                                'available': slot.get('availableSpots', 0)
                            })
                    except:
                        pass

    logging.info(f"Found {len(morning_times)} morning tee times across all dates")
    for slot in morning_times[:10]:  # Log first 10
        logging.info(f"  {slot['date']} {slot['time']} - {slot['course']} ({slot['available']} spots)")

    # You could add notification logic here (email, Slack, etc.)
    return morning_times

def dump_tee_times_to_json(**context):
    """Dump tee times to a timestamped JSON file"""
    all_tee_times = context['task_instance'].xcom_pull(key='tee_times', task_ids='fetch_tee_times')

    if not all_tee_times:
        logging.warning("No tee times data to dump")
        return

    # Create output directory if it doesn't exist
    TEE_TIMES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = TEE_TIMES_OUTPUT_DIR / f"tee_times_{timestamp}.json"

    # Calculate total slots across all dates
    total_slots = 0
    for tee_times in all_tee_times.values():
        if isinstance(tee_times, dict):
            slots = tee_times.get('content', tee_times.get('data', []))
            total_slots += len(slots)

    # Prepare output data
    output_data = {
        'timestamp': datetime.now().isoformat(),
        'dates_fetched': list(all_tee_times.keys()),
        'tee_times_by_date': all_tee_times,
        'summary': {
            'total_dates': len(all_tee_times),
            'total_slots': total_slots
        }
    }

    # Write to JSON file
    try:
        with open(filename, 'w') as f:
            json.dump(output_data, f, indent=2)
        logging.info(f"Successfully dumped tee times for {len(all_tee_times)} dates ({total_slots} total slots) to {filename}")

        # Store filename in XCom for potential downstream tasks
        context['task_instance'].xcom_push(key='output_file', value=str(filename))

        return str(filename)
    except Exception as e:
        logging.error(f"Failed to dump tee times to JSON: {e}")
        raise

def save_tee_times_to_database(**context):
    """Save tee times to PostgreSQL database"""
    all_tee_times = context['task_instance'].xcom_pull(key='tee_times', task_ids='fetch_tee_times')

    if not all_tee_times:
        logging.warning("No tee times data to save to database")
        return

    # Ensure database schema is up to date
    ensure_database_schema()

    # Create database connection
    engine = create_engine(DATABASE_URL)

    # Create tables if they don't exist
    Base.metadata.create_all(engine)

    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        saved_count = 0
        updated_count = 0
        total_processed = 0
        current_tee_time_ids = []  # Track all tee time IDs from current fetch

        # Process tee times for each date
        for search_date, tee_times in all_tee_times.items():
            if not tee_times:
                logging.warning(f"No tee times data for {search_date}")
                continue

            logging.info(f"Processing tee times for {search_date}")

            # Process tee times data for this date (API returns 'content' not 'data')
            slots = tee_times.get('content', tee_times.get('data', [])) if isinstance(tee_times, dict) else []
            if slots:
                for slot in slots:
                    total_processed += 1

                    # Extract tee off time (API uses 'startTime', backup to 'teeOffTime')
                    tee_off_time_str = slot.get('startTime', slot.get('teeOffTime', ''))

                    # Generate unique ID for this tee time
                    tee_time_id = f"{slot.get('courseId', '')}_{tee_off_time_str}_{search_date}_{slot.get('defaultRateCode', slot.get('rateCode', ''))}"
                    current_tee_time_ids.append(tee_time_id)  # Track this ID

                    # Parse tee off time to datetime if possible
                    tee_off_datetime = None
                    try:
                        if tee_off_time_str and search_date:
                            # Try parsing ISO format first (e.g., "2025-10-26T14:50:00")
                            if 'T' in tee_off_time_str:
                                tee_off_datetime = datetime.fromisoformat(tee_off_time_str.replace('Z', '+00:00'))
                            else:
                                # Fallback to manual parsing
                                datetime_str = f"{search_date} {tee_off_time_str}"
                                tee_off_datetime = datetime.strptime(datetime_str, "%a %b %d %Y %H:%M")
                    except Exception as e:
                        logging.warning(f"Could not parse datetime for {search_date} {tee_off_time_str}: {e}")

                    # Extract price info from shItemPrices
                    rate_amount = None
                    rate_name = None
                    rate_code = slot.get('defaultRateCode', slot.get('rateCode'))

                    sh_item_prices = slot.get('shItemPrices', [])
                    if sh_item_prices and len(sh_item_prices) > 0:
                        first_price = sh_item_prices[0]
                        rate_amount = first_price.get('price', first_price.get('displayPrice'))
                        rate_name = first_price.get('itemDesc')
                        if not rate_code:
                            rate_code = first_price.get('rateCode')

                    # Determine available spots
                    available_participants = slot.get('availableParticipantNo', [])
                    available_spots = len(available_participants) if available_participants else slot.get('participants', 0)

                    # Prepare tee time data
                    tee_time_data = {
                        'tee_time_id': tee_time_id,
                        'search_date': search_date,
                        'tee_off_time': tee_off_time_str,
                        'tee_off_datetime': tee_off_datetime,
                        'course_id': slot.get('courseId'),
                        'course_name': slot.get('courseName'),
                        'available_spots': available_spots,
                        'max_players': slot.get('maxPlayer', slot.get('maxPlayers', slot.get('participants'))),
                        'rate_code': rate_code,
                        'rate_name': rate_name,
                        'rate_amount': rate_amount,
                        'holes': slot.get('holes', slot.get('defaultHoles')),
                        'booking_class': slot.get('defaultClassCode', slot.get('bookingClass')),
                        'is_online_bookable': not slot.get('isNotAllowTwosomeBooking', False),
                        'is_available': True,  # Mark as available since we just fetched it
                        'raw_data': slot,
                        'updated_at': datetime.utcnow()
                    }

                    # Use insert with on_conflict_do_update to handle duplicates
                    stmt = insert(TeeTime).values(**tee_time_data)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['tee_time_id'],
                        set_={
                            'available_spots': stmt.excluded.available_spots,
                            'rate_amount': stmt.excluded.rate_amount,
                            'is_available': stmt.excluded.is_available,
                            'raw_data': stmt.excluded.raw_data,
                            'updated_at': stmt.excluded.updated_at,
                        }
                    )

                    result = session.execute(stmt)

                    # Check if it was an insert or update
                    if result.rowcount > 0:
                        # Check if we're updating existing record
                        existing = session.query(TeeTime).filter_by(tee_time_id=tee_time_id).first()
                        if existing and existing.created_at < datetime.utcnow() - timedelta(seconds=1):
                            updated_count += 1
                        else:
                            saved_count += 1

        # Mark tee times that are no longer available (not in current fetch)
        # Only check tee times for today and future dates
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Find all tee times that were previously available but are not in the current fetch
        missing_tee_times = session.query(TeeTime).filter(
            TeeTime.is_available == True,
            TeeTime.tee_time_id.notin_(current_tee_time_ids),
            TeeTime.tee_off_datetime >= today_start
        ).all()

        marked_unavailable = 0
        for tee_time in missing_tee_times:
            tee_time.is_available = False
            tee_time.available_spots = 0
            tee_time.updated_at = datetime.utcnow()
            marked_unavailable += 1
            logging.info(f"Marked as unavailable: {tee_time.course_name} at {tee_time.tee_off_time} on {tee_time.search_date}")

        # Commit all changes
        session.commit()

        logging.info(f"Successfully processed {total_processed} tee time slots across {len(all_tee_times)} dates")
        logging.info(f"Saved {saved_count} new tee times and updated {updated_count} existing tee times")
        logging.info(f"Marked {marked_unavailable} tee times as no longer available")

        # Store counts in XCom
        context['task_instance'].xcom_push(key='saved_count', value=saved_count)
        context['task_instance'].xcom_push(key='updated_count', value=updated_count)
        context['task_instance'].xcom_push(key='total_processed', value=total_processed)
        context['task_instance'].xcom_push(key='marked_unavailable', value=marked_unavailable)
        context['task_instance'].xcom_push(key='current_tee_time_ids', value=current_tee_time_ids)

        return {'saved': saved_count, 'updated': updated_count, 'total_processed': total_processed, 'marked_unavailable': marked_unavailable}

    except Exception as e:
        session.rollback()
        logging.error(f"Failed to save tee times to database: {e}")
        raise
    finally:
        session.close()

def cleanup_old_tee_times(**context):
    """Delete tee times from yesterday and older"""
    # Create database connection
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Delete tee times from before today
        # This includes both:
        # 1. Tee times with tee_off_datetime before today
        # 2. Tee times with NULL tee_off_datetime (we'll use a separate query for these)
        deleted_count = session.query(TeeTime).filter(
            TeeTime.tee_off_datetime < today_start
        ).delete()

        # Also delete tee times with NULL datetime that are from past dates based on search_date
        # Parse search_date and check if it's in the past
        null_datetime_records = session.query(TeeTime).filter(
            TeeTime.tee_off_datetime.is_(None)
        ).all()

        null_deleted = 0
        for record in null_datetime_records:
            try:
                # Try to parse the search_date to check if it's old
                search_date_obj = datetime.strptime(record.search_date, "%a %b %d %Y")
                if search_date_obj < today_start:
                    session.delete(record)
                    null_deleted += 1
            except Exception as e:
                logging.warning(f"Could not parse search_date '{record.search_date}' for record {record.id}: {e}")

        session.commit()

        total_deleted = deleted_count + null_deleted
        logging.info(f"Deleted {deleted_count} tee times with datetime before today")
        logging.info(f"Deleted {null_deleted} tee times with NULL datetime from past dates")
        logging.info(f"Total deleted: {total_deleted} old tee times")

        # Store count in XCom
        context['task_instance'].xcom_push(key='deleted_count', value=total_deleted)

        return {'deleted': total_deleted}

    except Exception as e:
        session.rollback()
        logging.error(f"Failed to cleanup old tee times: {e}")
        raise
    finally:
        session.close()

# Create DAG
dag = DAG(
    'bergen_county_golf_tee_times',
    default_args=default_args,
    description='Check Bergen County Golf Course tee times',
    schedule_interval=timedelta(minutes=5),  # Run every 5 minutes
    start_date=days_ago(1),
    catchup=False,
    tags=['golf', 'booking'],
)

# Define tasks
start_task = DummyOperator(
    task_id='start',
    dag=dag,
)

check_token_task = BranchPythonOperator(
    task_id='check_token',
    python_callable=check_token_validity,
    dag=dag,
)

authenticate_task_node = PythonOperator(
    task_id='authenticate',
    python_callable=authenticate_task,
    dag=dag,
)

fetch_tee_times_task_node = PythonOperator(
    task_id='fetch_tee_times',
    python_callable=fetch_tee_times_task,
    dag=dag,
    trigger_rule='none_failed_or_skipped',
)

process_tee_times_task_node = PythonOperator(
    task_id='process_tee_times',
    python_callable=process_tee_times_task,
    dag=dag,
)

dump_json_task = PythonOperator(
    task_id='dump_tee_times_json',
    python_callable=dump_tee_times_to_json,
    dag=dag,
)

save_to_db_task = PythonOperator(
    task_id='save_to_database',
    python_callable=save_tee_times_to_database,
    dag=dag,
)

cleanup_task = PythonOperator(
    task_id='cleanup_old_tee_times',
    python_callable=cleanup_old_tee_times,
    dag=dag,
)

end_task = DummyOperator(
    task_id='end',
    dag=dag,
    trigger_rule='none_failed_or_skipped',
)

# Define task dependencies
start_task >> check_token_task
check_token_task >> [authenticate_task_node, fetch_tee_times_task_node]
authenticate_task_node >> fetch_tee_times_task_node
fetch_tee_times_task_node >> [process_tee_times_task_node, dump_json_task, save_to_db_task]
save_to_db_task >> cleanup_task
[process_tee_times_task_node, dump_json_task, cleanup_task] >> end_task
