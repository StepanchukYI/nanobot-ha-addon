# Nanobot Assistant — Home Assistant Add-on

[![HA Addon](https://img.shields.io/badge/Home%20Assistant-Add--on-blue)](https://www.home-assistant.io/)
[![Nanobot](https://img.shields.io/badge/nanobot-v0.1.4-green)](https://github.com/HKUDS/nanobot)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Ultra-lightweight AI assistant for Home Assistant, powered by [nanobot](https://github.com/HKUDS/nanobot) (~4,000 lines of code, ~100 MB RAM).

## Features

- **Zhipu GLM / OpenRouter / Anthropic / DeepSeek** — multi-provider LLM support
- **Home Assistant MCP** — direct control of your smart home devices via AI
- **Telegram** — chat with your home assistant from anywhere
- **Scheduled Tasks** — automated morning briefings, reminders, periodic reports
- **MCP Support** — connect any MCP server for extended capabilities
- **Persistent Storage** — config and memory survive addon updates

## Quick Install

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Add: `https://github.com/StepanchukYI/nanobot-ha-addon`
3. Find and install **Nanobot Assistant**
4. Configure your API key and start

## Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `llm_provider` | LLM provider name | `zhipu` |
| `llm_api_key` | API key for LLM provider | (required) |
| `llm_model` | Model identifier | `zai/glm-4-flash` |
| `llm_api_base` | API base URL | Zhipu coding plan URL |
| `telegram_enabled` | Enable Telegram bot | `false` |
| `telegram_token` | Telegram bot token | |
| `telegram_allow_from` | Allowed Telegram user IDs | `[]` |
| `ha_mcp_enabled` | Enable HA MCP integration | `true` |
| `ha_mcp_url` | Home Assistant MCP endpoint | `http://homeassistant.local.hass.io:8123/api/mcp` |
| `ha_mcp_token` | HA Long-Lived Access Token | |

## Architecture

```
┌─────────────────────────────────────────┐
│           Raspberry Pi 4 (8GB)          │
│                                         │
│  ┌──────────────┐  ┌────────────────┐   │
│  │    Home       │  │   Nanobot      │   │
│  │  Assistant    │◄─│  Assistant     │   │
│  │              │  │  (HA Addon)    │   │
│  │  MCP Server  │  │               │   │
│  └──────────────┘  │  GLM-4-Flash  │   │
│                     │  Telegram     │   │
│                     │  MCP Client   │   │
│                     └────────────────┘   │
└─────────────────────────────────────────┘
            │                    │
            ▼                    ▼
     Local network         Zhipu AI API
```

## License

MIT — same as [nanobot](https://github.com/HKUDS/nanobot).
