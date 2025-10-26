from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from kafka import KafkaProducer
import os

app = FastAPI(title="My API")

# Configure CORS - Allow requests from frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
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