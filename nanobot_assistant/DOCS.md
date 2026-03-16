# Nanobot — AI Assistant for Raspberry Pi

Ultra-lightweight AI assistant (~100 MB RAM) built for Raspberry Pi and low-power devices. Works with any OpenAI-compatible LLM provider.

## Getting Started

1. Install the add-on from the repository
2. Start the add-on
3. Edit `/config/nanobot/config.json` (via File Editor, VS Code Server, or Ansible)
4. Set your LLM provider, API key, Telegram token, MCP servers
5. Restart the add-on

## Add-on Options

Since v0.1.28, add-on options are minimal — just paths and basic flags.
All actual configuration lives in `config.json`.

| Option | Description |
|--------|-------------|
| `CONFIG_PATH` | Path to nanobot config directory (default: `/config/nanobot`) |
| `DATA_PATH` | Path to nanobot data directory (default: `/data/nanobot`) |
| `ha_config_access` | Allow bot to read/edit HA config files |
| `timezone` | Timezone (e.g. `Europe/Kiev`) |
| `secrets` | List of key-value pairs for secret substitution (see below) |

## Secrets

Secrets allow you to keep API keys and tokens out of config.json.
Add secrets in **Settings → Add-ons → Nanobot → Configuration → secrets**:

| Name | Value |
|------|-------|
| `ZHIPU_API_KEY` | `fd40870a...` |
| `TELEGRAM_TOKEN` | `77277567...` |
| `HA_MCP_TOKEN` | `eyJhbG...` |
| `GROQ_API_KEY` | `gsk_...` |

Then use `${SECRET_NAME}` placeholders in config.json:

```json
"apiKey": "${ZHIPU_API_KEY}",
"token": "${TELEGRAM_TOKEN}"
```

On every restart, the addon resolves placeholders → `config.runtime.json` (used by nanobot).
The template `config.json` keeps placeholders — safe for git, Ansible, sharing.

## Configuration (config.json)

All settings are in `/config/nanobot/config.json`. Edit it with File Editor,
VS Code Server addon, or deploy via Ansible.

**On first install**, a default config.json is created automatically.
**On restart**, the addon resolves `${SECRET}` placeholders but NEVER changes your config.json structure.

### Example config.json

```json
{
  "providers": {
    "zhipu": {
      "apiKey": "your-api-key",
      "apiBase": "https://open.bigmodel.cn/api/coding/paas/v4"
    }
  },
  "agents": {
    "defaults": {
      "model": "zai/glm-4-flash",
      "workspace": "/config/nanobot/workspace",
      "maxTokens": 8192,
      "temperature": 0.7
    },
    "profiles": {}
  },
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "bot-token-from-botfather",
      "allowFrom": ["123456789"]
    }
  },
  "tools": {
    "mcpServers": {
      "homeassistant": {
        "command": "/opt/nanobot-venv/bin/mcp-proxy",
        "args": ["--transport=streamablehttp", "--stateless", "https://your-ha.example.com/api/mcp"],
        "env": {
          "API_ACCESS_TOKEN": "your-ha-long-lived-token"
        }
      }
    }
  },
  "gateway": {
    "host": "0.0.0.0",
    "port": 18790
  }
}
```

## Home Assistant MCP

The bot can control Home Assistant via the Model Context Protocol (MCP).

### Setup

1. **Install MCP integration in HA:**
   Settings → Devices & Services → Add Integration → **Model Context Protocol Server**

2. **Create a Long-Lived Access Token:**
   HA Profile (bottom-left) → Security → Long-Lived Access Tokens → Create Token

3. **Add MCP server to config.json** (`tools.mcpServers.homeassistant`):

```json
"homeassistant": {
  "command": "/opt/nanobot-venv/bin/mcp-proxy",
  "args": [
    "--transport=streamablehttp",
    "--stateless",
    "https://your-ha-url/api/mcp"
  ],
  "env": {
    "API_ACCESS_TOKEN": "your-long-lived-token"
  }
}
```

