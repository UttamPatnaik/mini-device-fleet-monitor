from datetime import datetime, timezone
from pydantic import BaseModel, Field, field_validator


class DeviceCreate(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)


class Heartbeat(BaseModel):
    timestamp: datetime
    status: str

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)


class DeviceResponse(BaseModel):
    id: str
    name: str
    status: str
    last_heartbeat: datetime | None


class SummaryResponse(BaseModel):
    total: int
    online: int
    offline: int