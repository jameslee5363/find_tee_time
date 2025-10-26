#!/usr/bin/env python3
"""
Tee Time Kafka Producer
Generates and sends fake golf tee time booking requests to Kafka
"""

import json
import random
import time
from datetime import datetime, timedelta
from kafka import KafkaProducer
from kafka.errors import KafkaError
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TeeTimeProducer:
    def __init__(self, bootstrap_servers='localhost:9092', topic='tee-times'):
        """Initialize Kafka producer for tee time bookings"""
        self.topic = topic
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',  # Wait for all replicas to acknowledge
            retries=3,
            max_in_flight_requests_per_connection=1
        )
        
        # Sample data for generating fake requests
        self.golf_courses = [
            {"id": "GC001", "name": "Pebble Beach Golf Links", "city": "Pebble Beach", "state": "CA"},
            {"id": "GC002", "name": "Augusta National", "city": "Augusta", "state": "GA"},
            {"id": "GC003", "name": "St. Andrews Links", "city": "St. Andrews", "state": "Scotland"},
            {"id": "GC004", "name": "Pine Valley Golf Club", "city": "Pine Valley", "state": "NJ"},
            {"id": "GC005", "name": "Cypress Point Club", "city": "Pebble Beach", "state": "CA"},
            {"id": "GC006", "name": "Shinnecock Hills", "city": "Southampton", "state": "NY"},
            {"id": "GC007", "name": "Royal County Down", "city": "Newcastle", "state": "Northern Ireland"},
            {"id": "GC008", "name": "Merion Golf Club", "city": "Ardmore", "state": "PA"}
        ]
        
        self.player_names = [
            "John Smith", "Emma Johnson", "Michael Brown", "Sarah Davis",
            "Robert Wilson", "Lisa Anderson", "David Martinez", "Jennifer Taylor",
            "James Miller", "Maria Garcia", "William Jones", "Patricia Rodriguez",
            "Richard Lee", "Linda White", "Charles Harris", "Barbara Martin"
        ]
        
        self.booking_types = ["REGULAR", "MEMBER", "GUEST", "TOURNAMENT", "CORPORATE"]
        self.payment_methods = ["CREDIT_CARD", "DEBIT_CARD", "CASH", "MEMBER_ACCOUNT", "CORPORATE_ACCOUNT"]
        
    def generate_tee_time_request(self):
        """Generate a fake tee time booking request"""
        course = random.choice(self.golf_courses)
        
        # Generate random tee time (7 AM to 5 PM, in 10-minute intervals)
        base_date = datetime.now() + timedelta(days=random.randint(1, 30))
        hour = random.randint(7, 16)
        minute = random.choice([0, 10, 20, 30, 40, 50])
        tee_time = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # Generate player group (1-4 players)
        num_players = random.randint(1, 4)
        players = random.sample(self.player_names, num_players)
        
        # Calculate pricing
        base_price = random.uniform(50, 250)
        total_price = base_price * num_players
        
        request = {
            "request_id": f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{random.randint(1000, 9999)}",
            "timestamp": datetime.now().isoformat(),
            "course": course,
            "tee_time": tee_time.isoformat(),
            "booking_type": random.choice(self.booking_types),
            "players": [
                {
                    "name": player,
                    "email": f"{player.lower().replace(' ', '.')}@email.com",
                    "handicap": random.randint(0, 36),
                    "member_id": f"MEM-{random.randint(1000, 9999)}" if random.random() > 0.5 else None
                }
                for player in players
            ],
            "num_players": num_players,
            "num_holes": random.choice([9, 18]),
            "cart_required": random.choice([True, False]),
            "num_carts": random.randint(1, (num_players + 1) // 2) if num_players > 1 else 1,
            "equipment_rental": random.choice([True, False]),
            "pricing": {
                "base_price": round(base_price, 2),
                "total_price": round(total_price, 2),
                "currency": "USD",
                "payment_method": random.choice(self.payment_methods),
                "payment_status": random.choice(["PENDING", "COMPLETED", "PROCESSING"])
            },
            "special_requests": random.choice([
                None,
                "Early morning preferred",
                "Need left-handed clubs",
                "Wheelchair accessible cart needed",
                "Birthday celebration",
                "Corporate event"
            ]),
            "weather_preference": random.choice(["ANY", "SUNNY_ONLY", "NO_RAIN"]),
            "status": "PENDING",
            "priority": random.choice(["LOW", "NORMAL", "HIGH"])
        }
        
        return request
    
    def send_message(self, message, key=None):
        """Send a message to Kafka topic"""
        try:
            future = self.producer.send(
                self.topic,
                key=key,
                value=message
            )
            
            # Wait for message to be sent (synchronous for demo purposes)
            record_metadata = future.get(timeout=10)
            
            logger.info(
                f"Message sent successfully - Topic: {record_metadata.topic}, "
                f"Partition: {record_metadata.partition}, "
                f"Offset: {record_metadata.offset}"
            )
            return True
            
        except KafkaError as e:
            logger.error(f"Failed to send message: {e}")
            return False
    
    def start_producing(self, num_messages=None, interval_seconds=2):
        """Start producing tee time requests"""
        logger.info(f"Starting Tee Time Producer - Topic: {self.topic}")
        logger.info(f"Interval: {interval_seconds} seconds")
        
        if num_messages:
            logger.info(f"Will send {num_messages} messages")
        else:
            logger.info("Will run continuously (Ctrl+C to stop)")
        
        message_count = 0
        
        try:
            while True:
                # Generate and send tee time request
                tee_time_request = self.generate_tee_time_request()
                
                # Use course ID as the key for partitioning
                key = tee_time_request['course']['id']
                
                # Send to Kafka
                success = self.send_message(tee_time_request, key)
                
                if success:
                    message_count += 1
                    logger.info(
                        f"Sent tee time request #{message_count}: "
                        f"{tee_time_request['request_id']} - "
                        f"Course: {tee_time_request['course']['name']}, "
                        f"Time: {tee_time_request['tee_time']}, "
                        f"Players: {tee_time_request['num_players']}"
                    )
                
                # Check if we've sent enough messages
                if num_messages and message_count >= num_messages:
                    break
                
                # Wait before sending next message
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logger.info("\nShutting down producer...")
        finally:
            self.close()
            logger.info(f"Total messages sent: {message_count}")
    
    def close(self):
        """Close the Kafka producer"""
        self.producer.flush()
        self.producer.close()
        logger.info("Producer closed")


def main():
    """Main function to run the producer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Tee Time Kafka Producer')
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
        '--num-messages',
        type=int,
        default=None,
        help='Number of messages to send (default: unlimited)'
    )
    parser.add_argument(
        '--interval',
        type=float,
        default=2.0,
        help='Interval between messages in seconds (default: 2.0)'
    )
    parser.add_argument(
        '--create-topic',
        action='store_true',
        help='Create topic if it doesn\'t exist'
    )
    
    args = parser.parse_args()
    
    # Optional: Create topic first
    if args.create_topic:
        from kafka.admin import KafkaAdminClient, NewTopic
        
        admin_client = KafkaAdminClient(
            bootstrap_servers=args.bootstrap_servers,
            client_id='tee-time-admin'
        )
        
        topic = NewTopic(
            name=args.topic,
            num_partitions=3,
            replication_factor=1
        )
        
        try:
            admin_client.create_topics(new_topics=[topic], validate_only=False)
            logger.info(f"Topic '{args.topic}' created successfully")
        except Exception as e:
            logger.warning(f"Topic creation failed (may already exist): {e}")
        
        admin_client.close()
    
    # Create and start producer
    producer = TeeTimeProducer(
        bootstrap_servers=args.bootstrap_servers,
        topic=args.topic
    )
    
    producer.start_producing(
        num_messages=args.num_messages,
        interval_seconds=args.interval
    )


if __name__ == "__main__":
    main()