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

export HOME="/data"
export NANOBOT_HOME

WEB_PID=""
GW_PID=""

cleanup() {
    echo "[INFO] Shutting down..."
    [ -n "${WEB_PID}" ] && kill "${WEB_PID}" 2>/dev/null
    [ -n "${GW_PID}" ] && kill "${GW_PID}" 2>/dev/null
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
echo " Nanobot Assistant v0.1.8"
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

# --- Start Nanobot Gateway ---
if [ -n "${API_KEY}" ]; then
    echo "[INFO] Starting Nanobot Gateway..."
    cd "${NANOBOT_HOME}"
    ${NANOBOT_BIN} gateway 2>&1 | tee -a "${LOG_FILE}" &
    GW_PID=$!
    echo "[INFO] Gateway started (PID: ${GW_PID})"
else
    echo "[INFO] Gateway NOT started (no API key). Configure in HA Settings."
fi

# --- Wait for processes ---
if [ -n "${GW_PID}" ]; then
    wait -n "${WEB_PID}" "${GW_PID}" 2>/dev/null
    echo "[WARN] A process exited. Cleaning up..."
else
    wait "${WEB_PID}" 2>/dev/null
    echo "[WARN] Web UI exited."
fi

cleanup
