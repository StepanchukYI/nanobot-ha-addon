# Nanobot Assistant — Home Assistant Add-on

Ultra-lightweight AI assistant for smart home control. ~4000 lines of code, ~100 MB RAM.

## Getting Started

1. Install the add-on from the repository
2. Start the add-on
3. Open **File Editor** and edit `/config/nanobot/config.json`
4. Set your LLM provider and API key:

```json
{
  "providers": {
    "openrouter": {
      "apiKey": "sk-or-v1-..."
    }
  },
  "agents": {
    "defaults": {
      "model": "anthropic/claude-sonnet-4"
    }
  }
}
```

5. Restart the add-on

## Configuration

All configuration is done via `/config/nanobot/config.json`. The add-on creates
a default template on first run. Edit it using File Editor, Samba, or SSH.

The add-on only reads `timezone` from the HA add-on settings panel.

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

## Telegram Setup

Add to your `config.json`:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "123456:ABC-...",
      "allowFrom": ["your_user_id"]
    }
  }
}
```

Get your bot token from `@BotFather` and your User ID from `@userinfobot`.

## Home Assistant MCP Setup

1. Install the **Model Context Protocol Server** integration in Home Assistant
2. Create a Long-Lived Access Token: Profile → Long-Lived Access Tokens → Create
3. Add to your `config.json`:

```json
{
  "tools": {
    "mcpServers": {
      "homeassistant": {
        "url": "http://homeassistant.local.hass.io:8123/api/mcp",
        "headers": {
          "Authorization": "Bearer YOUR_TOKEN"
        }
      }
    }
  }
}
```

## User Files

The add-on exposes its working files at `/config/nanobot/`:

- `config.json` — full nanobot configuration
- `skills/` — custom bot skills
- `workspace/` — agent working directory, memory
- `gateway.log` — gateway log file

The config is never overwritten by the add-on after first creation.

## MCP Servers

Nanobot supports connecting any MCP servers. Add them to
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
- Check the API key in `/config/nanobot/config.json`
- Check the add-on logs

**Telegram not working:**
- Make sure the bot token is correct
- Verify your User ID is in `allowFrom`

**MCP not connecting:**
- Make sure the MCP Server integration is installed in HA
- Check your Long-Lived Access Token

## Data

All data is stored persistently and accessible at `/config/nanobot/` for easy editing.
