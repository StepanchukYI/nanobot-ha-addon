#!/usr/bin/env python3
"""Generate / update nanobot config.json from HA addon options.

On every restart the script merges HA UI options into config.json.
Manual edits to config.json are preserved — HA options only override
the fields that the user changed in the HA Settings panel.
"""

import json
import os
import copy

OPTIONS_FILE = "/data/options.json"
NANOBOT_HOME = "/config/nanobot"
CONFIG_FILE = os.path.join(NANOBOT_HOME, "config.json")

# Provider presets: apiBase URLs for known providers
PROVIDER_BASES = {
    "zhipu":      "https://open.bigmodel.cn/api/coding/paas/v4",
    "openrouter": "https://openrouter.ai/api/v1",
    "openai":     "https://api.openai.com/v1",
    "anthropic":  "https://api.anthropic.com",
    "deepseek":   "https://api.deepseek.com/v1",
    "gemini":     "https://generativelanguage.googleapis.com/v1beta/openai",
    "vllm":       "http://localhost:11434/v1",
}


def load_options():
    """Load HA addon options (nested: llm, telegram, homeassistant_mcp, advanced)."""
    if not os.path.exists(OPTIONS_FILE):
        return {}
    with open(OPTIONS_FILE, "r") as f:
        return json.load(f)


def load_existing_config():
    """Load existing config.json if present."""
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def create_default_config():
    """Baseline config template."""
    return {
        "providers": {
            "zhipu": {
                "apiKey": "",
                "apiBase": "https://open.bigmodel.cn/api/coding/paas/v4",
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
            "mcpServers": {},
        },
        "gateway": {
            "host": "0.0.0.0",
            "port": 18790,
        },
    }


def apply_llm_options(config, llm):
    """Apply LLM section from HA options."""
    provider = llm.get("provider", "").strip()
    api_key = llm.get("api_key", "").strip()
    model = llm.get("model", "").strip()
    api_base = llm.get("api_base", "").strip()

    if not provider:
        return

    # Determine apiBase: explicit value > preset > keep existing
    if not api_base:
        api_base = PROVIDER_BASES.get(provider, "")

    # Build provider entry
    provider_entry = {}
    if api_key:
        provider_entry["apiKey"] = api_key
    if api_base:
        provider_entry["apiBase"] = api_base

    # Replace providers section with the configured one
    if api_key:
        config["providers"] = {provider: provider_entry}
    elif provider in config.get("providers", {}):
        # Update apiBase even without key change
        if api_base:
            config["providers"][provider]["apiBase"] = api_base

    # Update model
    if model:
        config.setdefault("agents", {}).setdefault("defaults", {})["model"] = model


def apply_telegram_options(config, telegram):
    """Apply Telegram section from HA options."""
    enabled = telegram.get("enabled", False)
    token = telegram.get("token", "").strip()
    allow_from = telegram.get("allow_from", [])

    # Clean up empty strings from allow_from
    allow_from = [x.strip() for x in allow_from if x.strip()]

    if enabled and token:
        existing_tg = config.get("channels", {}).get("telegram", {})
        tg_config = {
            "enabled": True,
            "token": token,
        }
        # Preserve existing allowFrom if HA UI list is empty
        if allow_from:
            tg_config["allowFrom"] = allow_from
        elif existing_tg.get("allowFrom"):
            tg_config["allowFrom"] = existing_tg["allowFrom"]

        config.setdefault("channels", {})["telegram"] = tg_config
    else:
        # Remove telegram if disabled or no token
        config.setdefault("channels", {}).pop("telegram", None)


def apply_mcp_options(config, mcp):
    """Apply Home Assistant MCP section from HA options.

    Uses mcp-proxy as a stdio-to-Streamable-HTTP bridge.
    nanobot connects to mcp-proxy via stdio, mcp-proxy connects to HA via HTTP.
    This avoids protocol-level incompatibilities with direct Streamable HTTP.
    """
    enabled = mcp.get("enabled", False)
    url = mcp.get("url", "").strip()
    token = mcp.get("token", "").strip()

    tools = config.setdefault("tools", {})
    servers = tools.setdefault("mcpServers", {})

    if enabled and token:
        mcp_url = url or "http://localhost:8123/api/mcp"
        servers["homeassistant"] = {
            "command": "/opt/nanobot-venv/bin/mcp-proxy",
            "args": [
                "--transport=streamablehttp",
                "--stateless",
                mcp_url,
            ],
            "env": {
                "API_ACCESS_TOKEN": token,
            },
        }
    else:
        # Remove MCP if disabled or no token (prevents crash on placeholder)
        servers.pop("homeassistant", None)


def load_system_prompt(ha_prompt: str) -> str:
    """Load system prompt: HA settings field > file > empty.

    Priority:
      1. HA settings field (if non-empty)
      2. /config/nanobot/system_prompt.txt (editable via File Editor)
    """
    if ha_prompt:
        return ha_prompt

    prompt_file = os.path.join(NANOBOT_HOME, "system_prompt.txt")
    if os.path.exists(prompt_file):
        try:
            with open(prompt_file, "r") as f:
                content = f.read().strip()
            if content:
                print(f"[INFO] System prompt loaded from {prompt_file}")
                return content
        except OSError:
            pass
    return ""


def apply_advanced_options(config, advanced):
    """Apply Advanced section from HA options (timezone handled by run.sh)."""
    ha_prompt = advanced.get("system_prompt", "").strip()
    max_tokens = advanced.get("max_tokens")
    temperature = advanced.get("temperature")

    defaults = config.setdefault("agents", {}).setdefault("defaults", {})

    system_prompt = load_system_prompt(ha_prompt)
    if system_prompt:
        defaults["systemPrompt"] = system_prompt

    if max_tokens is not None:
        defaults["maxTokens"] = int(max_tokens)
    if temperature is not None:
        defaults["temperature"] = float(temperature)


def main():
    os.environ["HOME"] = "/data"
    os.makedirs(NANOBOT_HOME, exist_ok=True)
    os.makedirs(os.path.join(NANOBOT_HOME, "workspace"), exist_ok=True)
    os.makedirs(os.path.join(NANOBOT_HOME, "skills"), exist_ok=True)

    opts = load_options()
    existing = load_existing_config()

    if existing is not None:
        config = existing
        print(f"[INFO] Loaded existing config from {CONFIG_FILE}")
    else:
        config = create_default_config()
        print("[INFO] No config found — creating from defaults.")

    # Merge HA options into config
    if opts.get("llm"):
        apply_llm_options(config, opts["llm"])
    if opts.get("telegram"):
        apply_telegram_options(config, opts["telegram"])
    if opts.get("homeassistant_mcp"):
        apply_mcp_options(config, opts["homeassistant_mcp"])
    if opts.get("advanced"):
        apply_advanced_options(config, opts["advanced"])

    # Ensure workspace path is set
    config.setdefault("agents", {}).setdefault("defaults", {}).setdefault(
        "workspace", os.path.join(NANOBOT_HOME, "workspace")
    )

    # Ensure gateway config
    config.setdefault("gateway", {"host": "0.0.0.0", "port": 18790})

    # Remove fields that nanobot's Pydantic model doesn't accept
    config.pop("timezone", None)

    # Write config
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"[INFO] Config written to {CONFIG_FILE}")


if __name__ == "__main__":
    main()
