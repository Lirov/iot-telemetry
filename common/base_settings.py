from pydantic_settings import BaseSettings, SettingsConfigDict

class BaseConfig(BaseSettings):
    kafka_bootstrap: str = "kafka:9092"
    mongo_uri: str = "mongodb://mongo:27017"
    mongo_db: str = "iotdb"
    raw_topic: str = "telemetry.raw"
    alerts_topic: str = "alerts.triggered"
    agg_collection: str = "telemetry_minute"
    raw_collection: str = "telemetry_raw"
    alerts_collection: str = "alerts"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
