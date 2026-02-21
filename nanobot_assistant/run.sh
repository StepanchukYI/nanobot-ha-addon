#!/usr/bin/env bash
# ============================================================
# Nanobot Assistant — Home Assistant Add-on entry point
# Manages: Web UI (port 8080) + Nanobot Gateway (port 18790)
# ============================================================

# /config = addon_config (visible from other addons like File Editor, VS Code)
# /data   = addon private data (only visible inside this container)
NANOBOT_HOME="/config/nanobot"
NANOBOT_BIN="/opt/nanobot-venv/bin/nanobot"
PYTHON="/opt/nanobot-venv/bin/python3"
CONFIG_FILE="${NANOBOT_HOME}/config.json"
LOG_FILE="${NANOBOT_HOME}/gateway.log"
MAX_RETRIES=5
RETRY_DELAY=15

export HOME="/data"
export NANOBOT_HOME

WEB_PID=""
GW_LOOP_PID=""
STOPPING=false

cleanup() {
    STOPPING=true
    echo "[INFO] Shutting down..."
    [ -n "${WEB_PID}" ] && kill "${WEB_PID}" 2>/dev/null
    [ -n "${GW_LOOP_PID}" ] && kill "${GW_LOOP_PID}" 2>/dev/null
    # Kill any nanobot gateway processes
    pkill -f "nanobot gateway" 2>/dev/null
    wait 2>/dev/null
    exit 0
}
trap cleanup SIGTERM SIGINT

# --- Create directories ---
mkdir -p "${NANOBOT_HOME}" "${NANOBOT_HOME}/workspace" "${NANOBOT_HOME}/skills" "/data/.nanobot"

# --- Migrate from old /data/nanobot location if exists ---
if [ -d "/data/nanobot" ] && [ ! -L "/data/nanobot" ]; then
    echo "[INFO] Migrating data from /data/nanobot to ${NANOBOT_HOME}..."
    cp -rn /data/nanobot/* "${NANOBOT_HOME}/" 2>/dev/null || true
    rm -rf /data/nanobot
    echo "[INFO] Migration complete."
fi

# --- Generate / merge config from HA options ---
echo "[INFO] Generating config..."
${PYTHON} /generate_config.py

# Debug: show generated config (without secrets)
echo "[INFO] Config keys: $(jq -r 'keys | join(", ")' "${CONFIG_FILE}" 2>/dev/null)"
echo "[INFO] MCP servers: $(jq -r '.tools.mcpServers | keys | join(", ") // "none"' "${CONFIG_FILE}" 2>/dev/null)"
echo "[INFO] Channels: $(jq -r '.channels | keys | join(", ") // "none"' "${CONFIG_FILE}" 2>/dev/null)"

# Symlink for nanobot CLI which reads from ~/.nanobot/config.json
ln -sf "${CONFIG_FILE}" "/data/.nanobot/config.json" 2>/dev/null || true

# --- Timezone (from HA options) ---
TIMEZONE=$(jq -r '.advanced.timezone // "Europe/Kiev"' /data/options.json 2>/dev/null)
if [ -f "/usr/share/zoneinfo/${TIMEZONE}" ]; then
    ln -sf "/usr/share/zoneinfo/${TIMEZONE}" /etc/localtime
    echo "${TIMEZONE}" > /etc/timezone
    echo "[INFO] Timezone: ${TIMEZONE}"
fi

# --- Check API key ---
API_KEY=$(jq -r '.providers | to_entries[0].value.apiKey // empty' "${CONFIG_FILE}" 2>/dev/null)
if [ -z "${API_KEY}" ]; then
    echo "=============================================="
    echo "[WARN] No LLM API key configured!"
    echo "[WARN] Set your API key in Settings -> Add-ons -> Nanobot Assistant -> Configuration"
    echo "=============================================="
fi

# --- Banner ---
echo "=============================================="
echo " Nanobot Assistant v0.1.10"
echo " Config:   ${NANOBOT_HOME}/"
echo " Web UI:   http://0.0.0.0:8080  (HA Ingress)"
echo " Gateway:  http://0.0.0.0:18790"
echo " Provider: $(jq -r '.providers | keys[0] // "none"' "${CONFIG_FILE}" 2>/dev/null)"
echo " Model:    $(jq -r '.agents.defaults.model // "unknown"' "${CONFIG_FILE}" 2>/dev/null)"
echo "=============================================="

# --- Start Web UI ---
echo "[INFO] Starting Web UI server..."
${PYTHON} /webui.py 2>&1 &
WEB_PID=$!
echo "[INFO] Web UI started (PID: ${WEB_PID})"

# --- Gateway restart loop ---
gateway_loop() {
    local retries=0
    while [ "${STOPPING}" = "false" ] && [ ${retries} -lt ${MAX_RETRIES} ]; do
        echo "[INFO] Starting Nanobot Gateway (attempt $((retries + 1))/${MAX_RETRIES})..."
        cd "${NANOBOT_HOME}"
        ${NANOBOT_BIN} gateway 2>&1 | tee -a "${LOG_FILE}"
        EXIT_CODE=$?

        if [ "${STOPPING}" = "true" ]; then
            break
        fi

        retries=$((retries + 1))
        if [ ${retries} -lt ${MAX_RETRIES} ]; then
            echo "[WARN] Gateway exited (code: ${EXIT_CODE}). Restarting in ${RETRY_DELAY}s... (${retries}/${MAX_RETRIES})"
            sleep ${RETRY_DELAY}
        else
            echo "[ERROR] Gateway failed ${MAX_RETRIES} times. Giving up."
            echo "[ERROR] Check your MCP/Telegram settings or view logs for details."
        fi
    done
}

# --- Start Nanobot Gateway ---
if [ -n "${API_KEY}" ]; then
    gateway_loop &
    GW_LOOP_PID=$!
    echo "[INFO] Gateway loop started (PID: ${GW_LOOP_PID})"
else
    echo "[INFO] Gateway NOT started (no API key). Configure in HA Settings."
fi

# --- Keep alive: wait for Web UI ---
# Web UI keeps the addon running even if gateway crashes
wait "${WEB_PID}" 2>/dev/null
echo "[WARN] Web UI exited."
cleanup
