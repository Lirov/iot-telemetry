from pydantic import BaseModel
from datetime import datetime

class Telemetry(BaseModel):
    device_id: str
    ts: datetime
    temperature_c: float
    humidity: float
