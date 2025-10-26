#!/usr/bin/env python3
"""
Tee Time Matcher Consumer
Processes tee time bookings from Kafka and matches compatible bookings
"""

import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import threading
import time

# Configure logging with colors for better visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


@dataclass
class TeeTimeBooking:
    """Represents a tee time booking"""
    request_id: str
    timestamp: datetime
    course_id: str
    course_name: str
    tee_time: datetime
    players: List[Dict]
    num_players: int
    num_holes: int
    booking_type: str
    payment_status: str
    total_price: float
    priority: str
    special_requests: Optional[str] = None
    weather_preference: str = "ANY"
    cart_required: bool = False
    equipment_rental: bool = False
    
    @property
    def has_availability(self) -> bool:
        """Check if booking can accept more players"""
        return self.num_players < 4
    
    @property
    def available_slots(self) -> int:
        """Number of available slots in this booking"""
        return 4 - self.num_players
    
    def is_compatible_time(self, other: 'TeeTimeBooking', window_minutes: int = 30) -> bool:
        """Check if two bookings have compatible tee times"""
        if self.course_id != other.course_id:
            return False
        time_diff = abs((self.tee_time - other.tee_time).total_seconds() / 60)
        return time_diff <= window_minutes
    
    def can_merge_with(self, other: 'TeeTimeBooking') -> bool:
        """Check if this booking can be merged with another"""
        if self.course_id != other.course_id:
            return False
        if self.tee_time != other.tee_time:
            return False
        if self.num_players + other.num_players > 4:
            return False
        if self.num_holes != other.num_holes:
            return False
        return True


@dataclass
class MatchResult:
    """Represents a matching result between bookings"""
    match_type: str  # MERGED, SEQUENTIAL, SIMILAR_TIME, WAITLIST
    primary_booking: TeeTimeBooking
    matched_bookings: List[TeeTimeBooking]
    match_score: float
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)


