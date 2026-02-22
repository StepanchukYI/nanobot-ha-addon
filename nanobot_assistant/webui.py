#!/usr/bin/env python3
"""Minimal web UI for Nanobot HA addon: config editor + log viewer.

Works both via direct port access and through HA Ingress proxy.
"""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

NANOBOT_HOME = os.environ.get("NANOBOT_HOME", "/config/nanobot")
CONFIG_FILE = os.path.join(NANOBOT_HOME, "config.json")
LOG_FILE = os.path.join(NANOBOT_HOME, "gateway.log")
LOG_LINES = 500

HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nanobot Assistant</title>
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; background: #f5f5f5; color: #333; }
  .header { background: #03a9f4; color: white; padding: 16px 24px; display: flex; align-items: center; gap: 12px; }
  .header h1 { font-size: 18px; margin: 0; font-weight: 500; }
  .tabs { display: flex; background: white; border-bottom: 1px solid #ddd; }
  .tab { padding: 12px 24px; cursor: pointer; font-size: 14px; border-bottom: 3px solid transparent; color: #666; }
  .tab:hover { color: #333; }
  .tab.active { color: #03a9f4; border-bottom-color: #03a9f4; font-weight: 500; }
  .panel { display: none; padding: 24px; }
  .panel.active { display: block; }
  textarea { width: 100%; min-height: 500px; font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; font-size: 13px; line-height: 1.5; border: 1px solid #ddd; border-radius: 4px; padding: 12px; background: #fafafa; resize: vertical; box-sizing: border-box; tab-size: 2; }
  .logs { background: #1e1e1e; color: #d4d4d4; font-family: "SFMono-Regular", Consolas, monospace; font-size: 12px; line-height: 1.6; padding: 12px; border-radius: 4px; min-height: 500px; max-height: 80vh; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
  .btn { padding: 8px 20px; border: none; border-radius: 4px; font-size: 14px; cursor: pointer; font-weight: 500; }
  .btn-primary { background: #03a9f4; color: white; }
  .btn-primary:hover { background: #0288d1; }
  .btn-secondary { background: #e0e0e0; color: #333; }
  .btn-secondary:hover { background: #bdbdbd; }
  .toolbar { display: flex; gap: 8px; margin-bottom: 12px; align-items: center; }
  .toolbar .spacer { flex: 1; }
  .status { font-size: 12px; color: #888; }
  .msg { padding: 8px 12px; border-radius: 4px; margin-bottom: 12px; font-size: 13px; }
  .msg-ok { background: #e8f5e9; color: #2e7d32; }
  .msg-err { background: #ffebee; color: #c62828; }
</style>
</head>
<body>

<div class="header">
  <span style="font-size:24px">🐈</span>
  <h1>Nanobot Assistant</h1>
</div>

<div class="tabs">
  <div class="tab active" onclick="showTab('config')">Configuration</div>
  <div class="tab" onclick="showTab('logs')">Log</div>
</div>

<div id="msg"></div>

<div class="panel active" id="panel-config">
  <div class="toolbar">
    <button class="btn btn-primary" onclick="saveConfig()">Save</button>
    <button class="btn btn-secondary" onclick="loadConfig()">Reload</button>
    <div class="spacer"></div>
    <span class="status" id="configStatus"></span>
  </div>
  <textarea id="configEditor" spellcheck="false"></textarea>
</div>

<div class="panel" id="panel-logs">
  <div class="toolbar">
    <button class="btn btn-secondary" onclick="loadLogs()">Refresh</button>
    <label style="font-size:13px;display:flex;align-items:center;gap:4px">
      <input type="checkbox" id="autoScroll" checked> Auto-scroll
    </label>
    <div class="spacer"></div>
    <span class="status" id="logStatus"></span>
  </div>
  <div class="logs" id="logsView">Loading...</div>
</div>

<script>
// Detect base path for HA Ingress compatibility
// Ingress URLs: /api/hassio_ingress/<token>/
// Direct URLs: /
const basePath = window.location.pathname.replace(/\\/+$/, '');

function apiUrl(path) {
  return basePath + path;
}

function showTab(name) {
  document.querySelectorAll('.tab').forEach((t,i) => t.classList.toggle('active', t.textContent.toLowerCase().includes(name)));
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
  if (name === 'logs') loadLogs();
  if (name === 'config') loadConfig();
}

function showMsg(text, ok) {
  const el = document.getElementById('msg');
  el.innerHTML = '<div class="msg ' + (ok ? 'msg-ok' : 'msg-err') + '">' + text + '</div>';
  setTimeout(() => el.innerHTML = '', 4000);
}

async function loadConfig() {
  try {
    const r = await fetch(apiUrl('/api/config'));
    const data = await r.json();
    document.getElementById('configEditor').value = JSON.stringify(data, null, 2);
    document.getElementById('configStatus').textContent = 'Loaded';
  } catch(e) {
    showMsg('Failed to load config: ' + e.message, false);
  }
}

async function saveConfig() {
  const text = document.getElementById('configEditor').value;
  try {
    JSON.parse(text);
  } catch(e) {
    showMsg('Invalid JSON: ' + e.message, false);
    return;
  }
  try {
    const r = await fetch(apiUrl('/api/config'), { method: 'POST', headers: {'Content-Type':'application/json'}, body: text });
    if (r.ok) {
      showMsg('Config saved. Restart addon to apply changes.', true);
      document.getElementById('configStatus').textContent = 'Saved';
    } else {
      showMsg('Save failed: ' + r.statusText, false);
    }
  } catch(e) {
    showMsg('Save failed: ' + e.message, false);
  }
}

async function loadLogs() {
  try {
    const r = await fetch(apiUrl('/api/logs'));
    const data = await r.json();
    const el = document.getElementById('logsView');
    el.textContent = (data.logs || []).join('\\n');
    if (document.getElementById('autoScroll').checked) {
      el.scrollTop = el.scrollHeight;
    }
    document.getElementById('logStatus').textContent = data.logs.length + ' lines';
  } catch(e) {
    document.getElementById('logsView').textContent = 'Error: ' + e.message;
  }
}

document.getElementById('configEditor').addEventListener('keydown', function(e) {
  if (e.key === 'Tab') {
    e.preventDefault();
    const s = this.selectionStart;
    this.value = this.value.substring(0, s) + '  ' + this.value.substring(this.selectionEnd);
    this.selectionStart = this.selectionEnd = s + 2;
  }
});

loadConfig();
setInterval(() => { if (document.getElementById('panel-logs').classList.contains('active')) loadLogs(); }, 5000);
</script>
</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _headers(self, code=200, content_type="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.end_headers()

    def _strip_ingress(self, path):
        """Strip HA Ingress prefix from path.

        Ingress paths: /api/hassio_ingress/<token>/api/config
        Direct paths:  /api/config
        """
        # Find the last occurrence of /api/ that is our API
        for prefix in ("/api/config", "/api/logs", "/api/health"):
            if path.endswith(prefix):
                return prefix
        if path.endswith("/") or path.endswith("/index.html"):
            return "/"
        return path

    def do_GET(self):
        route = self._strip_ingress(self.path)

        if route == "/" or route == "/index.html":
            self._headers(200, "text/html")
            self.wfile.write(HTML.encode())

        elif route == "/api/config":
            try:
                with open(CONFIG_FILE) as f:
                    data = f.read()
                self._headers()
                self.wfile.write(data.encode())
            except Exception as e:
                self._headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        elif route == "/api/logs":
            try:
                if os.path.exists(LOG_FILE):
                    with open(LOG_FILE) as f:
                        lines = f.readlines()[-LOG_LINES:]
                    lines = [l.rstrip() for l in lines]
                else:
                    lines = ["No logs available yet."]
                self._headers()
                self.wfile.write(json.dumps({"logs": lines}).encode())
            except Exception as e:
                self._headers()
                self.wfile.write(json.dumps({"logs": [f"Error: {e}"]}).encode())

        elif route == "/api/health":
            self._headers()
            self.wfile.write(json.dumps({"ok": True}).encode())

        else:
            self._headers(404)
            self.wfile.write(b'{"error":"not found"}')

    def do_POST(self):
        route = self._strip_ingress(self.path)

        if route == "/api/config":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                json.loads(body)
                with open(CONFIG_FILE, "wb") as f:
                    f.write(body)
                self._headers()
                self.wfile.write(b'{"ok":true}')
            except json.JSONDecodeError as e:
                self._headers(400)
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {e}"}).encode())
            except Exception as e:
                self._headers(500)
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self._headers(404)
            self.wfile.write(b'{"error":"not found"}')


def main():
    port = int(os.environ.get("WEB_PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), Handler)
    print(f"[INFO] Web UI running on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
