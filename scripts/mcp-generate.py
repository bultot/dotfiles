#!/usr/bin/env python3
"""Generate Claude Code and Claude Desktop MCP configs from mcp-registry.yaml.

Reads the MCP server registry and produces chezmoi template files:
- home/dot_claude/settings.json.tmpl (Claude Code)
- home/private_Library/private_Application Support/Claude/modify_claude_desktop_config.json (Claude Desktop)

Usage:
    python3 mcp-generate.py                        # auto-detect scope from cwd
    python3 mcp-generate.py --scope personal       # explicit scope
    python3 mcp-generate.py --scope universal --dry-run  # preview output
"""

import argparse
import json
import os
import sys
from pathlib import Path

import yaml

# Maps ${VAR_NAME} references in the registry to chezmoi onepasswordRead calls.
# The generator replaces these in the output templates so chezmoi resolves secrets at apply time.
#
# Two-phase approach: during JSON construction, we insert PLACEHOLDER tokens (no double quotes).
# After json.dumps serialization, we replace placeholders with actual Go template expressions.
# This avoids json.dumps escaping the double quotes inside {{ onepasswordRead "..." }}.
CHEZMOI_SECRET_MAP = {
    "${STITCH_API_KEY}": "CHEZMOI_PLACEHOLDER_STITCH_API_KEY",
    "${SANITY_AUTH_TOKEN}": "CHEZMOI_PLACEHOLDER_SANITY_AUTH_TOKEN",
}

# Post-serialization replacements: placeholder -> actual Go template expression.
# The replacement includes wrapping double quotes so the result is valid JSON after
# chezmoi template resolution (onepasswordRead returns a raw string).
CHEZMOI_SECRET_RESOLVE = {
    '"CHEZMOI_PLACEHOLDER_STITCH_API_KEY"': '"{{ onepasswordRead "op://Integrations/stitch-api-key/credential" }}"',
    '"CHEZMOI_PLACEHOLDER_SANITY_AUTH_TOKEN"': '"{{ onepasswordRead "op://Integrations/sanity-cms/credential" }}"',
}

# Resolve ${HOME} to the actual home directory for chezmoi templates.
# chezmoi templates run on the target machine, so we use the literal path.
HOME_DIR = os.path.expanduser("~")


def load_registry(path: Path) -> dict:
    """Load and validate mcp-registry.yaml."""
    with open(path) as f:
        data = yaml.safe_load(f)
    if data.get("version") != 1:
        print(f"Error: unsupported registry version: {data.get('version')}", file=sys.stderr)
        sys.exit(1)
    return data


def detect_scope(registry: dict) -> str:
    """Auto-detect scope from current working directory using registry scope_paths."""
    cwd = os.getcwd()
    scope_paths = registry.get("defaults", {}).get("scope_paths", {})
    for scope_name, path_template in scope_paths.items():
        expanded = path_template.replace("${HOME}", HOME_DIR)
        if cwd.startswith(expanded):
            return scope_name
    return "universal"


def filter_servers(servers: dict, scope: str, client: str) -> dict:
    """Filter servers by scope and client target. Skips cloud connectors."""
    result = {}
    for name, config in servers.items():
        if config.get("managed") == "cloud":
            continue
        server_scopes = config.get("scope", ["universal"])
        server_clients = config.get("client", [])
        if client not in server_clients:
            continue
        if "universal" in server_scopes or scope in server_scopes:
            result[name] = config
    return result


def resolve_variables(value: str, mcp_host: str) -> str:
    """Replace variable references in a string value.

    Handles ${MCP_HOST}, ${HOME}, and secret variables from CHEZMOI_SECRET_MAP.
    """
    result = value
    # Replace secrets first (before ${HOME} which might match partial patterns)
    for var_ref, chezmoi_call in CHEZMOI_SECRET_MAP.items():
        result = result.replace(var_ref, chezmoi_call)
    # Replace ${MCP_HOST} with the literal default value (not secret)
    result = result.replace("${MCP_HOST}", mcp_host)
    # Replace ${HOME} with the actual home directory
    result = result.replace("${HOME}", HOME_DIR)
    return result


