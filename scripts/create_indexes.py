#!/usr/bin/env python3
"""
Script to create MongoDB indexes for performance optimization
"""
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def create_indexes():
    """Create MongoDB indexes for optimal performance"""
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.iotdb
    
    print("Creating MongoDB indexes...")
    
    try:
        # Create index for telemetry_raw collection
        # Note: The collection name is telemetry_raw, not telemetry_minute
        print("Creating index for telemetry_raw collection...")
        await db.telemetry_raw.create_index([("device_id", 1), ("ts", -1)])
        print("✓ Created index: device_id:1, ts:-1 on telemetry_raw")
        
        # Create index for alerts collection
        print("Creating index for alerts collection...")
        await db.alerts.create_index([("created_at", -1)])
        print("✓ Created index: created_at:-1 on alerts")
        
        # Create index for aggregated_data collection
        print("Creating index for aggregated_data collection...")
        await db.aggregated_data.create_index([("device_id", 1), ("timestamp", -1)])
        print("✓ Created index: device_id:1, timestamp:-1 on aggregated_data")
        
        # Create additional useful indexes
        print("Creating additional indexes...")
        await db.telemetry_raw.create_index([("ts", -1)])
        print("✓ Created index: ts:-1 on telemetry_raw")
        
        await db.alerts.create_index([("device_id", 1), ("created_at", -1)])
        print("✓ Created index: device_id:1, created_at:-1 on alerts")
        
        await db.aggregated_data.create_index([("sensor_type", 1), ("timestamp", -1)])
        print("✓ Created index: sensor_type:1, timestamp:-1 on aggregated_data")
        
        print("\nAll indexes created successfully!")
        
    except Exception as e:
        print(f"Error creating indexes: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(create_indexes())
