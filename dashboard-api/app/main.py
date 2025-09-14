from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient
import os
from typing import List, Dict, Any

app = FastAPI(title="IoT Telemetry Dashboard API", version="1.0.0")

# MongoDB connection
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client.iotdb

@app.on_event("startup")
async def startup_db_client():
    """Initialize database connection on startup"""
    await client.admin.command('ping')

@app.on_event("shutdown")
async def shutdown_db_client():
    """Close database connection on shutdown"""
    client.close()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "IoT Telemetry Dashboard API is running"}

@app.get("/telemetry")
async def get_telemetry_data(limit: int = 100):
    """Get recent telemetry data"""
    collection = db.telemetry_raw
    cursor = collection.find().sort("ts", -1).limit(limit)
    data = []
    async for document in cursor:
        document["_id"] = str(document["_id"])
        data.append(document)
    return {"data": data}

@app.get("/aggregated")
async def get_aggregated_data(limit: int = 100):
    """Get aggregated telemetry data"""
    collection = db.aggregated_data
    cursor = collection.find().sort("timestamp", -1).limit(limit)
    data = []
    async for document in cursor:
        document["_id"] = str(document["_id"])
        data.append(document)
    return {"data": data}

@app.get("/alerts")
async def get_alerts(limit: int = 100):
    """Get recent alerts"""
    collection = db.alerts
    cursor = collection.find().sort("timestamp", -1).limit(limit)
    data = []
    async for document in cursor:
        document["_id"] = str(document["_id"])
        data.append(document)
    return {"data": data}

@app.get("/alerts/recent")
async def get_recent_alerts(limit: int = 100):
    """Get recent alerts (alias for /alerts)"""
    collection = db.alerts
    cursor = collection.find().sort("timestamp", -1).limit(limit)
    data = []
    async for document in cursor:
        document["_id"] = str(document["_id"])
        data.append(document)
    return {"data": data}

@app.get("/devices/{device_id}/aggregates")
async def get_device_aggregates(device_id: str, limit: int = 100):
    """Get aggregated data for a specific device"""
    collection = db.aggregated_data
    cursor = collection.find({"device_id": device_id}).sort("timestamp", -1).limit(limit)
    data = []
    async for document in cursor:
        document["_id"] = str(document["_id"])
        data.append(document)
    return {"device_id": device_id, "data": data}

@app.get("/devices/{device_id}/telemetry")
async def get_device_telemetry(device_id: str, limit: int = 100):
    """Get raw telemetry data for a specific device"""
    collection = db.telemetry_raw
    cursor = collection.find({"device_id": device_id}).sort("ts", -1).limit(limit)
    data = []
    async for document in cursor:
        document["_id"] = str(document["_id"])
        data.append(document)
    return {"device_id": device_id, "data": data}

@app.get("/devices")
async def get_devices():
    """Get list of all devices"""
    # Get unique device IDs from telemetry_raw collection
    devices = await db.telemetry_raw.distinct("device_id")
    return {"devices": devices}

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    telemetry_count = await db.telemetry_raw.count_documents({})
    aggregated_count = await db.aggregated_data.count_documents({})
    alerts_count = await db.alerts.count_documents({})
    
    return {
        "telemetry_records": telemetry_count,
        "aggregated_records": aggregated_count,
        "alerts": alerts_count
    }
