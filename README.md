# Mini Device Fleet Monitor

A small service that tracks a fleet of simulated devices via heartbeats and exposes
their current ONLINE/OFFLINE status.

**Stack:** Python · FastAPI · Pydantic · pytest

## What it does

- Registers devices by ID and name
- Accepts heartbeats with client-supplied UTC timestamps
- Computes ONLINE/OFFLINE status on read using a 30-second timeout rule
- Exposes a fleet summary (total / online / offline)
- Ships with a simulator that runs 5 devices concurrently

## Design

**Stack:** Python 3.12+ (developed and tested on 3.14.7), FastAPI, Pydantic v2, Uvicorn.

**Layout:**

```text
src/
  main.py      FastAPI routes
  models.py    Pydantic request/response schemas
  service.py   In-memory store + status logic
  clock.py     Injectable time source
tests/         pytest suite
simulator/     Device heartbeat simulator
```

**Key decisions:**

1. **Status is never stored.** It is computed on every read via
   `compute_status(last_heartbeat, now)`. This guarantees the API always returns
   a value consistent with the 30-second rule.
2. **Time is injectable.** `src/clock.py` provides `now()`, which tests can
   monkeypatch or which can be substituted with fixed timestamps. This makes the
   timeout boundary deterministic to test — no `time.sleep(31)`.
3. **Client timestamps are authoritative.** The `timestamp` field in the
   heartbeat body is used for both ordering and status computation. Out-of-order
   (older) heartbeats are ignored — only the maximum timestamp seen is kept.
4. **Timezone-aware UTC only.** Naive datetimes are rejected with HTTP 422 by
   a Pydantic validator. Offset-aware timestamps are normalized to UTC.
5. **In-memory storage.** A `dict` guarded by a `threading.Lock`. No database,
   no persistence — this is a 3-hour assessment, not a production service.

**Status rule:**

- ONLINE if `now - last_heartbeat <= 30s`
- OFFLINE if `now - last_heartbeat > 30s`, or if no heartbeat has ever been received

## Prerequisites

- Python 3.12 or later (developed and tested on 3.14.7)
- Git

## Build

```bash
git clone https://github.com/UttamPatnaik/mini-device-fleet-monitor
cd mini-device-fleet-monitor
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# or: source .venv/bin/activate  # macOS / Linux
pip install -r requirements.txt
```

## Run

```bash
uvicorn src.main:app --reload
```

The server listens on `http://127.0.0.1:8000`.

Interactive API docs: `http://127.0.0.1:8000/docs`

Stop the server with `Ctrl+C`.

## Run the simulator

In a second terminal (with the server running):

```bash
python simulator/simulator.py
```

This registers `device-01` through `device-05` and sends a heartbeat every 5 seconds.

Options:

```bash
python simulator/simulator.py --devices 10 --interval 3
python simulator/simulator.py --skip device-03
```

To observe the timeout:

1. Start the server and simulator.
2. `curl http://127.0.0.1:8000/summary` → `{"total":5,"online":5,"offline":0}`
3. Stop the simulator with `Ctrl+C`.
4. `curl http://127.0.0.1:8000/summary` immediately → still `online: 5`
5. Wait ~35 seconds.
6. `curl http://127.0.0.1:8000/summary` → `{"total":5,"online":0,"offline":5}`

## Run the tests

```bash
pytest -v
```

12 tests covering registration, heartbeats, status, and the 30-second boundary.

## Example API requests

Register a device:

```bash
curl -X POST http://127.0.0.1:8000/devices \
  -H "Content-Type: application/json" \
  -d '{"id": "device-01", "name": "Lab Device 01"}'
```

Send a heartbeat:

```bash
curl -X POST http://127.0.0.1:8000/devices/device-01/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"timestamp": "2026-09-30T10:30:00Z", "status": "OK"}'
```

List devices:

```bash
curl http://127.0.0.1:8000/devices
```

Get a device:

```bash
curl http://127.0.0.1:8000/devices/device-01
```

Fleet summary:

```bash
curl http://127.0.0.1:8000/summary
```

Error responses:

- `409 Conflict` — duplicate device registration
- `404 Not Found` — heartbeat or lookup for an unknown device
- `422 Unprocessable Entity` — malformed or timezone-naive timestamp

## Assumptions

- The client-supplied `timestamp` in the heartbeat body is trusted and used
  directly. Server receipt time is not used for status calculation.
- Future timestamps are accepted as-is. A device whose heartbeat is in the
  future will remain ONLINE until `now` passes `timestamp + 30s`. Clock-skew
  handling is out of scope.
- A device that has been registered but never sent a heartbeat is OFFLINE with
  `last_heartbeat: null`.
- Devices are never deleted or un-registered.
- `status` on the heartbeat payload (e.g. `"OK"`) is stored nowhere and has no
  effect on the ONLINE/OFFLINE computation — that rule is purely time-based.

## Known limitations

- Storage is in-memory. Restarting the server loses all state.
- No authentication or rate limiting.
- No pagination on `GET /devices`.
- Simulator devices share one process; stopping one device without stopping the
  others requires editing the simulator or using `--skip`.
- No clock-skew protection (by design — documented above).

## What I would improve with one more day

- Persist devices and heartbeats to SQLite so state survives restarts.
- Add a `DELETE /devices/{id}` endpoint and a way to mark a device as retired.
- Structured JSON logging with request IDs, plus `TIMEOUT_SECONDS` configurable
  via environment variable.
- Additional per-heartbeat metrics (`cpu_usage`, `signal_strength`) stored and
  exposed in device details.
- Dockerfile and a `docker-compose.yml` for one-command startup.

## AI Usage

**Tool used:** ChatGPT (GPT-4 / GPT-5 class model).

**What I used it for:**

- Reviewing my initial plan and flagging edge cases (duplicate registration,
  unknown-device heartbeats, malformed timestamps, out-of-order heartbeats,
  timezone handling, the 30-second boundary).
- Reviewing the Pydantic models and business logic I wrote.
- Cross-checking test coverage for the timeout boundary.

**One suggestion I changed/rejected:**

The AI initially suggested testing the 30-second timeout using `time.sleep(31)`
inside the test. I rejected that and instead designed `src/clock.py` with an
injectable `now()` and wrote `compute_status(last_heartbeat, now)` so the
timeout could be tested with fixed datetimes at `t+0`, `t+30`, and `t+31`.
This made the test suite run in ~0.3 seconds instead of waiting half a minute
per case, and removed all timing flakiness.

**One thing I personally verified:**

I ran the simulator with 5 devices, stopped it with `Ctrl+C`, and confirmed via
`curl /summary` that the fleet remained `online=5` immediately after the stop
and flipped to `offline=5` after approximately 35 seconds. I also verified the
`--skip device-03` flag excluded that device from registration and from the
`GET /devices` listing.