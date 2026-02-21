#!/usr/bin/env python3
"""Generate default nanobot config.json on first run only.

All configuration is done by the user via /config/nanobot/config.json
(File Editor, Samba, SSH). This script only creates a starter template
if no config exists yet.
"""

import json
import os
import sys

OPTIONS_FILE = "/data/options.json"
NANOBOT_HOME = "/data/nanobot"
CONFIG_FILE = os.path.join(NANOBOT_HOME, "config.json")


def load_options():
    """Load HA addon options (timezone only)."""
    if not os.path.exists(OPTIONS_FILE):
        return {}
    with open(OPTIONS_FILE, "r") as f:
        return json.load(f)


def create_default_config():
    """Create a starter config template."""
    return {
        "providers": {
            "zhipu": {
                "apiKey": "YOUR_API_KEY_HERE",
                "apiBase": "https://open.bigmodel.cn/api/coding/paas/v4"
            }
        },
        "agents": {
            "defaults": {
                "model": "zai/glm-4-flash",
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
            "mcpServers": {
                "homeassistant": {
                    "url": "http://homeassistant.local.hass.io:8123/api/mcp",
                    "headers": {
                        "Authorization": "Bearer YOUR_HA_TOKEN_HERE"
                    }
                }
            }
        },
        "gateway": {
            "host": "0.0.0.0",
            "port": 18790,
        },
        "timezone": "Europe/Kiev",
    }


def main():
    opts = load_options()

    os.environ["HOME"] = "/data"
    os.makedirs(NANOBOT_HOME, exist_ok=True)
    os.makedirs(os.path.join(NANOBOT_HOME, "workspace"), exist_ok=True)
    os.makedirs(os.path.join(NANOBOT_HOME, "skills"), exist_ok=True)

    if os.path.exists(CONFIG_FILE):
        print(f"[INFO] Config already exists at {CONFIG_FILE} — not overwriting.")
        print("[INFO] Edit via File Editor at /config/nanobot/config.json")
    else:
        print("[INFO] No config found. Creating default template...")
        config = create_default_config()
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Default config written to {CONFIG_FILE}")
        print("[INFO] Edit /config/nanobot/config.json to set your API key and provider.")


if __name__ == "__main__":
    main()
