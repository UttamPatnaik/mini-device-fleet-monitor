from fastapi import FastAPI, HTTPException, status

from .models import DeviceCreate, DeviceResponse, Heartbeat, SummaryResponse
from .service import DeviceStore, DuplicateDeviceError, UnknownDeviceError


app = FastAPI(title="Mini Device Fleet Monitor")
store = DeviceStore()


@app.post("/devices", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def register_device(payload: DeviceCreate) -> DeviceResponse:
    try:
        return store.register(payload)
    except DuplicateDeviceError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Device '{payload.id}' already exists",
        )


@app.get("/devices", response_model=list[DeviceResponse])
def list_devices() -> list[DeviceResponse]:
    return store.list_all()


@app.get("/devices/{device_id}", response_model=DeviceResponse)
def get_device(device_id: str) -> DeviceResponse:
    try:
        return store.get(device_id)
    except UnknownDeviceError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found",
        )


@app.post("/devices/{device_id}/heartbeat", status_code=status.HTTP_200_OK)
def receive_heartbeat(device_id: str, payload: Heartbeat) -> dict:
    try:
        store.record_heartbeat(device_id, payload)
    except UnknownDeviceError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{device_id}' not found",
        )
    return {"status": "received"}


@app.get("/summary", response_model=SummaryResponse)
def fleet_summary() -> SummaryResponse:
    return store.summary()