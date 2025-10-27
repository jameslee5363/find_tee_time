#!/usr/bin/env python3
"""Consume tee-time search events and trigger notifications."""
import json
import logging
import os
import sys
import time
from pathlib import Path

from kafka import KafkaConsumer
from kafka.errors import KafkaError

# Add backend src to path
backend_src = Path(__file__).parent.parent.parent / 'src'
sys.path.insert(0, str(backend_src))

from services.tee_time_matcher import tee_time_matcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:29092')
KAFKA_TOPIC = 'tee-time-searches'
CONSUMER_GROUP = 'tee-time-notifier-group'


def process_search_message(message):
    """Handle one Kafka message containing a tee time search."""
    try:
        # Parse message value
        search_data = json.loads(message.value.decode('utf-8'))

        logger.info(f"Received search request: {search_data}")

        # Extract search ID
        search_id = search_data.get('search_id')
        if not search_id:
            logger.error("No search_id in message")
            return

        user_id = search_data.get('user_id')
        course_name = search_data.get('course_name')
        logger.info(
            f"Processing search ID {search_id} for user {user_id} "
            f"looking for {course_name}"
        )

        # Process matches for this specific search
        stats = tee_time_matcher.process_search_matches(search_id=search_id)

        logger.info(
            f"Processed search {search_id}: "
            f"{stats['matches_found']} matches found, "
            f"{stats['notifications_sent']} notifications sent"
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode message as JSON: {e}")
    except Exception as e:
        logger.error(f"Error processing search message: {e}", exc_info=True)


def run_consumer():
    """Start the Kafka consumer loop."""
    logger.info(f"Starting Tee Time Notifier Consumer")
    logger.info(f"Kafka Bootstrap Servers: {KAFKA_BOOTSTRAP_SERVERS}")
    logger.info(f"Topic: {KAFKA_TOPIC}")
    logger.info(f"Consumer Group: {CONSUMER_GROUP}")

    # Create consumer with retry logic
    max_retries = 5
    retry_delay = 5  # seconds

    for attempt in range(max_retries):
        try:
            consumer = KafkaConsumer(
                KAFKA_TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                group_id=CONSUMER_GROUP,
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                value_deserializer=lambda x: x,  # We'll decode manually
                request_timeout_ms=30000,
                session_timeout_ms=10000,
                heartbeat_interval_ms=3000
            )

            logger.info("Successfully connected to Kafka")
            break

        except KafkaError as e:
            logger.error(f"Failed to connect to Kafka (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("Max retries reached. Exiting.")
                sys.exit(1)

    # Main consumer loop
    logger.info("Waiting for messages...")

    try:
        for message in consumer:
            logger.info(
                f"Received message: topic={message.topic}, "
                f"partition={message.partition}, offset={message.offset}"
            )

            process_search_message(message)

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Consumer error: {e}", exc_info=True)
    finally:
        logger.info("Closing consumer")
        consumer.close()


def run_periodic_matcher():
    """Periodically scan all searches for new matches."""
    logger.info("Starting Periodic Tee Time Matcher")

    check_interval = int(os.getenv('MATCHER_CHECK_INTERVAL', '300'))  # 5 minutes default
    logger.info(f"Check interval: {check_interval} seconds")

    try:
        while True:
            try:
                logger.info("Running periodic match check for all active searches...")

                stats = tee_time_matcher.process_search_matches()

                logger.info(
                    f"Periodic check complete: "
                    f"Processed {stats['searches_processed']} searches, "
                    f"Found {stats['matches_found']} matches, "
                    f"Sent {stats['notifications_sent']} notifications"
                )

            except Exception as e:
                logger.error(f"Error in periodic matcher: {e}", exc_info=True)

            # Wait for next check
            time.sleep(check_interval)

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")


if __name__ == '__main__':
    # Check which mode to run in
    mode = os.getenv('NOTIFIER_MODE', 'consumer')  # 'consumer', 'periodic', or 'both'

    if mode == 'consumer':
        run_consumer()
    elif mode == 'periodic':
        run_periodic_matcher()
    elif mode == 'both':
        # Run both modes in parallel
        import threading

        consumer_thread = threading.Thread(target=run_consumer, daemon=True)
        periodic_thread = threading.Thread(target=run_periodic_matcher, daemon=True)

        consumer_thread.start()
        periodic_thread.start()

        logger.info("Running both consumer and periodic matcher")

        try:
            # Keep main thread alive
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
    else:
        logger.error(f"Unknown NOTIFIER_MODE: {mode}")
        sys.exit(1)