def generate_claude_code_entry(name: str, config: dict, mcp_host: str) -> dict:
    """Generate a single mcpServers entry for Claude Code settings.json."""
    if config["transport"] == "http":
        entry = {
            "type": "url",
            "url": resolve_variables(config["url"], mcp_host),
        }
        if config.get("headers"):
            resolved_headers = {}
            for key, val in config["headers"].items():
                resolved_headers[key] = resolve_variables(val, mcp_host)
            entry["headers"] = resolved_headers
        return entry
    elif config["transport"] == "stdio":
        command = resolve_variables(config["command"], mcp_host)
        args = [resolve_variables(a, mcp_host) for a in config.get("args", [])]
        entry = {"command": command, "args": args}
        if config.get("env"):
            resolved_env = {}
            for key, val in config["env"].items():
                resolved_env[key] = resolve_variables(val, mcp_host)
            entry["env"] = resolved_env
        return entry
    return {}


def generate_claude_desktop_entry(
    name: str, config: dict, mcp_host: str, mcp_remote_version: str
) -> dict:
    """Generate a single mcpServers entry for Claude Desktop."""
    if config["transport"] == "http":
        url = resolve_variables(config["url"], mcp_host)
        args = [f"mcp-remote@{mcp_remote_version}", url]
        if config.get("headers"):
            for key, val in config["headers"].items():
                args.extend(["--header", f"{key}: {resolve_variables(val, mcp_host)}"])
        return {"command": "npx", "args": args}
    elif config["transport"] == "stdio":
        command = resolve_variables(config["command"], mcp_host)
        args = [resolve_variables(a, mcp_host) for a in config.get("args", [])]
        entry = {"command": command, "args": args}
        if config.get("env"):
            resolved_env = {}
            for key, val in config["env"].items():
                resolved_env[key] = resolve_variables(val, mcp_host)
            entry["env"] = resolved_env
        return entry
    return {}


def generate_settings_json(
    servers: dict, mcp_host: str, base_template_path: Path, output_path: Path, dry_run: bool
) -> int:
    """Generate Claude Code settings.json.tmpl from base template and registry servers."""
    # Build mcpServers object
    mcp_servers = {}
    for name, config in servers.items():
        mcp_servers[name] = generate_claude_code_entry(name, config, mcp_host)

    # Serialize the mcpServers object with 4-space indent
    mcp_json = json.dumps(mcp_servers, indent=4)

    # Post-serialization: replace placeholder tokens with actual Go template expressions.
    # This must happen after json.dumps to avoid double-quote escaping.
    for placeholder, template_expr in CHEZMOI_SECRET_RESOLVE.items():
        mcp_json = mcp_json.replace(placeholder, template_expr)

    # Read the base template
    base_content = base_template_path.read_text()

    # Replace %%MCP_SERVERS%% with the generated JSON.
    # The placeholder sits at 2-space indent ("mcpServers": %%MCP_SERVERS%%),
    # so we need to re-indent the JSON block to align with the surrounding structure.
    # The top-level braces of the mcpServers object should be at the same position.
    lines = mcp_json.split("\n")
    # First line (opening brace) has no extra indent needed; subsequent lines get 2 spaces
    indented_lines = [lines[0]] + ["  " + line for line in lines[1:]]
    indented_mcp_json = "\n".join(indented_lines)

    output = base_content.replace("%%MCP_SERVERS%%", indented_mcp_json)

    if dry_run:
        print("=== Claude Code settings.json.tmpl (dry run) ===")
        print(output[:500])
        print("... (truncated)")
    else:
        output_path.write_text(output)

    return len(mcp_servers)


