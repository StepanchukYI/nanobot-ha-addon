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
  .mcp-list { display: flex; flex-direction: column; gap: 10px; }
  .mcp-card { border: 1px solid #ddd; border-radius: 4px; padding: 12px; background: #fafafa; }
  .mcp-card-head { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
  .mcp-card-name { font-weight: 500; font-size: 14px; }
  .mcp-badge { font-size: 11px; padding: 2px 8px; border-radius: 3px; background: #e0e0e0; color: #666; }
  .mcp-badge-builtin { background: #e3f2fd; color: #1565c0; }
  .mcp-card-detail { font-size: 12px; color: #666; margin: 2px 0; }
  .mcp-card-detail code { background: #f0f0f0; padding: 1px 5px; border-radius: 2px; font-size: 12px; }
  .mcp-card-actions { margin-top: 8px; display: flex; justify-content: flex-end; }
  .btn-danger { background: #ef5350; color: white; }
  .btn-danger:hover { background: #d32f2f; }
  .btn-sm { padding: 4px 12px; font-size: 12px; }
  .modal-bg { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center; z-index: 100; }
  .modal-box { background: white; padding: 24px; border-radius: 6px; width: 90%; max-width: 460px; }
  .modal-box h3 { margin: 0 0 16px; font-size: 16px; }
  .fg { margin-bottom: 12px; }
  .fg label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 4px; }
  .fg input, .fg textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-family: monospace; font-size: 13px; box-sizing: border-box; }
  .fg textarea { resize: vertical; }
  .fg .hint { font-size: 11px; color: #999; margin-top: 2px; }
  .section-title { font-size: 13px; font-weight: 500; color: #666; margin: 16px 0 8px; text-transform: uppercase; letter-spacing: 0.5px; }
</style>
</head>
<body>

<div class="header">
  <span style="font-size:24px">🐈</span>
  <h1>Nanobot</h1>
</div>

<div class="tabs">
  <div class="tab active" onclick="showTab('config')">Configuration</div>
  <div class="tab" onclick="showTab('mcp')">MCP Servers</div>
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

<div class="panel" id="panel-mcp">
  <div class="toolbar">
    <button class="btn btn-primary" onclick="openAddModal()">+ Add Server</button>
    <div class="spacer"></div>
    <span class="status" id="mcpStatus"></span>
  </div>
  <div class="section-title">Built-in</div>
  <div class="mcp-list" id="builtinList"></div>
  <div class="section-title">Custom</div>
  <div class="mcp-list" id="customList"></div>
</div>

<div id="mcpModal" style="display:none"></div>

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
  if (name === 'mcp') loadMcpServers();
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

const BUILTIN_SERVERS = ['homeassistant', 'exchange'];

async function loadMcpServers() {
  try {
    const r = await fetch(apiUrl('/api/config'));
    const config = await r.json();
    const servers = (config.tools && config.tools.mcpServers) || {};
    const builtin = [];
    const custom = [];
    for (const [name, srv] of Object.entries(servers)) {
      const entry = {name, command: srv.command || '', args: srv.args || [], env: srv.env || {}};
      if (BUILTIN_SERVERS.includes(name)) builtin.push(entry);
      else custom.push(entry);
    }
    renderServers('builtinList', builtin, false);
    renderServers('customList', custom, true);
    document.getElementById('mcpStatus').textContent = Object.keys(servers).length + ' servers';
  } catch(e) {
    showMsg('Failed to load MCP servers: ' + e.message, false);
  }
}

function renderServers(containerId, servers, canDelete) {
  const el = document.getElementById(containerId);
  if (!servers.length) {
    el.innerHTML = '<div style="color:#999;font-size:13px;padding:8px 0">No servers configured</div>';
    return;
  }
  el.innerHTML = servers.map(s => {
    const argsStr = s.args.length ? s.args.join(' ') : '';
    const envKeys = Object.keys(s.env);
    const envStr = envKeys.map(k => {
      const v = s.env[k];
      const masked = (k.toLowerCase().includes('password') || k.toLowerCase().includes('token') || k.toLowerCase().includes('secret') || k.toLowerCase().includes('key'))
        ? '***' : v;
      return k + '=' + masked;
    }).join(', ');
    return '<div class="mcp-card">' +
      '<div class="mcp-card-head">' +
        '<span class="mcp-card-name">' + esc(s.name) + '</span>' +
        (canDelete ? '<span class="mcp-badge">custom</span>' : '<span class="mcp-badge mcp-badge-builtin">built-in</span>') +
      '</div>' +
      '<div class="mcp-card-detail"><strong>Command:</strong> <code>' + esc(s.command) + '</code></div>' +
      (argsStr ? '<div class="mcp-card-detail"><strong>Args:</strong> <code>' + esc(argsStr) + '</code></div>' : '') +
      (envKeys.length ? '<div class="mcp-card-detail"><strong>Env:</strong> <code>' + esc(envStr) + '</code></div>' : '') +
      (canDelete ? '<div class="mcp-card-actions"><button class="btn btn-danger btn-sm" onclick="deleteMcpServer(\\'' + esc(s.name) + '\\')">Delete</button></div>' : '') +
    '</div>';
  }).join('');
}

function esc(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }

function openAddModal() {
  document.getElementById('mcpModal').style.display = '';
  document.getElementById('mcpModal').innerHTML =
    '<div class="modal-bg" onclick="if(event.target===this)closeModal()">' +
    '<div class="modal-box">' +
      '<h3>Add MCP Server</h3>' +
      '<div class="fg"><label>Name</label><input id="m-name" placeholder="my-server"></div>' +
      '<div class="fg"><label>Command</label><input id="m-cmd" placeholder="/usr/bin/mcp-server"><div class="hint">Full path to the MCP server binary</div></div>' +
      '<div class="fg"><label>Arguments</label><input id="m-args" placeholder="--flag1 --flag2 value"><div class="hint">Space-separated arguments</div></div>' +
      '<div class="fg"><label>Environment Variables</label><textarea id="m-env" rows="4" placeholder="KEY=value\\nANOTHER_KEY=value"></textarea><div class="hint">One per line: KEY=value</div></div>' +
      '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">' +
        '<button class="btn btn-secondary" onclick="closeModal()">Cancel</button>' +
        '<button class="btn btn-primary" onclick="saveMcpServer()">Add</button>' +
      '</div>' +
    '</div></div>';
}

function closeModal() {
  document.getElementById('mcpModal').style.display = 'none';
  document.getElementById('mcpModal').innerHTML = '';
}

async function saveMcpServer() {
  const name = document.getElementById('m-name').value.trim();
  const cmd = document.getElementById('m-cmd').value.trim();
  const argsStr = document.getElementById('m-args').value.trim();
  const envStr = document.getElementById('m-env').value.trim();

  if (!name || !cmd) { showMsg('Name and Command are required', false); return; }
  if (BUILTIN_SERVERS.includes(name)) { showMsg('Cannot use reserved name: ' + name, false); return; }
  if (!/^[a-zA-Z0-9_-]+$/.test(name)) { showMsg('Name: only letters, numbers, hyphens, underscores', false); return; }

  const args = argsStr ? argsStr.split(/\\s+/) : [];
  const env = {};
  if (envStr) {
    for (const line of envStr.split('\\n')) {
      const eq = line.indexOf('=');
      if (eq > 0) env[line.substring(0, eq).trim()] = line.substring(eq + 1).trim();
    }
  }

  try {
    const r = await fetch(apiUrl('/api/config'));
    const config = await r.json();
    if (!config.tools) config.tools = {};
    if (!config.tools.mcpServers) config.tools.mcpServers = {};
    config.tools.mcpServers[name] = {command: cmd, args: args, env: env};

    const r2 = await fetch(apiUrl('/api/config'), {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(config, null, 2)
    });
    if (r2.ok) {
      showMsg('Server "' + name + '" added. Restart addon to apply.', true);
      closeModal();
      loadMcpServers();
    } else {
      showMsg('Failed to save: ' + r2.statusText, false);
    }
  } catch(e) { showMsg('Error: ' + e.message, false); }
}

async function deleteMcpServer(name) {
  if (!confirm('Delete MCP server "' + name + '"?')) return;
  try {
    const r = await fetch(apiUrl('/api/config'));
    const config = await r.json();
    if (config.tools && config.tools.mcpServers) {
      delete config.tools.mcpServers[name];
    }
    const r2 = await fetch(apiUrl('/api/config'), {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(config, null, 2)
    });
    if (r2.ok) {
      showMsg('Server "' + name + '" deleted. Restart addon to apply.', true);
      loadMcpServers();
    } else {
      showMsg('Delete failed: ' + r2.statusText, false);
    }
  } catch(e) { showMsg('Error: ' + e.message, false); }
}

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