### MCP URL — which URL to use?

The addon runs with `host_network: true`, so Docker DNS names like `homeassistant` are NOT available.

| Setup | URL to use |
|-------|-----------|
| HA with SSL via NPM/Cloudflare | `https://your-domain.com/api/mcp` |
| HA with SSL (built-in) | `https://10.0.x.x:443/api/mcp` (add `--insecure` to args if self-signed) |
| HA without SSL | `http://10.0.x.x:8123/api/mcp` |

> **Do NOT use** `http://localhost:8123/api/mcp` if HA is configured with `server_port: 443` or SSL.
> **Do NOT use** `http://homeassistant:8123/api/mcp` — Docker DNS doesn't work with host_network.

### Capabilities

Once connected, the bot can:
- Toggle lights, switches, climate, covers
- Read sensor states and attributes
- Run automations and scripts
- Call any HA service
- Query entity history

## Adding Custom MCP Servers

Add any MCP server to `tools.mcpServers` in config.json:

```json
"my-server": {
  "command": "/usr/bin/npx",
  "args": ["-y", "some-mcp-package"],
  "env": {
    "API_KEY": "key"
  }
}
```

Restart the addon after changes. All MCP servers in config.json are preserved — the addon never removes them.

## Exchange MCP (Email & Calendar)

```json
"exchange": {
  "command": "/opt/nanobot-venv/bin/ews-mcp-server",
  "args": [],
  "env": {
    "EWS_SERVER_URL": "https://mail.company.com",
    "EWS_EMAIL": "you@company.com",
    "EWS_AUTH_TYPE": "ntlm",
    "EWS_USERNAME": "you@company.com",
    "EWS_PASSWORD": "password",
    "TIMEZONE": "Europe/Kiev"
  }
}
```

Gives the bot access to email, calendar, contacts, and tasks via Exchange Web Services.

## Supported LLM Providers

| Provider | Key in config | Example Model | Notes |
|----------|--------------|---------------|-------|
| Zhipu AI | `zhipu` | `zai/glm-4-flash` | Default. Cheapest for smart home |
| OpenRouter | `openrouter` | `anthropic/claude-sonnet-4` | 100+ models |
| OpenAI | `openai` | `gpt-4o` | GPT models |
| Anthropic | `anthropic` | `claude-sonnet-4-5` | Direct API |
| DeepSeek | `deepseek` | `deepseek-chat` | Budget-friendly |
| Gemini | `gemini` | `gemini-2.5-flash` | Google models |
| Ollama | `vllm` | any local model | No API costs |

Set `provider`, `apiKey`, `apiBase` in `providers` section of config.json.

## System Prompt

Two ways to set a custom system prompt:

1. **File** — create `/config/nanobot/system_prompt.txt` (loaded as IDENTITY.md)
2. **In config.json** — not directly supported; use the file method

## User Files

All files at `/config/nanobot/` (editable via File Editor / VS Code Server):

- `config.json` — main configuration
- `system_prompt.txt` — custom system prompt (optional)
- `skills/` — custom bot skills
- `workspace/` — agent working directory, memory
- `gateway.log` — gateway log

## Migration from v0.1.27

If upgrading from v0.1.27 (old options format with llm/telegram/mcp sections):
- The addon automatically migrates old HA options into config.json (one-time)
- After migration, old options are ignored
- Set new simple options (CONFIG_PATH, DATA_PATH) and save

## Troubleshooting

**Bot not responding:**
- Check API key in config.json (`providers.<name>.apiKey`)
- Check add-on logs

**MCP not connecting (401 Unauthorized):**
- Verify Long-Lived Access Token is valid
- Check URL is correct for your network setup (see MCP URL table above)
- Make sure MCP Server integration is installed in HA

**MCP not connecting (Connection refused):**
- Don't use `localhost` or `homeassistant` hostname — use IP or external domain
- Check HA port (443 if SSL, 8123 if not)

**Telegram not working:**
- Check bot token in config.json
- Verify User ID in `allowFrom`
