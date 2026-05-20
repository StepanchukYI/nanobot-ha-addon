#!/usr/bin/env bash
# ============================================================
# Nanobot Assistant — Home Assistant Add-on entry point
# Runs upstream nanobot gateway. WebUI is bundled into the
# wheel and served by the websocket channel on 127.0.0.1:8765;
# HA Ingress proxies it to the addon panel.
#
# config.json is a template with ${SECRET} placeholders.
# Secrets are set in HA addon options. generate_config.py
# resolves placeholders → config.runtime.json (used by nanobot).
# ============================================================

# Read paths from HA options (new simple format)
NANOBOT_HOME=$(jq -r '.CONFIG_PATH // "/config/nanobot"' /data/options.json 2>/dev/null)
DATA_DIR=$(jq -r '.DATA_PATH // "/data/nanobot"' /data/options.json 2>/dev/null)

NANOBOT_BIN="/opt/nanobot-venv/bin/nanobot"
PYTHON="/opt/nanobot-venv/bin/python3"
# config.json = template (with ${SECRET} placeholders, safe for git)
# config.runtime.json = resolved (with actual secrets, used by nanobot)
CONFIG_TEMPLATE="${NANOBOT_HOME}/config.json"
CONFIG_FILE="${NANOBOT_HOME}/config.runtime.json"
LOG_FILE="${NANOBOT_HOME}/gateway.log"
MAX_RETRIES=5
RETRY_DELAY=15

export HOME="/data"
export NANOBOT_HOME

GW_LOOP_PID=""
PROXY_PID=""
STOPPING=false

cleanup() {
    STOPPING=true
    echo "[INFO] Shutting down..."
    [ -n "${PROXY_PID}" ] && kill "${PROXY_PID}" 2>/dev/null
    [ -n "${GW_LOOP_PID}" ] && kill "${GW_LOOP_PID}" 2>/dev/null
    pkill -f "nanobot gateway" 2>/dev/null
    pkill -f "ingress_proxy.py" 2>/dev/null
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

# --- Bootstrap config (only if missing) ---
echo "[INFO] Checking config..."
${PYTHON} /generate_config.py

# Debug: show config summary (without secrets)
echo "[INFO] Config keys: $(jq -r 'keys | join(", ")' "${CONFIG_FILE}" 2>/dev/null)"
echo "[INFO] MCP servers: $(jq -r '.tools.mcpServers | keys | join(", ") // "none"' "${CONFIG_FILE}" 2>/dev/null)"
echo "[INFO] Channels: $(jq -r '.channels | keys | join(", ") // "none"' "${CONFIG_FILE}" 2>/dev/null)"

# Symlink for nanobot CLI which reads from ~/.nanobot/config.json
ln -sf "${CONFIG_FILE}" "/data/.nanobot/config.json" 2>/dev/null || true

# --- HA config access (from options) ---
HA_CONFIG_ACCESS=$(jq -r '.ha_config_access // false' /data/options.json 2>/dev/null)
if [ "${HA_CONFIG_ACCESS}" = "true" ] && [ -d "/homeassistant" ]; then
    ln -sfn /homeassistant "${NANOBOT_HOME}/workspace/ha-config"
    echo "[INFO] HA config access ENABLED: workspace/ha-config -> /homeassistant/"
    jq '.tools.restrictToWorkspace = false' "${CONFIG_FILE}" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "${CONFIG_FILE}"
    if [ -n "${SUPERVISOR_TOKEN}" ]; then
        export SUPERVISOR_TOKEN
        echo "[INFO] Supervisor API token available"
    fi
else
    rm -f "${NANOBOT_HOME}/workspace/ha-config" 2>/dev/null
fi

# --- Timezone (from options) ---
TIMEZONE=$(jq -r '.timezone // "Europe/Kiev"' /data/options.json 2>/dev/null)
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
    echo "[WARN] Open the Web UI → Settings to add one, or edit config.json."
    echo "=============================================="
fi

# --- Banner ---
echo "=============================================="
echo " Nanobot Assistant v0.2.0"
echo " Config:        ${NANOBOT_HOME}/"
echo " Nanobot WebUI: http://127.0.0.1:8765/  (loopback only)"
echo " Ingress proxy: http://0.0.0.0:8099/    (HA Ingress entry point)"
echo " Gateway:       http://0.0.0.0:18790"
echo " Provider:      $(jq -r '.providers | keys[0] // "none"' "${CONFIG_FILE}" 2>/dev/null)"
echo " Model:         $(jq -r '.agents.defaults.model // "unknown"' "${CONFIG_FILE}" 2>/dev/null)"
echo "=============================================="

# --- Start ingress proxy (sits between HA Ingress and nanobot WebUI) ---
echo "[INFO] Starting ingress proxy on 0.0.0.0:8099 → 127.0.0.1:8765..."
${PYTHON} /ingress_proxy.py 2>&1 &
PROXY_PID=$!
echo "[INFO] Ingress proxy started (PID: ${PROXY_PID})"

# --- Gateway restart loop ---
gateway_loop() {
    local retries=0
    while [ "${STOPPING}" = "false" ] && [ ${retries} -lt ${MAX_RETRIES} ]; do
        echo "[INFO] Starting Nanobot Gateway (attempt $((retries + 1))/${MAX_RETRIES})..."
        cd "${NANOBOT_HOME}"
        ${NANOBOT_BIN} gateway -c "${CONFIG_FILE}" 2>&1 | tee -a "${LOG_FILE}"
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
            echo "[ERROR] Check config.json or view logs for details."
        fi
    done
}

# --- Start Nanobot Gateway (foreground) ---
gateway_loop
cleanup
