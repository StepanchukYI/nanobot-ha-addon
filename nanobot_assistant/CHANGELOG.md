# Changelog

## 0.1.3 (2026-02-21)

### Added

- Expose user-editable files at `/config/nanobot/` (skills, workspace, config, logs)
- Config-as-file: all settings via `/config/nanobot/config.json` instead of HA form
- Translate DOCS.md to English

### Fixed

- Fix BUILD_FROM arg override in build.yaml

## 0.1.1 (2026-02-21)

### Fixed

- Fix Docker build: correct COPY paths (webserver.py → webui.py, remove missing web/ dir)
- Fix run.sh: reference correct webui.py filename

## 0.1.0 (2026-02-21)

### Initial Release

- Nanobot AI assistant as Home Assistant add-on
- Zhipu AI (GLM-4 / GLM-4-Flash) support out of the box
- Multi-provider support: OpenRouter, Anthropic, OpenAI, DeepSeek, Gemini, Ollama
- Home Assistant MCP integration for smart home control
- Telegram bot integration
- Scheduled tasks (cron)
- Persistent configuration and memory
- Multi-arch support: aarch64 (Raspberry Pi 4/5), amd64, armv7
