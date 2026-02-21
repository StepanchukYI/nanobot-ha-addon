# Nanobot Assistant — Home Assistant Add-on

[![HA Addon](https://img.shields.io/badge/Home%20Assistant-Add--on-blue)](https://www.home-assistant.io/)
[![Nanobot](https://img.shields.io/badge/nanobot-v0.1.4-green)](https://github.com/HKUDS/nanobot)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Ultra-lightweight AI assistant for Home Assistant, powered by [nanobot](https://github.com/HKUDS/nanobot) (~4,000 lines of code, ~100 MB RAM).

Works with **any OpenAI-compatible LLM provider** — OpenRouter, Anthropic, OpenAI, DeepSeek, Gemini, Zhipu, Ollama, and more.

## Features

- **Any LLM provider** — OpenRouter, Anthropic, OpenAI, DeepSeek, Gemini, Zhipu, Ollama, or any OpenAI-compatible API
- **Home Assistant MCP** — direct AI control of your smart home devices (lights, climate, switches, etc.)
- **Telegram** — chat with your home from anywhere, restrict access by user ID
- **Scheduled Tasks** — automated morning briefings, reminders, periodic reports
- **MCP Support** — connect any MCP server for extended capabilities
- **Custom System Prompt** — personalize your assistant's personality and knowledge
- **Persistent Storage** — config and memory survive addon updates

## Quick Install

1. **Settings → Add-ons → Add-on Store → ⋮ → Repositories**
2. Add: `https://github.com/StepanchukYI/nanobot-ha-addon`
3. Find and install **Nanobot Assistant**
4. Configure your LLM provider and API key, then start

## Supported Providers

| Provider | Config key | Example model | Notes |
|----------|-----------|---------------|-------|
| **OpenRouter** | `openrouter` | `anthropic/claude-sonnet-4` | Access to 100+ models via single API key |
| **Anthropic** | `anthropic` | `claude-sonnet-4-5` | Direct Anthropic API |
| **OpenAI** | `openai` | `gpt-4o` | GPT models |
| **DeepSeek** | `deepseek` | `deepseek-chat` | Budget-friendly, strong reasoning |
| **Gemini** | `gemini` | `gemini-2.5-flash` | Google's models |
| **Zhipu AI** | `zhipu` | `zai/glm-4-flash` | Cheapest option, great for basic smart home tasks |
| **Ollama** | `vllm` | any local model | Run locally, no API costs |

> **Tip:** Zhipu GLM-4-Flash is set as default because it's the cheapest option that handles smart home control well. Switch to any other provider for more advanced conversations.

## Architecture

```
┌─────────────────────────────────────────┐
│              Home Assistant              │
│                                         │
│  ┌──────────────┐  ┌────────────────┐   │
│  │  HA Core     │  │   Nanobot      │   │
│  │              │◄─│  Assistant     │   │
│  │  MCP Server  │  │  (Add-on)     │   │
│  │  integration │  │               │   │
│  └──────────────┘  │  Any LLM      │   │
│                     │  Telegram     │   │
│                     │  MCP Client   │   │
│                     └────────────────┘   │
└─────────────────────────────────────────┘
            │                    │
            ▼                    ▼
     Smart home             LLM API
     devices             (your choice)
```

## Documentation

See [DOCS.md](nanobot_assistant/DOCS.md) for full configuration reference.

## License

MIT — same as [nanobot](https://github.com/HKUDS/nanobot).