class TeeTimeMatcherConsumer:
    def __init__(self, bootstrap_servers='localhost:9092', topic='tee-times', 
                 group_id='tee-time-matcher-group'):
        """Initialize the Tee Time Matcher Consumer"""
        self.topic = topic
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset='latest',  # Only process new messages
            enable_auto_commit=True,
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            key_deserializer=lambda k: k.decode('utf-8') if k else None
        )
        
        # Data structures for matching
        self.pending_bookings: Dict[str, List[TeeTimeBooking]] = defaultdict(list)  # By course
        self.matched_groups: List[MatchResult] = []
        self.waitlist: Dict[str, deque] = defaultdict(lambda: deque(maxlen=50))  # By course
        self.processed_count = 0
        self.match_count = 0
        
        # Matching configuration
        self.matching_window_minutes = 30
        self.max_wait_time_minutes = 60
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'successful_merges': 0,
            'sequential_matches': 0,
            'waitlisted': 0,
            'expired': 0,
            'by_course': defaultdict(int),
            'by_hour': defaultdict(int),
            'avg_group_size': 0
        }
        
        # Start background thread for periodic matching
        self.matching_thread = threading.Thread(target=self._periodic_matching, daemon=True)
        self.running = True
        self.matching_thread.start()
        
        logger.info(f"Matcher Consumer initialized for topic: {topic}")
    
    def _parse_booking(self, message: Dict) -> TeeTimeBooking:
        """Parse message into TeeTimeBooking object"""
        return TeeTimeBooking(
            request_id=message['request_id'],
            timestamp=datetime.fromisoformat(message['timestamp']),
            course_id=message['course']['id'],
            course_name=message['course']['name'],
            tee_time=datetime.fromisoformat(message['tee_time']),
            players=message['players'],
            num_players=message['num_players'],
            num_holes=message['num_holes'],
            booking_type=message['booking_type'],
            payment_status=message['pricing']['payment_status'],
            total_price=message['pricing']['total_price'],
            priority=message['priority'],
            special_requests=message.get('special_requests'),
            weather_preference=message.get('weather_preference', 'ANY'),
            cart_required=message.get('cart_required', False),
            equipment_rental=message.get('equipment_rental', False)
        )
    
    def _calculate_match_score(self, booking1: TeeTimeBooking, 
                              booking2: TeeTimeBooking) -> float:
        """Calculate compatibility score between two bookings"""
        score = 0.0
        
        # Same course (required)
        if booking1.course_id != booking2.course_id:
            return 0.0
        
        # Time proximity (max 30 points)
        time_diff = abs((booking1.tee_time - booking2.tee_time).total_seconds() / 60)
        if time_diff == 0:
            score += 30
        elif time_diff <= 10:
            score += 20
        elif time_diff <= 30:
            score += 10
        
        # Same number of holes (20 points)
        if booking1.num_holes == booking2.num_holes:
            score += 20
        
        # Compatible group size (20 points)
        if booking1.num_players + booking2.num_players <= 4:
            score += 20
        
        # Same booking type (10 points)
        if booking1.booking_type == booking2.booking_type:
            score += 10
        
        # Similar preferences (10 points each)
        if booking1.cart_required == booking2.cart_required:
            score += 5
        if booking1.equipment_rental == booking2.equipment_rental:
            score += 5
        if booking1.weather_preference == booking2.weather_preference:
            score += 5
        
        # Priority boost
        if booking1.priority == 'HIGH' or booking2.priority == 'HIGH':
            score += 5
        
        return score
    
    def _find_matches(self, booking: TeeTimeBooking) -> List[MatchResult]:
        """Find potential matches for a booking"""
        matches = []
        course_bookings = self.pending_bookings[booking.course_id]
        
        for other in course_bookings:
            if other.request_id == booking.request_id:
                continue
            
            # Check for exact time match (can merge)
            if booking.can_merge_with(other):
                match = MatchResult(
                    match_type="MERGED",
                    primary_booking=booking,
                    matched_bookings=[other],
                    match_score=100.0,
                    reason=f"Perfect match - same time, combined {booking.num_players + other.num_players} players"
                )
                matches.append(match)
            
            # Check for sequential times
            elif booking.is_compatible_time(other, window_minutes=10):
                score = self._calculate_match_score(booking, other)
                if score >= 40:  # Minimum score threshold
                    time_diff = int((other.tee_time - booking.tee_time).total_seconds() / 60)
                    match = MatchResult(
                        match_type="SEQUENTIAL",
                        primary_booking=booking,
                        matched_bookings=[other],
                        match_score=score,
                        reason=f"Sequential booking - {abs(time_diff)} minutes apart"
                    )
                    matches.append(match)
        
        # Sort by score
        matches.sort(key=lambda x: x.match_score, reverse=True)
        return matches
    
    def _try_create_foursome(self, course_id: str) -> Optional[MatchResult]:
        """Try to create a complete foursome from pending bookings"""
        course_bookings = self.pending_bookings[course_id]
        
        # Group by tee time
        time_groups = defaultdict(list)
        for booking in course_bookings:
            time_key = booking.tee_time.strftime('%Y-%m-%d %H:%M')
            time_groups[time_key].append(booking)
        
        # Try to form foursomes
        for time_key, bookings in time_groups.items():
            if len(bookings) < 2:
                continue
            
            # Try different combinations
            for i, primary in enumerate(bookings):
                compatible = []
                total_players = primary.num_players
                
                for j, other in enumerate(bookings):
                    if i != j and total_players + other.num_players <= 4:
                        compatible.append(other)
                        total_players += other.num_players
                        
                        if total_players == 4:
                            # Perfect foursome!
                            return MatchResult(
                                match_type="MERGED",
                                primary_booking=primary,
                                matched_bookings=compatible,
                                match_score=100.0,
                                reason=f"Created perfect foursome with {len(compatible) + 1} bookings"
                            )
        
        return None
    
    def _periodic_matching(self):
        """Background thread that periodically tries to match bookings"""
        while self.running:
            time.sleep(10)  # Run every 10 seconds
            
            for course_id in list(self.pending_bookings.keys()):
                # Try to create foursomes
                foursome = self._try_create_foursome(course_id)
                if foursome:
                    self._process_match(foursome)
                
                # Clean up old bookings
                self._cleanup_expired_bookings(course_id)
    
    def _cleanup_expired_bookings(self, course_id: str):
        """Remove bookings that are too old or past their tee time"""
        current_time = datetime.now()
        expired = []
        
        for booking in self.pending_bookings[course_id]:
            # Remove if tee time has passed
            if booking.tee_time < current_time:
                expired.append(booking)
            # Or if booking is too old (waiting too long)
            elif (current_time - booking.timestamp).total_seconds() / 60 > self.max_wait_time_minutes:
                expired.append(booking)
                self.waitlist[course_id].append(booking)
                self.stats['waitlisted'] += 1
        
        for booking in expired:
            self.pending_bookings[course_id].remove(booking)
            self.stats['expired'] += 1
    
    def _process_match(self, match: MatchResult):
        """Process a successful match"""
        self.matched_groups.append(match)
        self.match_count += 1
        
        # Update statistics
        if match.match_type == "MERGED":
            self.stats['successful_merges'] += 1
        elif match.match_type == "SEQUENTIAL":
            self.stats['sequential_matches'] += 1
        
        # Remove matched bookings from pending
        course_id = match.primary_booking.course_id
        
        # Remove primary booking
        if match.primary_booking in self.pending_bookings[course_id]:
            self.pending_bookings[course_id].remove(match.primary_booking)
        
        # Remove matched bookings
        for booking in match.matched_bookings:
            if booking in self.pending_bookings[course_id]:
                self.pending_bookings[course_id].remove(booking)
        
        self._display_match(match)
    
    def _display_match(self, match: MatchResult):
        """Display a match result with formatting"""
        print(f"\n{Colors.OKGREEN}{'='*80}{Colors.ENDC}")
        print(f"{Colors.BOLD}⛳ MATCH FOUND! - {match.match_type}{Colors.ENDC}")
        print(f"{'='*80}")
        print(f"Match Score: {Colors.OKCYAN}{match.match_score:.1f}/100{Colors.ENDC}")
        print(f"Reason: {match.reason}")
        print(f"Timestamp: {match.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Primary booking
        print(f"\n{Colors.BOLD}Primary Booking:{Colors.ENDC}")
        self._print_booking_summary(match.primary_booking, prefix="  → ")
        
        # Matched bookings
        if match.matched_bookings:
            print(f"\n{Colors.BOLD}Matched With:{Colors.ENDC}")
            for booking in match.matched_bookings:
                self._print_booking_summary(booking, prefix="  → ")
        
        # Combined summary
        total_players = match.primary_booking.num_players
        all_players = list(match.primary_booking.players)
        
        for booking in match.matched_bookings:
            total_players += booking.num_players
            all_players.extend(booking.players)
        
        print(f"\n{Colors.BOLD}Combined Group Summary:{Colors.ENDC}")
        print(f"  Total Players: {Colors.OKGREEN}{total_players}/4{Colors.ENDC}")
        print(f"  Course: {match.primary_booking.course_name}")
        print(f"  Tee Time: {match.primary_booking.tee_time.strftime('%B %d at %I:%M %p')}")
        print(f"  Players:")
        for i, player in enumerate(all_players, 1):
            print(f"    {i}. {player['name']} (Handicap: {player['handicap']})")
        
        if total_players == 4:
            print(f"\n  {Colors.OKGREEN}✓ FOURSOME COMPLETE!{Colors.ENDC}")
        else:
            print(f"\n  {Colors.WARNING}⚠ {4 - total_players} slots still available{Colors.ENDC}")
        
        print(f"{Colors.OKGREEN}{'='*80}{Colors.ENDC}\n")
    
    def _print_booking_summary(self, booking: TeeTimeBooking, prefix: str = ""):
        """Print a summary of a booking"""
        print(f"{prefix}ID: {booking.request_id}")
        print(f"{prefix}Players: {booking.num_players} - {', '.join([p['name'] for p in booking.players])}")
        print(f"{prefix}Time: {booking.tee_time.strftime('%I:%M %p')}, {booking.num_holes} holes")
        print(f"{prefix}Type: {booking.booking_type}, Priority: {booking.priority}")
    
    def _display_stats(self):
        """Display current statistics"""
        print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
        print(f"{Colors.BOLD}📊 MATCHING STATISTICS{Colors.ENDC}")
        print(f"{'='*80}")
        print(f"Total Processed: {self.stats['total_processed']}")
        print(f"Successful Merges: {Colors.OKGREEN}{self.stats['successful_merges']}{Colors.ENDC}")
        print(f"Sequential Matches: {Colors.OKCYAN}{self.stats['sequential_matches']}{Colors.ENDC}")
        print(f"Waitlisted: {Colors.WARNING}{self.stats['waitlisted']}{Colors.ENDC}")
        print(f"Expired: {Colors.FAIL}{self.stats['expired']}{Colors.ENDC}")
        
        print(f"\n{Colors.BOLD}Pending Bookings by Course:{Colors.ENDC}")
        for course_id, bookings in self.pending_bookings.items():
            if bookings:
                print(f"  {course_id}: {len(bookings)} bookings pending")
        
        print(f"\n{Colors.BOLD}Bookings by Course:{Colors.ENDC}")
        for course_id, count in sorted(self.stats['by_course'].items(), 
                                      key=lambda x: x[1], reverse=True)[:5]:
            print(f"  {course_id}: {count}")
        
        print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}\n")
    
    def consume_and_match(self):
        """Main consumption and matching loop"""
        logger.info(f"Starting Tee Time Matcher - Topic: {self.topic}")
        logger.info("Processing bookings and finding matches...")
        logger.info("Press Ctrl+C to stop\n")
        
        try:
            for message in self.consumer:
                try:
                    # Parse booking
                    booking = self._parse_booking(message.value)
                    self.processed_count += 1
                    self.stats['total_processed'] += 1
                    self.stats['by_course'][booking.course_id] += 1
                    
                    hour = booking.tee_time.hour
                    self.stats['by_hour'][hour] += 1
                    
                    # Display new booking
                    print(f"\n{Colors.OKBLUE}📥 New Booking Received:{Colors.ENDC}")
                    print(f"  Request: {booking.request_id}")
                    print(f"  Course: {booking.course_name}")
                    print(f"  Time: {booking.tee_time.strftime('%B %d at %I:%M %p')}")
                    print(f"  Players: {booking.num_players} ({', '.join([p['name'] for p in booking.players[:2]])}{'...' if booking.num_players > 2 else ''})")
                    
                    # Try to find immediate matches
                    matches = self._find_matches(booking)
                    
                    if matches:
                        # Process best match
                        best_match = matches[0]
                        self._process_match(best_match)
                    else:
                        # Add to pending
                        self.pending_bookings[booking.course_id].append(booking)
                        print(f"  {Colors.WARNING}→ Added to pending (Course: {booking.course_id}, "
                              f"Pending: {len(self.pending_bookings[booking.course_id])}){Colors.ENDC}")
                    
                    # Display stats every 10 bookings
                    if self.processed_count % 10 == 0:
                        self._display_stats()
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except KeyboardInterrupt:
            logger.info("\nShutting down matcher...")
        finally:
            self.running = False
            self.close()
            self._display_stats()
            logger.info(f"Final: Processed {self.processed_count} bookings, "
                       f"created {self.match_count} matches")
    
    def close(self):
        """Close the consumer and clean up"""
        self.running = False
        self.consumer.close()
        logger.info("Matcher consumer closed")


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tee Time Matcher Consumer')
    parser.add_argument(
        '--bootstrap-servers',
        default='localhost:9092',
        help='Kafka bootstrap servers (default: localhost:9092)'
    )
    parser.add_argument(
        '--topic',
        default='tee-times',
        help='Kafka topic name (default: tee-times)'
    )
    parser.add_argument(
        '--group-id',
        default='tee-time-matcher-group',
        help='Consumer group ID (default: tee-time-matcher-group)'
    )
    parser.add_argument(
        '--matching-window',
        type=int,
        default=30,
        help='Time window in minutes for matching bookings (default: 30)'
    )
    
    args = parser.parse_args()
    
    # Create and start matcher
    matcher = TeeTimeMatcherConsumer(
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic,
        group_id=args.group_id
    )
    
    matcher.matching_window_minutes = args.matching_window
    matcher.consume_and_match()


if __name__ == "__main__":
    main()