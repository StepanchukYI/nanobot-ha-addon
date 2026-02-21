#!/usr/bin/env python3
"""Generate nanobot config.json from Home Assistant add-on options."""

import json
import os
import sys

OPTIONS_FILE = "/data/options.json"
NANOBOT_HOME = "/data/nanobot"
CONFIG_FILE = os.path.join(NANOBOT_HOME, "config.json")


def load_options():
    """Load HA addon options."""
    if not os.path.exists(OPTIONS_FILE):
        print("[ERROR] options.json not found", file=sys.stderr)
        sys.exit(1)
    with open(OPTIONS_FILE, "r") as f:
        return json.load(f)


def build_config(opts):
    """Build nanobot config from HA addon options."""
    config = {
        "providers": {},
        "agents": {
            "defaults": {
                "model": opts.get("llm_model", "zai/glm-4-flash"),
                "workspace": os.path.join(NANOBOT_HOME, "workspace"),
                "maxTokens": 8192,
                "temperature": 0.7,
                "maxToolIterations": 20,
                "memoryWindow": 50,
            }
        },
        "channels": {},
        "tools": {
            "exec": {"timeout": 60},
            "restrictToWorkspace": True,
        },
        "gateway": {
            "host": "0.0.0.0",
            "port": 18790,
        },
    }

    # --- LLM Provider ---
    provider = opts.get("llm_provider", "zhipu")
    api_key = opts.get("llm_api_key", "")
    api_base = opts.get("llm_api_base", "")

    if api_key:
        provider_config = {"apiKey": api_key}
        if api_base:
            provider_config["apiBase"] = api_base
        config["providers"][provider] = provider_config
    else:
        print("[WARN] No LLM API key configured. Bot will not work until key is set.")

    # --- Telegram ---
    if opts.get("telegram_enabled", False):
        token = opts.get("telegram_token", "")
        allow_from = opts.get("telegram_allow_from", [])
        if token:
            config["channels"]["telegram"] = {
                "enabled": True,
                "token": token,
                "allowFrom": allow_from,
            }
        else:
            print("[WARN] Telegram enabled but no token provided.")

    # --- Web Search ---
    search_key = opts.get("web_search_api_key", "")
    if search_key:
        config["tools"]["web"] = {
            "search": {
                "apiKey": search_key,
                "maxResults": 5,
            }
        }

    # --- MCP (Home Assistant) ---
    if opts.get("ha_mcp_enabled", False):
        ha_url = opts.get("ha_mcp_url", "")
        ha_token = opts.get("ha_mcp_token", "")
        if ha_url:
            mcp_config = {"url": ha_url}
            if ha_token:
                mcp_config["headers"] = {
                    "Authorization": f"Bearer {ha_token}"
                }
            config["tools"]["mcpServers"] = {
                "homeassistant": mcp_config
            }
        else:
            print("[WARN] HA MCP enabled but no URL provided.")

    return config


def merge_config(existing, generated):
    """
    Merge generated config into existing, preserving user customizations.
    Only updates keys that come from HA options; leaves extra keys untouched.
    """
    for key, value in generated.items():
        if key in existing and isinstance(existing[key], dict) and isinstance(value, dict):
            merge_config(existing[key], value)
        else:
            existing[key] = value
    return existing


def main():
    opts = load_options()

    # Set HOME for nanobot
    os.environ["HOME"] = "/data"

    # Ensure directories exist
    os.makedirs(NANOBOT_HOME, exist_ok=True)
    os.makedirs(os.path.join(NANOBOT_HOME, "workspace"), exist_ok=True)
    os.makedirs(os.path.join(NANOBOT_HOME, "skills"), exist_ok=True)

    generated = build_config(opts)

    # If config already exists, merge (preserve user edits via terminal)
    if os.path.exists(CONFIG_FILE):
        print("[INFO] Existing config found. Merging HA options...")
        with open(CONFIG_FILE, "r") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                print("[WARN] Existing config is invalid JSON. Overwriting.")
                existing = {}
        config = merge_config(existing, generated)
    else:
        print("[INFO] No existing config. Creating new config from HA options.")
        config = generated

    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"[INFO] Config written to {CONFIG_FILE}")
    print(f"[INFO] Provider: {opts.get('llm_provider', 'zhipu')}")
    print(f"[INFO] Model: {opts.get('llm_model', 'zai/glm-4-flash')}")
    print(f"[INFO] Telegram: {'enabled' if opts.get('telegram_enabled') else 'disabled'}")
    print(f"[INFO] HA MCP: {'enabled' if opts.get('ha_mcp_enabled') else 'disabled'}")


if __name__ == "__main__":
    main()
