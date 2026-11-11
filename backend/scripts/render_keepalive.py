"""
backend/scripts/render_keepalive.py
-----------------------------------
Standalone Render Keepalive Daemon:
Render free-tier web services spin down into cold sleep after 15 minutes of zero traffic.
This lightweight script sends an HTTP GET request to your deployed /health endpoint
every 10 minutes (600s), ensuring your API stays warm with 0ms cold-start latency.

Usage:
    python backend/scripts/render_keepalive.py --url https://<your-render-app>.onrender.com/health
    python backend/scripts/render_keepalive.py --interval 600
"""

import sys
import os
import time
import argparse
from datetime import datetime, timezone
import urllib.request
import urllib.error

def utc_timestamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def ping_health_endpoint(target_url: str) -> bool:
    req = urllib.request.Request(
        target_url,
        headers={"User-Agent": "CareerBeacon-KeepAlive/2.0 (+https://careerbeacon.internal)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.getcode()
            body = resp.read().decode("utf-8", errors="ignore")
            print(f"[{utc_timestamp()}] Keep-alive Ping OK -> {target_url} (HTTP {code}): {body[:60].strip()}")
            return True
    except urllib.error.HTTPError as he:
        print(f"[{utc_timestamp()}] Keep-alive Ping HTTP Error {he.code} -> {target_url}")
        return False
    except Exception as ex:
        print(f"[{utc_timestamp()}] Keep-alive Ping Connection Warning: {ex}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Career Beacon Render Keep-Alive Ping Service")
    parser.add_argument("--url", default=os.getenv("RENDER_EXTERNAL_URL") or os.getenv("PING_URL") or "http://127.0.0.1:8000/health", help="Target /health URL to ping")
    parser.add_argument("--interval", type=int, default=600, help="Interval in seconds between pings (default: 600s / 10min)")
    args = parser.parse_args()

    url = args.url.strip()
    if not url.endswith("/health"):
        url = f"{url.rstrip('/')}/health"

    print(f"=== CAREER BEACON RENDER KEEP-ALIVE DAEMON ===")
    print(f"Target URL: {url}")
    print(f"Interval:   {args.interval} seconds (10 minutes)")
    print(f"Press CTRL+C to terminate.")

    # Execute immediate initial ping
    ping_health_endpoint(url)

    while True:
        try:
            time.sleep(args.interval)
            ping_health_endpoint(url)
        except KeyboardInterrupt:
            print(f"\n[{utc_timestamp()}] Keep-alive daemon terminated by user.")
            break

if __name__ == "__main__":
    main()
