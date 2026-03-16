#!/usr/bin/env python3
"""Bootstrap nanobot config.json if it doesn't exist.

Since v0.1.28, addon options only define paths (CONFIG_PATH, DATA_PATH).
All actual configuration lives in config.json, managed externally
(Ansible, File Editor, Web UI, or manually via SSH).

This script:
- Creates a default config.json ONLY if none exists (first install)
- Migrates old-format HA options (llm, telegram, etc.) into config.json (one-time)
- NEVER overwrites an existing config.json
"""

import json
import os

OPTIONS_FILE = "/data/options.json"

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
    if not os.path.exists(OPTIONS_FILE):
        return {}
    with open(OPTIONS_FILE, "r") as f:
        return json.load(f)


def is_old_options_format(opts):
    """Detect old options format (pre-0.1.28) with nested config sections."""
    return "llm" in opts or "telegram" in opts or "homeassistant_mcp" in opts


def create_default_config(nanobot_home):
    """Baseline config template for first install."""
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
                "workspace": os.path.join(nanobot_home, "workspace"),
                "maxTokens": 8192,
                "temperature": 0.7,
                "maxToolIterations": 20,
                "memoryWindow": 50,
            },
            "profiles": {},
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


def migrate_old_options(opts, config, nanobot_home):
    """One-time migration: old HA addon options → config.json fields.

    Called only when old-format options are detected AND config.json
    doesn't have the corresponding values yet.
    """
    print("[INFO] Migrating old-format addon options into config.json...")

    # LLM
    llm = opts.get("llm", {})
    provider = llm.get("provider", "").strip()
    api_key = llm.get("api_key", "").strip()
    model = llm.get("model", "").strip()
    api_base = llm.get("api_base", "").strip() or PROVIDER_BASES.get(provider, "")

    if provider and api_key:
        config["providers"] = {provider: {"apiKey": api_key, "apiBase": api_base}}
    if model:
        config.setdefault("agents", {}).setdefault("defaults", {})["model"] = model

    # Telegram
    tg = opts.get("telegram", {})
    if tg.get("enabled") and tg.get("token", "").strip():
        tg_config = {"enabled": True, "token": tg["token"].strip()}
        allow_from = [x.strip() for x in tg.get("allow_from", []) if x.strip()]
        if allow_from:
            tg_config["allowFrom"] = allow_from
        config.setdefault("channels", {})["telegram"] = tg_config

    # HA MCP
    mcp = opts.get("homeassistant_mcp", {})
    if mcp.get("enabled") and mcp.get("token", "").strip():
        url = mcp.get("url", "").strip() or "http://localhost:8123/api/mcp"
        config.setdefault("tools", {}).setdefault("mcpServers", {})["homeassistant"] = {
            "command": "/opt/nanobot-venv/bin/mcp-proxy",
            "args": ["--transport=streamablehttp", "--stateless", url],
            "env": {"API_ACCESS_TOKEN": mcp["token"].strip()},
        }

    # Exchange MCP
    exchange = opts.get("exchange_mcp", {})
    if (exchange.get("enabled") and exchange.get("server_url", "").strip()
            and exchange.get("username", "").strip() and exchange.get("password", "").strip()):
        tz = opts.get("advanced", {}).get("timezone", "UTC")
        config.setdefault("tools", {}).setdefault("mcpServers", {})["exchange"] = {
            "command": "/opt/nanobot-venv/bin/ews-mcp-server",
            "args": [],
            "env": {
                "EWS_SERVER_URL": exchange["server_url"].strip(),
                "EWS_EMAIL": exchange.get("email", "").strip(),
                "EWS_AUTH_TYPE": exchange.get("auth_type", "ntlm").strip(),
                "EWS_USERNAME": exchange["username"].strip(),
                "EWS_PASSWORD": exchange["password"].strip(),
                "TIMEZONE": tz,
            },
        }

    # Advanced
    advanced = opts.get("advanced", {})
    defaults = config.setdefault("agents", {}).setdefault("defaults", {})
    if advanced.get("max_tokens") is not None:
        defaults["maxTokens"] = int(advanced["max_tokens"])
    if advanced.get("temperature") is not None:
        defaults["temperature"] = float(advanced["temperature"])

    # System prompt → IDENTITY.md
    ha_prompt = advanced.get("system_prompt", "").strip()
    if not ha_prompt:
        prompt_file = os.path.join(nanobot_home, "system_prompt.txt")
        if os.path.exists(prompt_file):
            try:
                ha_prompt = open(prompt_file).read().strip()
            except OSError:
                pass
    if ha_prompt:
        workspace = defaults.get("workspace", os.path.join(nanobot_home, "workspace"))
        identity_file = os.path.join(workspace, "IDENTITY.md")
        try:
            os.makedirs(workspace, exist_ok=True)
            with open(identity_file, "w") as f:
                f.write(ha_prompt)
            print(f"[INFO] System prompt written to {identity_file}")
        except OSError as e:
            print(f"[WARN] Could not write {identity_file}: {e}")

    # Remove legacy systemPrompt from defaults
    defaults.pop("systemPrompt", None)

    print("[INFO] Migration complete.")


def migrate_agents_to_profiles(config):
    """Migrate old-format named agents to agents.profiles."""
    agents = config.get("agents", {})
    profiles = agents.setdefault("profiles", {})
    defaults_keys = {"defaults", "profiles"}

    for key in list(agents.keys()):
        if key in defaults_keys:
            continue
        old_agent = agents.pop(key)
        profile_entry = {}
        sp = old_agent.get("systemPrompt") or old_agent.get("system_prompt")
        if sp:
            profile_entry["systemPrompt"] = sp
        model = old_agent.get("model")
        if model:
            profile_entry["model"] = model
        if profile_entry and key not in profiles:
            profiles[key] = profile_entry
            print(f"[INFO] Migrated agent '{key}' → agents.profiles.{key}")

    agents.get("defaults", {}).pop("systemPrompt", None)


def main():
    os.environ["HOME"] = "/data"

    opts = load_options()
    nanobot_home = opts.get("CONFIG_PATH", "/config/nanobot")
    config_file = os.path.join(nanobot_home, "config.json")

    # Create directories
    os.makedirs(nanobot_home, exist_ok=True)
    os.makedirs(os.path.join(nanobot_home, "workspace"), exist_ok=True)
    os.makedirs(os.path.join(nanobot_home, "skills"), exist_ok=True)

    if os.path.exists(config_file):
        print(f"[INFO] Config exists at {config_file} — preserving.")

        # One-time migration from old options format
        if is_old_options_format(opts):
            try:
                with open(config_file, "r") as f:
                    config = json.load(f)
                migrate_old_options(opts, config, nanobot_home)
                migrate_agents_to_profiles(config)
                config.pop("timezone", None)
                with open(config_file, "w") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                print("[INFO] Old-format options migrated into config.json (one-time)")
            except (json.JSONDecodeError, OSError) as e:
                print(f"[WARN] Migration failed: {e}")
    else:
        # First install — create default config
        config = create_default_config(nanobot_home)

        # If old-format options exist, apply them
        if is_old_options_format(opts):
            migrate_old_options(opts, config, nanobot_home)

        migrate_agents_to_profiles(config)
        config.pop("timezone", None)

        with open(config_file, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"[INFO] Default config created at {config_file}")
        print("[INFO] Edit config.json to add LLM keys, MCP servers, Telegram, etc.")

    print(f"[INFO] Config path: {config_file}")


if __name__ == "__main__":
    main()
