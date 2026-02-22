# Nanobot — AI Assistant for Raspberry Pi

Ultra-lightweight AI assistant (~100 MB RAM) built for Raspberry Pi and low-power devices. Works with any OpenAI-compatible LLM provider.

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

> **Zhipu GLM-4-Flash** is the default — it's the cheapest provider that handles smart home tasks well.
> Switch to OpenRouter, Anthropic, OpenAI, or any other provider for more advanced conversations.

### Telegram

| Field | Description |
|-------|-------------|
| `enabled` | Enable Telegram bot |
| `token` | Bot token from `@BotFather` |
| `allow_from` | List of allowed Telegram User IDs (get yours from `@userinfobot`). Empty = everyone can write |

### Home Assistant MCP

| Field | Description |
|-------|-------------|
| `enabled` | Enable Home Assistant MCP integration |
| `url` | MCP server URL (default: `http://localhost:8123/api/mcp`) |
| `token` | Long-Lived Access Token (Profile → Security → Long-Lived Access Tokens → Create) |

Requires the **Model Context Protocol Server** integration installed in HA:
**Settings → Devices & Services → Add Integration → Model Context Protocol Server**

The add-on uses `mcp-proxy` as a stdio-to-Streamable-HTTP bridge for reliable MCP connection.

### Exchange MCP (Email & Calendar)

| Field | Description |
|-------|-------------|
| `enabled` | Enable Exchange MCP integration |
| `server_url` | Exchange server hostname (e.g. `mail.company.com`) |
| `email` | Your Exchange email address |
| `auth_type` | Authentication type: `ntlm` (on-premises), `basic`, or `oauth2` (Office 365) |
| `username` | Exchange username (usually same as email) |
| `password` | Exchange password |

When enabled, the bot gets access to:
- **Email** — read, send, search, reply, forward
- **Calendar** — view events, create appointments, check availability
- **Contacts** — search, create, update
- **Tasks** — create, update, complete

Uses [ews-mcp-server](https://github.com/azizmazrou/ews-mcp) as stdio MCP server.
Timezone is inherited from the Advanced section.

### Advanced

| Field | Description |
|-------|-------------|
| `system_prompt` | Custom system prompt for the bot personality |
| `ha_config_access` | Allow bot to read/edit HA config files (automations.yaml, scripts.yaml, etc.) |
| `timezone` | Timezone (e.g. `Europe/Kiev`, `America/New_York`) |
| `max_tokens` | Maximum response tokens (default: 8192) |
| `temperature` | LLM temperature 0.0–1.0 (default: 0.7) |

#### System Prompt

Two ways to set the system prompt:

1. **HA Settings field** — paste into `system_prompt` in Advanced section
2. **File** — create `/config/nanobot/system_prompt.txt` via File Editor (used when HA field is empty)

File method is more convenient for long prompts with formatting.

#### HA Config Access

When enabled, the bot can:
- Read and edit `automations.yaml`, `scripts.yaml`, `scenes.yaml`
- Create new automations and scripts
- Call HA Supervisor API for service reloads

HA config is available at `workspace/ha-config/` inside the bot's workspace.

## Supported LLM Providers

| Provider | Key in config | Example Model | Notes |
|----------|--------------|---------------|-------|
| Zhipu AI | `zhipu` | `zai/glm-4-flash` | Default. Cheapest option for smart home tasks |
| OpenRouter | `openrouter` | `anthropic/claude-sonnet-4` | 100+ models via single API |
| OpenAI | `openai` | `gpt-4o` | GPT models |
| Anthropic | `anthropic` | `claude-sonnet-4-5` | Direct Anthropic API |
| DeepSeek | `deepseek` | `deepseek-chat` | Budget-friendly, strong reasoning |
| Gemini | `gemini` | `gemini-2.5-flash` | Google models |
| Ollama (local) | `vllm` | any local model | No API costs, runs on your hardware |

Any OpenAI-compatible API can be used — just set `provider`, `api_key`, `api_base`, and `model`.

## User Files

The add-on exposes its working files at `/config/nanobot/`:

- `config.json` — generated nanobot configuration (merged from HA settings)
- `system_prompt.txt` — custom system prompt (optional)
- `skills/` — custom bot skills
- `workspace/` — agent working directory, memory
- `gateway.log` — gateway log file

You can edit files directly via File Editor. Manual changes to `config.json` are preserved
on restart — HA settings override only the fields you change in the UI.

## MCP Servers

The Web UI has a dedicated **MCP Servers** tab where you can manage all MCP connections:

- **Built-in servers** (Home Assistant, Exchange) are configured via HA Settings and shown as read-only
- **Custom servers** can be added/removed directly from the Web UI
- Click **+ Add Server** to add a new MCP server: provide a name, command path, optional arguments and environment variables
- Changes require an addon restart to take effect

Custom servers added via the Web UI are preserved across restarts — `generate_config.py` only touches built-in server entries.

You can also add servers manually to `tools.mcpServers` in `/config/nanobot/config.json`.

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
- If `allow_from` keeps resetting: set IDs directly in config.json — they'll be preserved when UI list is empty

**MCP not connecting:**
- Make sure the MCP Server integration is installed in HA
- Check your Long-Lived Access Token
- The add-on uses `mcp-proxy` for reliable connection; check logs for HTTP status codes

**Exchange not connecting:**
- Verify your Exchange server URL (try `https://your-server/EWS/Exchange.asmx` in a browser)
- For on-premises Exchange use `ntlm` auth type
- Check that your credentials are correct
- Ensure your Exchange server is reachable from the HA host

## Data

All data is stored persistently and accessible at `/config/nanobot/` for easy editing.
