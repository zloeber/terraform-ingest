#!/usr/bin/env python3
"""
Validate server.json against the MCP Server JSON Schema.
Uses jsonschema library to validate the server.json file.
"""

import json
import sys
import urllib.request
from pathlib import Path


def validate_server_json():
    """Validate server.json against the MCP registry schema."""

    # Paths
    server_json_path = Path("server.json")

    if not server_json_path.exists():
        print("❌ Error: server.json not found in current directory")
        sys.exit(1)

    # Load server.json
    try:
        with open(server_json_path, "r") as f:
            server_config = json.load(f)
        print("✓ Loaded server.json")
    except json.JSONDecodeError as e:
        print(f"❌ Error: server.json is not valid JSON: {e}")
        sys.exit(1)

    # Fetch the JSON schema
    schema_url = (
        "https://static.modelcontextprotocol.io/schemas/2025-10-17/server.schema.json"
    )
    print(f"Fetching JSON schema from {schema_url}...")

    try:
        with urllib.request.urlopen(schema_url) as response:
            schema = json.loads(response.read().decode())
        print("✓ Fetched schema")
    except Exception as e:
        print(f"❌ Error fetching schema: {e}")
        sys.exit(1)

    # Try to import jsonschema
    try:
        from jsonschema import ValidationError, Draft202012Validator

        print("✓ jsonschema library available")
    except ImportError:
        print("⚠ jsonschema library not found, installing...")
        import subprocess

        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q", "jsonschema"]
        )
        from jsonschema import ValidationError, Draft202012Validator

        print("✓ jsonschema library installed")

    # Validate
    try:
        validator = Draft202012Validator(schema)
        errors = list(validator.iter_errors(server_config))

        if errors:
            print(f"\n❌ Validation failed with {len(errors)} error(s):\n")
            for error in errors:
                print(f"  • {error.message}")
                print(f"    Path: {'.'.join(str(p) for p in error.path) or 'root'}")
                print()
            sys.exit(1)

        print("\n✓ server.json is valid!")

        # Print some basic info
        print("\nServer Configuration:")
        print(f"  Name:        {server_config.get('name', 'N/A')}")
        print(f"  Title:       {server_config.get('title', 'N/A')}")
        print(f"  Version:     {server_config.get('version', 'N/A')}")
        print(f"  Description: {server_config.get('description', 'N/A')}")

        if "packages" in server_config:
            print(f"\nPackages ({len(server_config['packages'])}):")
            for pkg in server_config["packages"]:
                print(
                    f"  • {pkg.get('registryType', 'unknown')}: {pkg.get('identifier', 'unknown')}"
                )

        if "remotes" in server_config:
            print(f"\nRemotes ({len(server_config['remotes'])}):")
            for remote in server_config["remotes"]:
                print(
                    f"  • {remote.get('type', 'unknown')}: {remote.get('url', 'unknown')}"
                )

        sys.exit(0)

    except ValidationError as e:
        print(f"❌ Validation error: {e.message}")
        sys.exit(1)


if __name__ == "__main__":
    validate_server_json()
