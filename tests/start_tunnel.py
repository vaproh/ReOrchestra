#!/usr/bin/env python3
"""
Start Cloudflare Tunnel to expose local test server.

Usage:
    python tests/start_tunnel.py
    python tests/start_tunnel.py --port 8080

This creates a temporary tunnel URL (trycloudflare.com).
For a permanent tunnel, use: python tests/start_permanent_tunnel.py
"""

import subprocess
import time
import re
import os
import sys
import argparse

# Load settings from .env
try:
    sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from app.config import get_settings
    settings = get_settings()
    DEFAULT_PORT = settings.tunnel_port or 8080
    DEFAULT_DOMAIN = settings.tunnel_domain
    DEFAULT_SUBDOMAIN = settings.tunnel_subdomain
except Exception:
    DEFAULT_PORT = 8080
    DEFAULT_DOMAIN = "vaproh.space"
    DEFAULT_SUBDOMAIN = "reorchestra-test"


def run_cmd(cmd):
    """Run shell command and return output."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Start Cloudflare Tunnel for ReOrchestra test server"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Local port to tunnel (default: {DEFAULT_PORT})",
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("ReOrchestra Test Mode - Cloudflare Tunnel")
    print("=" * 60)
    print()
    print(f"Tunneling localhost:{args.port} via Cloudflare...")
    print()
    
    # Check if cloudflared is installed
    _, rc = run_cmd("cloudflared --version")
    if rc != 0:
        print("❌ cloudflared not found!")
        print()
        print("Install it from:")
        print("https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        sys.exit(1)
    print("✅ cloudflared is installed")
    print()
    
    # Start tunnel
    print(f"🌐 Starting tunnel...")
    print()
    
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "--url", f"http://localhost:{args.port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    
    tunnel_url = None
    if proc.stdout:
        for line in iter(proc.stdout.readline, ""):
            print(line.rstrip(), flush=True)
            
            # Look for cloudflared's tunnel URL
            match = re.search(r"(https://[a-z0-9-]+\.trycloudflare\.com)", line)
            if match:
                tunnel_url = match.group(1)
                print(f"\n✅ Tunnel ready: {tunnel_url}")
                break
            
            match = re.search(r"(https://[a-z0-9-]+\.[a-z0-9-]+\.[a-z]+)", line)
            if match:
                tunnel_url = match.group(1)
                print(f"\n✅ Tunnel ready: {tunnel_url}")
                break
    
    if not tunnel_url:
        print("\n❌ Failed to get tunnel URL")
        proc.terminate()
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("📋 Next steps:")
    print(f"1. Your test server is accessible at: {tunnel_url}")
    print(f"2. Set this URL in your environment:")
    print(f"   export TEST_SERVER_URL={tunnel_url}")
    print(f"   export APP_MODE=test")
    print(f"3. Run your tests: pytest tests/ -v")
    print("=" * 60)
    print()
    print("⏹️  Press Ctrl+C to stop the tunnel")
    print()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping tunnel...")
        proc.terminate()
        proc.wait()
        print("✅ Tunnel stopped")


if __name__ == "__main__":
    main()
