# Changelog

## 0.1.27 (2026-03-15)

### Changed

- Switch nanobot source from old feature branch to `dev` (rebased on latest upstream main)
- New features included: vision model preprocessor, event webhook trigger, telegram emoji reactions, litellm api_base fix, named agent profiles

### Added

- `vision_model` option in LLM settings — preprocesses images via a vision-capable model when the main model doesn't support vision
- `react_emoji` option in Telegram settings — auto-react to incoming messages with an emoji (e.g. `eyes`)

## 0.1.26 (2026-02-26)

### Changed

- pin nanobot to commit ba317e5 (feat/cron-named-agent-profiles)

## 0.1.25 (2026-02-25)

### Changed

- pin nanobot to commit b63d738 (feat/cron-named-agent-profiles)

## 0.1.24 (2026-02-25)

### Changed

- pin nanobot to commit 422550e (feat/cron-named-agent-profiles)

## 0.1.23 (2026-02-25)

### Changed

- pin nanobot to commit afa8994 (feat/cron-named-agent-profiles)

## 0.1.20 (2026-02-24)

### Fixed

- Agents tab: align with real schema of nanobot fork — `agents.defaults` has no `systemPrompt`; named profiles live under `agents.profiles` with only `systemPrompt` + `model`
- `generate_config.py`: write system prompt to `workspace/IDENTITY.md` (bootstrap file) instead of ignoring it in `agents.defaults`
- `generate_config.py`: auto-migrate old-format named agents from `agents.<name>` to `agents.profiles.<name>` on restart
- MCP Servers modal: add HTTP mode fields — `url`, `headers`, `toolTimeout`

## 0.1.19 (2026-02-24)

### Added

- Agents tab in Web UI — create, edit and delete nanobot agents with all settings: model, system prompt, maxTokens, temperature, maxToolIterations, memoryWindow, workspace
- MCP Servers: Edit button for all servers including built-in (homeassistant, exchange); env values masked in list but editable in form; warning shown when overriding built-in config

## 0.1.18 (2026-02-24)

### Changed

- Switch nanobot source from PyPI to custom fork `StepanchukYI/nanobot@feat/cron-named-agent-profiles` with cron fix and named agent profiles support

## 0.1.17 (2026-02-22)

### Fixed

- EWS MCP server: clone from source + wrapper script (pip entry point broken, `No module named 'src'`)

## 0.1.16 (2026-02-22)

### Added

- MCP Servers tab in Web UI — add/remove custom MCP servers without editing JSON
- Renamed addon to "Nanobot — AI Assistant for Raspberry Pi"

### Fixed

- EWS MCP server now installs from GitHub (not available on PyPI)

## 0.1.15 (2026-02-22)

### Added

- Exchange MCP integration (email, calendar, contacts, tasks) via `ews-mcp-server`
- `.gitignore` to prevent accidental commits of secrets

## 0.1.14 (2026-02-22)

### Added

- HA Ingress proxy support in Web UI — works both via direct port and through HA sidebar
- `mcp-proxy` as stdio-to-Streamable-HTTP bridge for reliable HA MCP connection
- `system_prompt.txt` file support (used when HA settings field is empty)
- `ha_config_access` toggle in Advanced settings — bot can read/edit HA config files
- Preserve Telegram `allowFrom` when HA UI list is empty

### Fixed

- Web UI port default from 8099 to 8080 (matching `ingress_port`)
- Web UI config/log file paths to use `NANOBOT_HOME` env (`/config/nanobot/`)
- Healthcheck now checks Web UI (port 8080, instant) instead of gateway (port 18790, slow startup)
- Added 60s `start-period` to prevent premature container restarts

## 0.1.7 (2026-02-21)

### Added

- Accordion-style configuration UI (LLM, Telegram, Home Assistant MCP, Advanced sections)
- HA Settings panel now controls all Nanobot config — no manual JSON editing required
- Config merges HA options into `config.json` on every restart (manual edits preserved)
- Provider presets with auto-filled API base URLs for Zhipu, OpenRouter, OpenAI, Anthropic, DeepSeek, Gemini, Ollama

### Changed

- Upgraded nanobot-ai to v0.1.4
- `generate_config.py` now always merges HA options into config.json instead of only creating on first run

### Fixed

- Config folder mapping (`addon_config:rw`) for proper `/config/` access
- Warning messages now point to HA Settings instead of manual file editing

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
