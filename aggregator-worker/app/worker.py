import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any
from confluent_kafka import Consumer, KafkaError
from motor.motor_asyncio import AsyncIOMotorClient
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
TELEMETRY_TOPIC = os.getenv("TELEMETRY_TOPIC", "telemetry.raw")

# MongoDB connection
client = AsyncIOMotorClient(MONGO_URL)
db = client.iotdb

class AggregatorWorker:
    def __init__(self):
        self.consumer = Consumer({
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
            'group.id': 'aggregator_worker',
            'auto.offset.reset': 'latest'
        })
        self.aggregated_data = {}
        
    async def start(self):
        """Start the aggregator worker"""
        logger.info("Starting aggregator worker...")
        
        # Subscribe to telemetry topic
        self.consumer.subscribe([TELEMETRY_TOPIC])
        
        try:
            while True:
                msg = self.consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                    
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    else:
                        logger.error(f"Consumer error: {msg.error()}")
                        continue
                
                # Process the message
                await self.process_telemetry_message(msg.value().decode('utf-8'))
                
        except KeyboardInterrupt:
            logger.info("Shutting down aggregator worker...")
        finally:
            self.consumer.close()
            client.close()
    
    async def process_telemetry_message(self, message: str):
        """Process a telemetry message and aggregate data"""
        try:
            data = json.loads(message)
            device_id = data.get('device_id')
            timestamp = data.get('ts', datetime.utcnow().isoformat())
            
            if not device_id:
                logger.warning(f"Invalid telemetry data: {data}")
                return
            
            # Process each sensor value
            sensors = {
                'temperature_c': data.get('temperature_c'),
                'humidity': data.get('humidity')
            }
            
            for sensor_type, value in sensors.items():
                if value is None:
                    continue
                    
                # Create aggregation key
                agg_key = f"{device_id}_{sensor_type}"
                
                # Initialize aggregation if not exists
                if agg_key not in self.aggregated_data:
                    self.aggregated_data[agg_key] = {
                        'device_id': device_id,
                        'sensor_type': sensor_type,
                        'count': 0,
                        'sum': 0,
                        'min': float('inf'),
                        'max': float('-inf'),
                        'last_updated': timestamp
                    }
                
                # Update aggregation
                agg = self.aggregated_data[agg_key]
                agg['count'] += 1
                agg['sum'] += value
                agg['min'] = min(agg['min'], value)
                agg['max'] = max(agg['max'], value)
                agg['last_updated'] = timestamp
                
                # Calculate average
                agg['average'] = agg['sum'] / agg['count']
                
                # Store in database every 10 records or every 5 minutes
                if agg['count'] % 10 == 0 or self.should_flush_aggregation(agg):
                    await self.flush_aggregation(agg_key)
                
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON message: {message}")
        except Exception as e:
            logger.error(f"Error processing telemetry message: {e}")
    
    def should_flush_aggregation(self, agg: Dict[str, Any]) -> bool:
        """Check if aggregation should be flushed based on time"""
        last_updated = datetime.fromisoformat(agg['last_updated'].replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        return (now - last_updated).total_seconds() > 300  # 5 minutes
    
    async def flush_aggregation(self, agg_key: str):
        """Flush aggregated data to database"""
        try:
            agg = self.aggregated_data[agg_key].copy()
            agg['timestamp'] = datetime.utcnow().isoformat()
            
            # Store in aggregated_data collection
            await db.aggregated_data.insert_one(agg)
            logger.info(f"Flushed aggregation for {agg_key}: {agg['count']} records")
            
            # Reset aggregation
            self.aggregated_data[agg_key] = {
                'device_id': agg['device_id'],
                'sensor_type': agg['sensor_type'],
                'count': 0,
                'sum': 0,
                'min': float('inf'),
                'max': float('-inf'),
                'last_updated': agg['timestamp']
            }
            
        except Exception as e:
            logger.error(f"Error flushing aggregation for {agg_key}: {e}")

async def main():
    """Main function to run the aggregator worker"""
    worker = AggregatorWorker()
    await worker.start()

if __name__ == "__main__":
    asyncio.run(main())
