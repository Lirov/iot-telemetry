import json, os
from confluent_kafka import Producer

producer = Producer({"bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "kafka:9092")})
RAW_TOPIC = os.getenv("RAW_TOPIC", "telemetry.raw")

def publish_telemetry(payload: dict):
    def ack(err, msg):
        if err:
            print(f"Kafka produce error: {err}")
    producer.produce(RAW_TOPIC, json.dumps(payload).encode("utf-8"), key=payload["device_id"], callback=ack)
    producer.poll(0)   # serve delivery callbacks
