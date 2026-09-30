"""Simulate a fleet of devices sending heartbeats to the monitor.

Usage:
    python simulator/simulator.py
    python simulator/simulator.py --url http://127.0.0.1:8000 --interval 5 --devices 5
    python simulator/simulator.py --skip device-03
"""

import argparse
import signal
import sys
import threading
import time
from datetime import datetime, timezone

import httpx


def register_device(base_url: str, device_id: str, name: str) -> None:
    resp = httpx.post(f"{base_url}/devices", json={"id": device_id, "name": name})
    if resp.status_code == 409:
        print(f"[{device_id}] already registered")
    elif resp.status_code == 201:
        print(f"[{device_id}] registered")
    else:
        print(f"[{device_id}] register failed: {resp.status_code} {resp.text}")


def heartbeat_loop(
    base_url: str,
    device_id: str,
    interval: int,
    stop_event: threading.Event,
) -> None:
    while not stop_event.is_set():
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "OK",
        }
        try:
            resp = httpx.post(
                f"{base_url}/devices/{device_id}/heartbeat",
                json=payload,
                timeout=5,
            )
            print(f"[{device_id}] heartbeat -> {resp.status_code}")
        except httpx.HTTPError as exc:
            print(f"[{device_id}] heartbeat error: {exc}")
        stop_event.wait(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description="Simulate device heartbeats.")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--devices", type=int, default=5)
    parser.add_argument("--interval", type=int, default=5)
    parser.add_argument(
        "--skip",
        action="append",
        default=[],
        help="Device id to skip (can be repeated). e.g. --skip device-03",
    )
    args = parser.parse_args()

    device_ids = [f"device-{i:02d}" for i in range(1, args.devices + 1)]
    active = [d for d in device_ids if d not in args.skip]

    if args.skip:
        print(f"Skipping: {', '.join(args.skip)}")

    for did in active:
        register_device(args.url, did, f"Simulated {did}")

    stop_event = threading.Event()

    def _shutdown(signum, frame):
        print("\nStopping simulator...")
        stop_event.set()

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    threads = []
    for did in active:
        t = threading.Thread(
            target=heartbeat_loop,
            args=(args.url, did, args.interval, stop_event),
            daemon=True,
        )
        t.start()
        threads.append(t)

    try:
        while not stop_event.is_set():
            time.sleep(0.5)
    except KeyboardInterrupt:
        stop_event.set()

    for t in threads:
        t.join(timeout=2)

    print("Simulator stopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())