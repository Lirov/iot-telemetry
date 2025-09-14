import asyncio
import json
import os
from datetime import datetime
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

class AlertsWorker:
    def __init__(self):
        self.consumer = Consumer({
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
            'group.id': 'alerts_worker',
            'auto.offset.reset': 'latest'
        })
        
        # Alert thresholds (can be configured via environment variables)
        self.thresholds = {
            'temperature_c': {
                'min': float(os.getenv('TEMP_MIN_THRESHOLD', '-10')),
                'max': float(os.getenv('TEMP_MAX_THRESHOLD', '50'))
            },
            'humidity': {
                'min': float(os.getenv('HUMIDITY_MIN_THRESHOLD', '0')),
                'max': float(os.getenv('HUMIDITY_MAX_THRESHOLD', '100'))
            }
        }
        
    async def start(self):
        """Start the alerts worker"""
        logger.info("Starting alerts worker...")
        
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
            logger.info("Shutting down alerts worker...")
        finally:
            self.consumer.close()
            client.close()
    
    async def process_telemetry_message(self, message: str):
        """Process a telemetry message and check for alerts"""
        try:
            data = json.loads(message)
            device_id = data.get('device_id')
            timestamp = data.get('ts', datetime.utcnow().isoformat())
            
            if not device_id:
                logger.warning(f"Invalid telemetry data: {data}")
                return
            
            # Check each sensor value for alerts
            sensors = {
                'temperature_c': data.get('temperature_c'),
                'humidity': data.get('humidity')
            }
            
            for sensor_type, value in sensors.items():
                if value is not None:
                    await self.check_alerts(device_id, sensor_type, value, timestamp)
                
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON message: {message}")
        except Exception as e:
            logger.error(f"Error processing telemetry message: {e}")
    
    async def check_alerts(self, device_id: str, sensor_type: str, value: float, timestamp: str):
        """Check if the sensor value triggers any alerts"""
        if sensor_type not in self.thresholds:
            return
        
        threshold = self.thresholds[sensor_type]
        alert_triggered = False
        alert_type = None
        severity = "warning"
        
        if value < threshold['min']:
            alert_triggered = True
            alert_type = f"{sensor_type}_low"
            severity = "critical" if value < threshold['min'] * 0.8 else "warning"
        elif value > threshold['max']:
            alert_triggered = True
            alert_type = f"{sensor_type}_high"
            severity = "critical" if value > threshold['max'] * 1.2 else "warning"
        
        if alert_triggered:
            await self.create_alert(device_id, sensor_type, value, alert_type, severity, timestamp)
    
    async def create_alert(self, device_id: str, sensor_type: str, value: float, 
                          alert_type: str, severity: str, timestamp: str):
        """Create an alert record in the database"""
        try:
            alert = {
                'device_id': device_id,
                'sensor_type': sensor_type,
                'value': value,
                'alert_type': alert_type,
                'severity': severity,
                'message': self.generate_alert_message(sensor_type, value, alert_type, severity),
                'timestamp': timestamp,
                'created_at': datetime.utcnow().isoformat(),
                'status': 'active'
            }
            
            # Store alert in database
            await db.alerts.insert_one(alert)
            logger.warning(f"Alert created: {alert['message']}")
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
    
    def generate_alert_message(self, sensor_type: str, value: float, alert_type: str, severity: str) -> str:
        """Generate a human-readable alert message"""
        if 'low' in alert_type:
            return f"{severity.upper()}: {sensor_type} value {value} is below minimum threshold"
        elif 'high' in alert_type:
            return f"{severity.upper()}: {sensor_type} value {value} is above maximum threshold"
        else:
            return f"{severity.upper()}: {sensor_type} value {value} is outside normal range"

async def main():
    """Main function to run the alerts worker"""
    worker = AlertsWorker()
    await worker.start()

if __name__ == "__main__":
    asyncio.run(main())
