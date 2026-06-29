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
import shutil

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


def run_cmd(cmd, check=True):
    """Run shell command and return (output, returncode)."""
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        print(f"Command failed: {cmd}")
        print(f"stderr: {result.stderr}")
        return None, result.returncode
    return result.stdout.strip(), result.returncode


def get_tunnel_id(tunnel_name):
    """Get existing tunnel ID by name."""
    import json
    output, _ = run_cmd("cloudflared tunnel list --output json", check=False)
    if not output:
        return None
    try:
        tunnels = json.loads(output)
        for tunnel in tunnels:
            if tunnel.get("name") == tunnel_name:
                return tunnel.get("id")
    except json.JSONDecodeError:
        pass
    return None


def create_tunnel(tunnel_name):
    """Create a new tunnel and return its ID."""
    print(f"Creating tunnel '{tunnel_name}'...")
    output, rc = run_cmd(f"cloudflared tunnel create {tunnel_name}", check=False)
    if rc != 0 or not output:
        print(f"Tunnel creation failed: {output}")
        return None
    
    # Output: "Created tunnel <tunnel_id> with name <tunnel_name>"
    match = re.search(r"Created tunnel\s+([a-f0-9-]+)\s+with name", output or "")
    if match:
        return match.group(1)
    
    # Fallback: try to get it from list
    return get_tunnel_id(tunnel_name)


def configure_dns(subdomain, domain, tunnel_id, tunnel_name):
    """Create CNAME record pointing subdomain to tunnel."""
    full_domain = f"{subdomain}.{domain}"
    print(f"Configuring DNS: {full_domain} -> tunnel {tunnel_name}")
    
    # Delete existing CNAME if any
    run_cmd(f"cloudflared tunnel route dns {tunnel_id} {full_domain}", check=False)
    
    # Verify DNS was set
    time.sleep(1)
    output, _ = run_cmd(f"dig +short CNAME {full_domain}", check=False)
    if output and tunnel_name in output:
        print(f"✅ DNS configured: {full_domain}")
    else:
        print(f"⚠️  DNS may not be configured. Check Cloudflare dashboard.")


def start_tunnel(tunnel_name, tunnel_id, port):
    """Start the tunnel."""
    print(f"Starting tunnel '{tunnel_name}' (ID: {tunnel_id})...")
    
    proc = subprocess.Popen(
        ["cloudflared", "tunnel", "run", "--token", tunnel_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    
    # Wait for ready signal
    ready = False
    if proc.stdout:
        for line in iter(proc.stdout.readline, ""):
            print(line.rstrip(), flush=True)
            if "started" in line.lower() or "running" in line.lower():
                ready = True
                break
    
    if not ready:
        print("⚠️  Tunnel may not have started properly")
    
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
    parser.add_argument(
        "--no-dns",
        action="store_true",
        help="Skip DNS configuration",
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
    
    # Check cloudflared
    _, rc = run_cmd("cloudflared --version", check=False)
    if rc != 0:
        print("❌ cloudflared not found!")
        print("Install: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        sys.exit(1)
    print("✅ cloudflared installed")
    
    # Get or create tunnel
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
    
    # Configure DNS
    if not args.no_dns:
        configure_dns(args.subdomain, args.domain, tunnel_id, tunnel_name)
    else:
        print("Skipping DNS configuration")
    
    # Start tunnel
    print()
    print("🚀 Starting tunnel...")
    proc = start_tunnel(tunnel_name, tunnel_id, args.port)
    
    print()
    print("=" * 60)
    print("✅ Tunnel is running!")
    print()
    print(f"🌐 Your test server is accessible at: https://{full_domain}")
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
