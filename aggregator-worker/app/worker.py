import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Dict, Any
from confluent_kafka import Consumer, KafkaError, Producer
from motor.motor_asyncio import AsyncIOMotorClient
import logging
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo:27017")
TELEMETRY_TOPIC = os.getenv("TELEMETRY_TOPIC", "telemetry.raw")
DLQ_TOPIC = os.getenv("DLQ_TOPIC", "telemetry.dlq")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# MongoDB connection
client = AsyncIOMotorClient(MONGO_URL)
db = client.iotdb

# Prometheus metrics
messages_processed_total = Counter('aggregator_messages_processed_total', 'Total number of messages processed', ['device_id', 'sensor_type'])
aggregations_flushed_total = Counter('aggregator_aggregations_flushed_total', 'Total number of aggregations flushed', ['device_id', 'sensor_type'])
processing_duration = Histogram('aggregator_processing_duration_seconds', 'Time spent processing messages')
active_aggregations = Gauge('aggregator_active_aggregations', 'Number of active aggregations in memory')
kafka_consumer_errors = Counter('aggregator_kafka_consumer_errors_total', 'Total number of Kafka consumer errors')
mongo_write_errors = Counter('aggregator_mongo_write_errors_total', 'Total number of MongoDB write errors')
dlq_messages_total = Counter('aggregator_dlq_messages_total', 'Total number of messages sent to DLQ')
retry_attempts_total = Counter('aggregator_retry_attempts_total', 'Total number of retry attempts')

class AggregatorWorker:
    def __init__(self):
        self.consumer = Consumer({
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
            'group.id': 'aggregator_worker',
            'auto.offset.reset': 'latest'
        })
        self.dlq_producer = Producer({
            'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS
        })
        self.aggregated_data = {}
        self.failed_messages = {}  # Track failed messages for retry
        
    async def start(self):
        """Start the aggregator worker"""
        logger.info("Starting aggregator worker...")
        
        # Start Prometheus metrics server
        start_http_server(8000)
        logger.info("Prometheus metrics server started on port 8000")
        
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
                        kafka_consumer_errors.inc()
                        continue
                
                # Process the message with retry logic
                await self.process_telemetry_message_with_retry(msg.value().decode('utf-8'))
                
        except KeyboardInterrupt:
            logger.info("Shutting down aggregator worker...")
        finally:
            self.consumer.close()
            self.dlq_producer.flush()
            client.close()
    
    async def process_telemetry_message_with_retry(self, message: str):
        """Process telemetry message with retry logic and DLQ"""
        message_hash = hash(message)
        
        # Check if this message has failed before
        if message_hash in self.failed_messages:
            retry_count = self.failed_messages[message_hash]['retry_count']
            if retry_count >= MAX_RETRIES:
                # Send to DLQ after max retries
                await self.send_to_dlq(message, f"Max retries ({MAX_RETRIES}) exceeded")
                del self.failed_messages[message_hash]
                return
            else:
                # Increment retry count
                self.failed_messages[message_hash]['retry_count'] += 1
                retry_attempts_total.inc()
        else:
            # First attempt
            self.failed_messages[message_hash] = {'retry_count': 0}
        
        try:
            await self.process_telemetry_message(message)
            # Success - remove from failed messages
            if message_hash in self.failed_messages:
                del self.failed_messages[message_hash]
        except Exception as e:
            logger.error(f"Error processing message (attempt {self.failed_messages[message_hash]['retry_count'] + 1}): {e}")
            # The retry logic will be handled in the next call
    
    async def send_to_dlq(self, message: str, reason: str):
        """Send failed message to Dead Letter Queue"""
        try:
            dlq_message = {
                'original_message': message,
                'failure_reason': reason,
                'timestamp': datetime.utcnow().isoformat(),
                'worker': 'aggregator_worker'
            }
            
            self.dlq_producer.produce(
                DLQ_TOPIC,
                json.dumps(dlq_message).encode('utf-8'),
                callback=self._dlq_delivery_callback
            )
            self.dlq_producer.poll(0)
            
            dlq_messages_total.inc()
            logger.warning(f"Message sent to DLQ: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to send message to DLQ: {e}")
    
    def _dlq_delivery_callback(self, err, msg):
        """Callback for DLQ message delivery"""
        if err:
            logger.error(f"DLQ delivery failed: {err}")
        else:
            logger.info(f"Message delivered to DLQ: {msg.topic()}")
    
    async def process_telemetry_message(self, message: str):
        """Process a telemetry message and aggregate data"""
        with processing_duration.time():
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
                    
                    # Update metrics
                    messages_processed_total.labels(device_id=device_id, sensor_type=sensor_type).inc()
                    active_aggregations.set(len(self.aggregated_data))
                    
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
            
            # Update metrics
            aggregations_flushed_total.labels(device_id=agg['device_id'], sensor_type=agg['sensor_type']).inc()
            
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
            
            # Update active aggregations count
            active_aggregations.set(len(self.aggregated_data))
            
        except Exception as e:
            logger.error(f"Error flushing aggregation for {agg_key}: {e}")
            mongo_write_errors.inc()

async def main():
    """Main function to run the aggregator worker"""
    worker = AggregatorWorker()
    await worker.start()

if __name__ == "__main__":
    asyncio.run(main())
