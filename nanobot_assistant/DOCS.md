# Nanobot Assistant — Home Assistant Add-on

Ultra-lightweight AI assistant for smart home control. ~4000 lines of code, ~100 MB RAM.

## Getting Started

1. Install the add-on from the repository
2. Start the add-on
3. Open **Settings → Add-ons → Nanobot Assistant → Configuration**
4. Expand the **LLM** section and set your provider, API key, and model
5. Click **Save** and restart the add-on

## Configuration

All settings are configured via the **Configuration** tab in the add-on panel.
Settings are organized into collapsible sections:

### LLM

| Field | Description |
|-------|-------------|
| `provider` | Provider name: `zhipu`, `openrouter`, `openai`, `anthropic`, `deepseek`, `gemini`, `vllm` |
| `api_key` | Your API key for the provider |
| `model` | Model name (e.g. `anthropic/claude-sonnet-4`, `gpt-4o`, `zai/glm-4-flash`) |
| `api_base` | (Optional) Custom API base URL. Auto-filled for known providers |

### Telegram

| Field | Description |
|-------|-------------|
| `enabled` | Enable Telegram bot |
| `token` | Bot token from `@BotFather` |
| `allow_from` | List of allowed Telegram User IDs (get yours from `@userinfobot`) |

### Home Assistant MCP

| Field | Description |
|-------|-------------|
| `enabled` | Enable Home Assistant MCP integration |
| `url` | MCP server URL (default: `http://homeassistant.local.hass.io:8123/api/mcp`) |
| `token` | Long-Lived Access Token (Profile → Long-Lived Access Tokens → Create) |

Requires the **Model Context Protocol Server** integration installed in HA.

### Advanced

| Field | Description |
|-------|-------------|
| `timezone` | Timezone (e.g. `Europe/Kiev`, `America/New_York`) |
| `max_tokens` | Maximum response tokens (default: 8192) |
| `temperature` | LLM temperature 0.0–1.0 (default: 0.7) |

## Supported LLM Providers

| Provider | Key in config | Example Model |
|----------|--------------|---------------|
| OpenRouter | `openrouter` | `anthropic/claude-sonnet-4` |
| OpenAI | `openai` | `gpt-4o` |
| Anthropic | `anthropic` | `claude-sonnet-4-5` |
| DeepSeek | `deepseek` | `deepseek-chat` |
| Zhipu AI | `zhipu` | `zai/glm-4-flash` |
| Gemini | `gemini` | `gemini-2.5-flash` |
| Ollama (local) | `vllm` | any local model |

## User Files

The add-on exposes its working files at `/config/nanobot/`:

- `config.json` — generated nanobot configuration (merged from HA settings)
- `skills/` — custom bot skills
- `workspace/` — agent working directory, memory
- `gateway.log` — gateway log file

You can also edit `config.json` directly via File Editor. Manual changes are preserved
on restart — HA settings override only the fields you change in the UI.

## MCP Servers

Nanobot supports connecting any MCP servers. Add them manually to
`tools.mcpServers` in `/config/nanobot/config.json`.

## Scheduled Tasks (Cron)

You can add tasks via Telegram by sending a message like:

```
Every morning at 8:00 send me a summary of house temperatures
```

Or via CLI:

```
nanobot cron add --name "morning" --message "Temperature summary" --cron "0 8 * * *"
```

## Troubleshooting

**Bot not responding:**
- Check the API key in Configuration tab
- Check the add-on logs

**Telegram not working:**
- Make sure the bot token is correct
- Verify your User ID is in `allow_from`

**MCP not connecting:**
- Make sure the MCP Server integration is installed in HA
- Check your Long-Lived Access Token

## Data

All data is stored persistently and accessible at `/config/nanobot/` for easy editing.
