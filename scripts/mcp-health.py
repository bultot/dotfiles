#!/usr/bin/env python3
"""MCP server health checker.

Reads mcp-registry.yaml and checks each server's health endpoint or command.
Produces clear pass/fail output for quick status checks.

Usage:
    python3 mcp-health.py              # formatted output
    python3 mcp-health.py --json       # machine-readable JSON
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

# ANSI color codes (only used when stdout is a TTY)
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def load_registry() -> dict:
    """Load mcp-registry.yaml from the same directory tree as this script."""
    script_dir = Path(__file__).resolve().parent
    registry_path = script_dir.parent / "mcp-registry.yaml"
    if not registry_path.exists():
        # Fallback: try relative to cwd
        registry_path = Path("mcp-registry.yaml")
    if not registry_path.exists():
        print("Error: mcp-registry.yaml not found", file=sys.stderr)
        sys.exit(2)
    with open(registry_path) as f:
        return yaml.safe_load(f)


def resolve_vars(value: str, mcp_host: str) -> str:
    """Replace ${MCP_HOST} and ${HOME} in health check strings."""
    result = value
    result = result.replace("${MCP_HOST}", mcp_host)
    result = result.replace("${HOME}", os.path.expanduser("~"))
    return result


def check_http(endpoint: str, expect_status: int, timeout: int = 5) -> tuple[bool, str]:
    """Check an HTTP endpoint. Returns (passed, detail_message)."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "--connect-timeout", str(timeout), endpoint],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        status_code = int(result.stdout.strip())
        if status_code == expect_status:
            return True, f"{endpoint} (status {status_code})"
        return False, f"{endpoint} (expected {expect_status}, got {status_code})"
    except subprocess.TimeoutExpired:
        return False, f"{endpoint} (timeout after {timeout}s)"
    except (ValueError, OSError) as e:
        return False, f"{endpoint} (error: {e})"


def check_command(cmd: str, expect_exit: int, timeout: int = 10) -> tuple[bool, str]:
    """Check a health command. Returns (passed, detail_message)."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, timeout=timeout,
        )
        if result.returncode == expect_exit:
            return True, f"{cmd} (exit {result.returncode})"
        return False, f"{cmd} (expected exit {expect_exit}, got {result.returncode})"
    except subprocess.TimeoutExpired:
        return False, f"{cmd} (timeout after {timeout}s)"
    except OSError as e:
        return False, f"{cmd} (error: {e})"


def main():
    parser = argparse.ArgumentParser(description="MCP server health checker")
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output machine-readable JSON",
    )
    args = parser.parse_args()

    registry = load_registry()
    mcp_host = registry.get("defaults", {}).get("mcp_host", "http://mcp.bultot.nl")
    servers = registry.get("servers", {})

    use_color = sys.stdout.isatty() and not args.json_output
    green = GREEN if use_color else ""
    red = RED if use_color else ""
    yellow = YELLOW if use_color else ""
    reset = RESET if use_color else ""

    results = []
    passed = 0
    failed = 0
    skipped = 0
    total_checkable = 0

    for name, config in servers.items():
        # Cloud connectors: skip
        if config.get("managed") == "cloud":
            results.append({
                "name": name,
                "status": "skip",
                "reason": "cloud connector",
                "detail": "",
            })
            skipped += 1
            continue

        health = config.get("health")
        if health is None:
            results.append({
                "name": name,
                "status": "skip",
                "reason": "no health check defined",
                "detail": "",
            })
            skipped += 1
            continue

        total_checkable += 1

        # HTTP health check
        if "endpoint" in health:
            endpoint = resolve_vars(health["endpoint"], mcp_host)
            expect_status = health.get("expect_status", 200)
            ok, detail = check_http(endpoint, expect_status)
        # Command health check
        elif "command" in health:
            cmd = resolve_vars(health["command"], mcp_host)
            expect_exit = health.get("expect_exit", 0)
            ok, detail = check_command(cmd, expect_exit)
        else:
            results.append({
                "name": name,
                "status": "skip",
                "reason": "unknown health check type",
                "detail": "",
            })
            skipped += 1
            continue

        if ok:
            passed += 1
            results.append({
                "name": name,
                "status": "pass",
                "reason": "",
                "detail": detail,
            })
        else:
            failed += 1
            results.append({
                "name": name,
                "status": "fail",
                "reason": "",
                "detail": detail,
            })

    # Output
    if args.json_output:
        output = {
            "results": results,
            "summary": {
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "total_checkable": total_checkable,
            },
        }
        print(json.dumps(output, indent=2))
    else:
        print("MCP Server Health Check")
        print("=" * 24)
        for r in results:
            name_padded = r["name"].ljust(18)
            if r["status"] == "pass":
                print(f"  {green}[PASS]{reset} {name_padded}{r['detail']}")
            elif r["status"] == "fail":
                print(f"  {red}[FAIL]{reset} {name_padded}{r['detail']}")
            elif r["status"] == "skip":
                print(f"  {yellow}[SKIP]{reset} {name_padded}{r['reason']}")
        print()
        print(f"Result: {passed}/{total_checkable} healthy, {failed} failed, {skipped} skipped")

    # Exit 1 if any checkable server failed
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