def generate_desktop_config(
    servers: dict, mcp_host: str, mcp_remote_version: str, output_path: Path, dry_run: bool
) -> int:
    """Generate Claude Desktop modify script from registry servers.

    Produces a modify_*.json.tmpl file. chezmoi processes Go template expressions
    first (resolving onepasswordRead for secrets), then executes the result as a
    modify script that merges mcpServers into the existing Claude Desktop config.
    """
    # Build mcpServers object for Claude Desktop
    mcp_servers = {}
    for name, config in servers.items():
        mcp_servers[name] = generate_claude_desktop_entry(
            name, config, mcp_host, mcp_remote_version
        )

    # Serialize JSON, apply secret placeholder resolution.
    mcp_json_str = json.dumps(mcp_servers, indent=2)

    # Post-serialization: replace placeholder tokens with actual Go template expressions
    for placeholder, template_expr in CHEZMOI_SECRET_RESOLVE.items():
        mcp_json_str = mcp_json_str.replace(placeholder, template_expr)

    # The .tmpl extension tells chezmoi to process Go template expressions first,
    # resolving {{ onepasswordRead ... }} calls to actual secret values.
    # The resulting script then executes as a chezmoi modify script.
    #
    # We write a pure Python script (#!/usr/bin/env python3) that reads current config
    # from stdin and outputs the merged config. The MCP servers JSON is embedded as a
    # multi-line string using triple quotes, which avoids shell quoting issues entirely.
    #
    # After chezmoi template processing, the Go template expressions become literal values
    # inside the Python triple-quoted string, which Python handles correctly.
    modify_script = f"""#!/usr/bin/env python3
# modify_claude_desktop_config.json.tmpl
# Generated by mcp-generate.py - do not edit manually
# chezmoi processes Go templates first (resolves secrets), then runs as modify script
# Merges MCP servers into existing Claude Desktop config, preserving preferences

import json
import sys

MCP_SERVERS_JSON = \"\"\"
{mcp_json_str}
\"\"\"

try:
    current = json.load(sys.stdin)
except (json.JSONDecodeError, ValueError):
    current = {{}}

new_servers = json.loads(MCP_SERVERS_JSON)
current["mcpServers"] = new_servers
print(json.dumps(current, indent=2))
"""

    if dry_run:
        print("=== Claude Desktop modify script (dry run) ===")
        print(modify_script[:500])
        print("... (truncated)")
    else:
        output_path.write_text(modify_script)
        output_path.chmod(0o755)

    return len(mcp_servers)


def main():
    parser = argparse.ArgumentParser(
        description="Generate MCP configs from mcp-registry.yaml"
    )
    parser.add_argument(
        "--scope",
        choices=["universal", "personal", "backbase"],
        help="Scope filter (default: auto-detect from cwd)",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=None,
        help="Path to mcp-registry.yaml (default: ../mcp-registry.yaml relative to script)",
    )
    parser.add_argument(
        "--chezmoi-root",
        type=Path,
        default=None,
        help="Path to chezmoi source root (default: parent of script dir)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview output without writing files",
    )
    args = parser.parse_args()

    # Resolve paths
    script_dir = Path(__file__).resolve().parent
    chezmoi_root = args.chezmoi_root or script_dir.parent
    registry_path = args.registry or chezmoi_root / "mcp-registry.yaml"

    if not registry_path.exists():
        print(f"Error: registry not found at {registry_path}", file=sys.stderr)
        sys.exit(1)

    # Load registry
    registry = load_registry(registry_path)
    mcp_host = registry.get("defaults", {}).get("mcp_host", "http://mcp.bultot.nl")
    mcp_remote_version = registry.get("defaults", {}).get("mcp_remote_version", "0.1.38")
    servers = registry.get("servers", {})

    # Determine scope
    scope = args.scope or detect_scope(registry)
    print(f"Scope: {scope}")

    # Filter servers for Claude Code
    cc_servers = filter_servers(servers, scope, "claude-code")

    # Warn if more than 5 servers (soft guideline per D-07)
    if len(cc_servers) > 5:
        print(f"Warning: {len(cc_servers)} servers for Claude Code (guideline suggests <= 5)")

    # Filter servers for Claude Desktop (universal scope only)
    cd_servers = filter_servers(servers, "universal", "claude-desktop")

    # Generate Claude Code settings.json.tmpl
    base_template = chezmoi_root / "home" / "dot_claude" / "settings-base.json.tmpl"
    settings_output = chezmoi_root / "home" / "dot_claude" / "settings.json.tmpl"

    if not base_template.exists():
        print(f"Error: base template not found at {base_template}", file=sys.stderr)
        sys.exit(1)

    cc_count = generate_settings_json(
        cc_servers, mcp_host, base_template, settings_output, args.dry_run
    )

    # Generate Claude Desktop modify script (.tmpl so chezmoi resolves secrets first)
    desktop_output = (
        chezmoi_root
        / "home"
        / "private_Library"
        / "private_Application Support"
        / "Claude"
        / "modify_claude_desktop_config.json.tmpl"
    )

    cd_count = generate_desktop_config(
        cd_servers, mcp_host, mcp_remote_version, desktop_output, args.dry_run
    )

    # Summary
    action = "would write" if args.dry_run else "written"
    print(f"Generated Claude Code settings: {cc_count} MCP servers (scope: {scope})")
    print(f"Generated Claude Desktop config: {cd_count} MCP servers (universal stdio only)")
    print(f"Files {action}:")
    print(f"  home/dot_claude/settings.json.tmpl")
    print(f"  home/private_Library/private_Application Support/Claude/modify_claude_desktop_config.json.tmpl")


if __name__ == "__main__":
    main()
