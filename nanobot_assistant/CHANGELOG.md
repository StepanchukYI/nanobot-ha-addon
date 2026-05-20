# Changelog

## 0.2.1 (2026-05-20)

### Fixed

- HA Ingress could not reach the bundled WebUI: the Supervisor proxy runs in a separate network namespace, so binding nanobot to `127.0.0.1:8765` made `127.0.0.1` from Supervisor's view a different loopback than the addon's. The previous symptom was "The app is not running" in the HA panel even though the addon was healthy.

### Added

- `ingress_proxy.py`: a small aiohttp reverse proxy that listens on `0.0.0.0:8099` (the new `ingress_port`) and forwards HTTP + WebSocket traffic to nanobot on `127.0.0.1:8765`. It enforces two checks per request:
  1. **Header check** — the request must carry at least one of `X-Ingress-Path` / `X-Hass-Source` (set by HA Supervisor on every Ingress-proxied request).
  2. **Source IP check** — the peer must come from the Supervisor docker bridge (`172.30.32.0/23`) or the host loopback. Either check alone is spoofable; both together are not.
- The proxy injects `Authorization: Bearer <secret>` only on `/webui/bootstrap`, where nanobot needs it to issue the short-lived `nbwt_…` API token. Subsequent `/api/*` and WebSocket requests already carry that token from the client and pass through unchanged.
- `generate_config.py` now generates a 256-bit URL-safe secret at first boot, persists it under `/data/.nanobot/proxy_secret` (mode 0600), and injects it into the runtime config as `channels.websocket.tokenIssueSecret`. The proxy reads the same file at startup.

### Changed

- `ingress_port` switched from `8765` to `8099`. The Web UI is now reached at `https://<ha>/api/hassio_ingress/<token>/` → proxy `:8099` → nanobot `:8765`.
- `channels.websocket.host` is now always `127.0.0.1` (pinned by `generate_config.py` on every boot); nanobot is unreachable from the LAN.
- Healthcheck still hits `http://127.0.0.1:8765/` — if nanobot is up, the proxy will be too.

## 0.2.0 (2026-05-20)

### Changed

- Switch nanobot source from custom fork `StepanchukYI/nanobot@dev` to upstream PyPI `nanobot-ai==0.2.0`. Fork is archived.
- Drop fork-only features no longer used: named agent profiles (`agents.profiles`), custom slash commands, vision-cache preprocessor, event-webhook trigger, telegram emoji reactions.
- Replace the addon's custom Web UI (Python `BaseHTTPRequestHandler` server on port 8080) with the upstream WebUI bundled inside `nanobot-ai`, served by the `websocket` channel on `127.0.0.1:8765`. Provides chat, redesigned Settings/BYOK, sessions, MCP/cron management, image generation.
- HA Ingress now points at port 8765 (was 8080). Direct port 8080 mapping is removed.
- Healthcheck targets `http://127.0.0.1:8765/`; `start-period` raised to 90s to accommodate gateway init.
- Default config enables the websocket channel (host `127.0.0.1`, port `8765`, no token — only HA Ingress on the same host can reach it).

### Removed

- `nanobot_assistant/webui.py` — custom Web UI (Configuration / Agents / MCP Servers / Logs tabs) replaced by upstream bundled UI.
- `agents.profiles` field is stripped from existing `config.json` on first run after upgrade.
- Port 8080 mapping (no longer used).

### Migrated

- `agents.defaults.memoryWindow` → `agents.defaults.maxMessages` (upstream renamed the field). Existing configs auto-migrate.

### Notes

- Upstream v0.2.0 brings `/goal` + `long_task`, WebUI bundled in the wheel, settings/BYOK redesign, 5 new providers (Bedrock, NVIDIA NIM, LongCat, Atomic Chat, MiMo), `fallback_models`, and four security fixes (SSRF, media path confinement, workspace boundaries). See [HKUDS/nanobot v0.2.0 release notes](https://github.com/HKUDS/nanobot/releases/tag/v0.2.0).
- Logs/MCP/cron are now manageable from the upstream Web UI; `config.json` remains the source of truth on disk.

## 0.1.30 (2026-03-16)

### Added

- Custom slash commands system: agent can create `/camera`, `/status`, etc.
- Three command modes: `script` (no LLM), `agent` (prompt injection), `mixed` (script + agent)
- Commands auto-register in Telegram bot menu
- New `command` tool for agent to manage commands at runtime
- Commands stored in `workspace/commands.json`

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
