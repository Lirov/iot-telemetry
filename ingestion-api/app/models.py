from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TelemetryIn(BaseModel):
    device_id: str = Field(..., examples=["dev-123"])
    ts: Optional[datetime] = None
    temperature_c: float
    humidity: float
    lat: Optional[float] = None
    lon: Optional[float] = None
