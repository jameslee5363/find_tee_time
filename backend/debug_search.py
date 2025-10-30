#!/usr/bin/env python3
"""
Debug script to test tee time matching logic.
This helps troubleshoot why a specific search isn't finding matches.
"""
import sys
from pathlib import Path
from datetime import time

# Add src directory to path
backend_src = Path(__file__).parent / "src"
sys.path.insert(0, str(backend_src))

from services.tee_time_matcher import TeeTimeMatcherService, TeeTime
from database.models import TeeTimeSearch

# Create a mock tee time for testing
def create_test_tee_time(course_name, tee_off_time, search_date="Fri Oct 31 2025"):
    """Create a test tee time object"""
    return TeeTime(
        id=1,
        tee_time_id="test_123",
        search_date=search_date,
        tee_off_time=tee_off_time,
        course_name=course_name,
        available_spots=4,
        max_players=4,
        is_available=True,
        is_online_bookable=True
    )

# Create a mock search request
def create_test_search(course_names, preferred_dates, time_start=None, time_end=None, group_size=1):
    """Create a test search object"""
    import json

    search = TeeTimeSearch()
    search.id = 1
    search.user_id = 1
    search.course_name = json.dumps(course_names)
    search.preferred_dates = json.dumps(preferred_dates)
    search.preferred_time_start = time_start
    search.preferred_time_end = time_end
    search.group_size = group_size
    search.status = "pending"

    return search

def main():
    print("=" * 80)
    print("TEE TIME MATCHER DEBUG SCRIPT")
    print("=" * 80)

    matcher = TeeTimeMatcherService()

    # Test Case: Your specific search
    print("\n### TEST CASE: Rockleigh Blue 9 at 8:00-8:30 AM on Oct 31")
    print("-" * 80)

    # Create test search (your criteria)
    search = create_test_search(
        course_names=["Rockleigh Blue 9"],
        preferred_dates=["2025-10-31"],
        time_start="08:00",
        time_end="08:30",
        group_size=1
    )

    print(f"Search criteria:")
    print(f"  Course: Rockleigh Blue 9")
    print(f"  Date: 2025-10-31 (Oct 31, 2025)")
    print(f"  Time: 08:00 to 08:30")
    print(f"  Group size: 1")
    print()

    # Test different tee times
    test_cases = [
        ("Rockleigh Blue 9", "07:30", "Should NOT match (before 8:00)"),
        ("Rockleigh Blue 9", "08:00", "Should MATCH (exactly at start)"),
        ("Rockleigh Blue 9", "08:15", "Should MATCH (within range)"),
        ("Rockleigh Blue 9", "08:30", "Should MATCH (exactly at end - INCLUSIVE)"),
        ("Rockleigh Blue 9", "08:31", "Should NOT match (after 8:30)"),
        ("Rockleigh Blue 9", "09:00", "Should NOT match (after 8:30)"),
        ("Valley Brook 9", "08:15", "Should NOT match (wrong course)"),
    ]

    for course, tee_time, expected in test_cases:
        tee_time_obj = create_test_tee_time(course, tee_time)
        matches = matcher.matches_search_criteria(tee_time_obj, search)

        status = "✓ PASS" if (("Should MATCH" in expected and matches) or ("Should NOT match" in expected and not matches)) else "✗ FAIL"
        match_str = "MATCHES" if matches else "NO MATCH"

        print(f"{status} | {course:20s} | {tee_time} | {match_str:10s} | {expected}")

    print()
    print("=" * 80)

    # Test date parsing
    print("\n### DATE PARSING TESTS")
    print("-" * 80)

    date_tests = [
        "2025-10-31",
        "Fri Oct 31 2025",
        "2025-10-31",
    ]

    for date_str in date_tests:
        parsed = matcher.parse_date(date_str)
        print(f"  '{date_str}' -> {parsed}")

    # Test time parsing
    print("\n### TIME PARSING TESTS")
    print("-" * 80)

    time_tests = [
        "08:00",
        "08:30",
        "8:00",  # single digit hour
        "08:00:00",  # with seconds
        "2025-10-31T08:00:00",  # ISO format
    ]

    for time_str in time_tests:
        parsed = matcher.parse_time(time_str)
        print(f"  '{time_str}' -> {parsed}")

    print()
    print("=" * 80)
    print("DEBUG COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
