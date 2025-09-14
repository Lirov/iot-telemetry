import argparse, random, time, threading, requests
from datetime import datetime, timezone

def one_device(device_id, base_url, rps):
    interval = 1.0 / rps
    while True:
        payload = {
            "device_id": device_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "temperature_c": round(random.uniform(35.0, 70.0), 2),
            "humidity": round(random.uniform(20.0, 60.0), 1),
            "lat": 32.1,
            "lon": 34.9
        }
        try:
            requests.post(f"{base_url}/ingest", json=payload, timeout=2)
        except Exception:
            pass
        time.sleep(interval)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--devices", type=int, default=10)
    p.add_argument("--rps", type=float, default=1.0, help="per-device requests/sec")
    p.add_argument("--base-url", default="http://localhost:8001")
    args = p.parse_args()

    print(f"Starting {args.devices} devices at {args.rps} rps to {args.base_url}")
    threads = []
    for i in range(args.devices):
        t = threading.Thread(target=one_device, args=(f"dev-{i+1}", args.base_url, args.rps), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
