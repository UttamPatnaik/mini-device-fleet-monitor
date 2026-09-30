from __future__ import annotations

import threading
from datetime import datetime, timedelta

from .clock import now as _now
from .models import DeviceCreate, DeviceResponse, Heartbeat, SummaryResponse


TIMEOUT_SECONDS = 30


def compute_status(last_heartbeat: datetime | None, current: datetime) -> str:
    """ONLINE if last heartbeat is within TIMEOUT_SECONDS, else OFFLINE."""
    if last_heartbeat is None:
        return "OFFLINE"
    if current - last_heartbeat <= timedelta(seconds=TIMEOUT_SECONDS):
        return "ONLINE"
    return "OFFLINE"


class DuplicateDeviceError(Exception):
    pass


class UnknownDeviceError(Exception):
    pass


class DeviceStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._devices: dict[str, dict] = {}

    def register(self, payload: DeviceCreate) -> DeviceResponse:
        with self._lock:
            if payload.id in self._devices:
                raise DuplicateDeviceError(payload.id)
            self._devices[payload.id] = {
                "id": payload.id,
                "name": payload.name,
                "last_heartbeat": None,
            }
            return self._to_response(payload.id, _now())

    def get(self, device_id: str) -> DeviceResponse:
        with self._lock:
            if device_id not in self._devices:
                raise UnknownDeviceError(device_id)
            return self._to_response(device_id, _now())

    def list_all(self) -> list[DeviceResponse]:
        with self._lock:
            current = _now()
            return [self._to_response(did, current) for did in self._devices]

    def record_heartbeat(self, device_id: str, hb: Heartbeat) -> None:
        with self._lock:
            if device_id not in self._devices:
                raise UnknownDeviceError(device_id)
            stored = self._devices[device_id]["last_heartbeat"]
            # Ignore out-of-order heartbeats: keep the maximum timestamp seen.
            if stored is None or hb.timestamp > stored:
                self._devices[device_id]["last_heartbeat"] = hb.timestamp

    def summary(self) -> SummaryResponse:
        with self._lock:
            current = _now()
            online = 0
            offline = 0
            for data in self._devices.values():
                if compute_status(data["last_heartbeat"], current) == "ONLINE":
                    online += 1
                else:
                    offline += 1
            return SummaryResponse(
                total=len(self._devices),
                online=online,
                offline=offline,
            )

    def _to_response(self, device_id: str, current: datetime) -> DeviceResponse:
        data = self._devices[device_id]
        return DeviceResponse(
            id=data["id"],
            name=data["name"],
            status=compute_status(data["last_heartbeat"], current),
            last_heartbeat=data["last_heartbeat"],
        )