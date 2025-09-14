from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone
import os
from .models import TelemetryIn
from .producer import publish_telemetry

app = FastAPI(title="ingestion-api")
client = AsyncIOMotorClient(os.getenv("MONGO_URI", "mongodb://mongo:27017"))
db = client[os.getenv("MONGO_DB", "iotdb")]
RAW_COLLECTION = os.getenv("RAW_COLLECTION", "telemetry_raw")

@app.post("/ingest")
async def ingest(t: TelemetryIn):
    doc = t.model_dump()
    doc["ts"] = (t.ts or datetime.now(timezone.utc)).isoformat()
    
    # Publish to Kafka first (before MongoDB adds _id)
    publish_telemetry(doc)
    
    # Then store in MongoDB (this will add _id)
    await db[RAW_COLLECTION].insert_one(doc)
    
    return {"status": "queued", "device_id": t.device_id}

@app.get("/health")
async def health():
    # lightweight health that also pings Mongo
    await db.command("ping")
    return {"ok": True}
