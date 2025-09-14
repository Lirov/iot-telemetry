from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import os
from .models import TelemetryIn
from .producer import publish_telemetry
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response

app = FastAPI(title="ingestion-api")
client = AsyncIOMotorClient(os.getenv("MONGO_URI", "mongodb://mongo:27017"))
db = client[os.getenv("MONGO_DB", "iotdb")]
RAW_COLLECTION = os.getenv("RAW_COLLECTION", "telemetry_raw")

# Prometheus metrics
telemetry_ingested_total = Counter('telemetry_ingested_total', 'Total number of telemetry records ingested', ['device_id'])
telemetry_ingest_duration = Histogram('telemetry_ingest_duration_seconds', 'Time spent processing telemetry ingestion')
kafka_publish_errors = Counter('kafka_publish_errors_total', 'Total number of Kafka publish errors')
mongo_write_errors = Counter('mongo_write_errors_total', 'Total number of MongoDB write errors')

@app.post("/ingest")
async def ingest(t: TelemetryIn):
    with telemetry_ingest_duration.time():
        try:
            doc = t.model_dump()
            doc["ts"] = (t.ts or datetime.now(timezone.utc)).isoformat()
            
            # Publish to Kafka first (before MongoDB adds _id)
            try:
                publish_telemetry(doc)
            except Exception as e:
                kafka_publish_errors.inc()
                raise e
            
            # Then store in MongoDB (this will add _id)
            try:
                await db[RAW_COLLECTION].insert_one(doc)
            except Exception as e:
                mongo_write_errors.inc()
                raise e
            
            # Increment success counter
            telemetry_ingested_total.labels(device_id=t.device_id).inc()
            
            return {"status": "queued", "device_id": t.device_id}
        except Exception as e:
            # Re-raise the exception to maintain error handling
            raise e

@app.get("/health")
async def health():
    # lightweight health that also pings Mongo
    await db.command("ping")
    return {"ok": True}

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
