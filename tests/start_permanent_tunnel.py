#!/usr/bin/env python3
"""
Create and start a permanent Cloudflare Tunnel for ReOrchestra test server.

Target: reorchestra-test.vaproh.space (configurable)

Usage:
    python tests/start_permanent_tunnel.py
    python tests/start_permanent_tunnel.py --subdomain mytest
    python tests/start_permanent_tunnel.py --domain example.com
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
    DEFAULT_DOMAIN = settings.tunnel_domain
    DEFAULT_SUBDOMAIN = settings.tunnel_subdomain
    DEFAULT_TUNNEL_NAME = settings.tunnel_name
    DEFAULT_PORT = settings.tunnel_port or 8080
except Exception:
    DEFAULT_DOMAIN = "vaproh.space"
    DEFAULT_SUBDOMAIN = "reorchestra-test"
    DEFAULT_TUNNEL_NAME = "reorchestra-test"
    DEFAULT_PORT = 8080


def run_cmd(cmd, timeout=30):
    """Run shell command with timeout, return (output, returncode)."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.stdout.strip(), result.returncode
    except subprocess.TimeoutExpired:
        return "", -1


def get_tunnel_id(tunnel_name):
    """Get existing tunnel ID by name."""
    import json
    output, _ = run_cmd("cloudflared tunnel list --output json", timeout=10)
    if not output or output == "null":
        return None
    try:
        tunnels = json.loads(output)
        if not tunnels:
            return None
        for tunnel in tunnels:
            if tunnel.get("name") == tunnel_name:
                return tunnel.get("id")
    except (json.JSONDecodeError, TypeError):
        pass
    return None


def create_tunnel(tunnel_name):
    """Create a new tunnel and return its ID."""
    print(f"Creating tunnel '{tunnel_name}'...")
    output, rc = run_cmd(f"cloudflared tunnel create {tunnel_name}", timeout=30)
    if rc != 0 or not output:
        print(f"Tunnel creation failed: {output}")
        return None

    match = re.search(r"with id\s+([a-f0-9-]+)", output or "")
    if match:
        return match.group(1)

    return get_tunnel_id(tunnel_name)


def check_dns(subdomain, domain, tunnel_id):
    """Check if DNS CNAME already points to the tunnel."""
    full_domain = f"{subdomain}.{domain}"
    cname_target = f"{tunnel_id}.cfargotunnel.com"

    output, rc = run_cmd(f"dig +short CNAME {full_domain}", timeout=5)
    if output and cname_target in output:
        return True
    return False


def configure_dns(subdomain, domain, tunnel_id, tunnel_name):
    """Try to configure DNS, but don't hang if it fails."""
    full_domain = f"{subdomain}.{domain}"
    cname_target = f"{tunnel_id}.cfargotunnel.com"

    if check_dns(subdomain, domain, tunnel_id):
        print(f"✅ DNS already configured: {full_domain} -> {cname_target}")
        return True

    print(f"Configuring DNS: {full_domain} -> {cname_target}")
    print("  (Trying cloudflared tunnel route dns...)")

    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "route", "dns", tunnel_id, full_domain],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        output, _ = proc.communicate(timeout=5)
        if proc.returncode == 0:
            print(f"  ✅ DNS configured automatically")
            return True
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    print()
    print("=" * 60)
    print("📋 Manual DNS Setup Required")
    print("=" * 60)
    print(f"Go to Cloudflare Dashboard → DNS → Add record:")
    print()
    print(f"  Type:    CNAME")
    print(f"  Name:    {subdomain}")
    print(f"  Target:  {cname_target}")
    print()
    print("After adding the DNS record, your tunnel will be live at:")
    print(f"  https://{full_domain}")
    print("=" * 60)
    print()
    return False


def start_tunnel(tunnel_name, tunnel_id, port):
    """Start the tunnel."""
    print(f"Starting tunnel '{tunnel_name}' (ID: {tunnel_id})...")

    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "run", tunnel_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    connected = False
    if proc.stdout:
        for line in iter(proc.stdout.readline, ""):
            if line:
                print(line.rstrip(), flush=True)
            if "connected successfully" in line.lower():
                connected = True
                break

    if not connected:
        print("  Tunnel starting in background...")

    return proc


def main():
    parser = argparse.ArgumentParser(
        description="Start permanent Cloudflare Tunnel for ReOrchestra"
    )
    parser.add_argument(
        "--subdomain",
        default=os.environ.get("TUNNEL_SUBDOMAIN", DEFAULT_SUBDOMAIN),
        help=f"Subdomain (default: {DEFAULT_SUBDOMAIN})",
    )
    parser.add_argument(
        "--domain",
        default=os.environ.get("TUNNEL_DOMAIN", DEFAULT_DOMAIN),
        help=f"Domain (default: {DEFAULT_DOMAIN})",
    )
    parser.add_argument(
        "--tunnel-name",
        default=os.environ.get("TUNNEL_NAME", DEFAULT_TUNNEL_NAME),
        help=f"Tunnel name (default: {DEFAULT_TUNNEL_NAME})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Local port (default: {DEFAULT_PORT})",
    )

    args = parser.parse_args()

    full_domain = f"{args.subdomain}.{args.domain}"
    tunnel_name = args.tunnel_name

    print("=" * 60)
    print("ReOrchestra - Permanent Cloudflare Tunnel")
    print("=" * 60)
    print(f"Target: https://{full_domain}")
    print(f"Tunnel name: {tunnel_name}")
    print(f"Local port: {args.port}")
    print()

    _, rc = run_cmd("cloudflared --version", timeout=5)
    if rc != 0:
        print("❌ cloudflared not found!")
        print("Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        sys.exit(1)
    print("✅ cloudflared installed")

    tunnel_id = get_tunnel_id(tunnel_name)
    if not tunnel_id:
        print(f"Creating new tunnel '{tunnel_name}'...")
        tunnel_id = create_tunnel(tunnel_name)
        if not tunnel_id:
            print("❌ Failed to create tunnel")
            sys.exit(1)
        print(f"✅ Created tunnel: {tunnel_id}")
    else:
        print(f"✅ Using existing tunnel: {tunnel_id}")

    configure_dns(args.subdomain, args.domain, tunnel_id, tunnel_name)

    print("🚀 Starting tunnel...")
    proc = start_tunnel(tunnel_name, tunnel_id, args.port)

    print()
    print("=" * 60)
    print("✅ Tunnel is running!")
    print()
    print(f"🌐 Your test server will be at: https://{full_domain}")
    print("   (after DNS is configured)")
    print()
    print("Environment variables:")
    print(f"  export TEST_SERVER_URL=https://{full_domain}")
    print(f"  export APP_MODE=test")
    print()
    print("Press Ctrl+C to stop the tunnel")
    print("=" * 60)

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
