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
  .tabs { display: flex; background: white; border-bottom: 1px solid #ddd; overflow-x: auto; }
  .tab { padding: 12px 24px; cursor: pointer; font-size: 14px; border-bottom: 3px solid transparent; color: #666; white-space: nowrap; }
  .tab:hover { color: #333; }
  .tab.active { color: #03a9f4; border-bottom-color: #03a9f4; font-weight: 500; }
  .panel { display: none; padding: 24px; }
  .panel.active { display: block; }
  textarea.code { width: 100%; min-height: 500px; font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; font-size: 13px; line-height: 1.5; border: 1px solid #ddd; border-radius: 4px; padding: 12px; background: #fafafa; resize: vertical; box-sizing: border-box; tab-size: 2; }
  .logs { background: #1e1e1e; color: #d4d4d4; font-family: "SFMono-Regular", Consolas, monospace; font-size: 12px; line-height: 1.6; padding: 12px; border-radius: 4px; min-height: 500px; max-height: 80vh; overflow-y: auto; white-space: pre-wrap; word-break: break-all; }
  .btn { padding: 8px 20px; border: none; border-radius: 4px; font-size: 14px; cursor: pointer; font-weight: 500; }
  .btn-primary { background: #03a9f4; color: white; }
  .btn-primary:hover { background: #0288d1; }
  .btn-secondary { background: #e0e0e0; color: #333; }
  .btn-secondary:hover { background: #bdbdbd; }
  .btn-danger { background: #ef5350; color: white; }
  .btn-danger:hover { background: #d32f2f; }
  .btn-sm { padding: 4px 12px; font-size: 12px; }
  .toolbar { display: flex; gap: 8px; margin-bottom: 12px; align-items: center; }
  .toolbar .spacer { flex: 1; }
  .status { font-size: 12px; color: #888; }
  .msg { padding: 8px 12px; border-radius: 4px; margin-bottom: 12px; font-size: 13px; }
  .msg-ok { background: #e8f5e9; color: #2e7d32; }
  .msg-err { background: #ffebee; color: #c62828; }
  .card-list { display: flex; flex-direction: column; gap: 10px; }
  .card { border: 1px solid #ddd; border-radius: 4px; padding: 12px; background: #fafafa; }
  .card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; flex-wrap: wrap; }
  .card-name { font-weight: 500; font-size: 14px; }
  .badge { font-size: 11px; padding: 2px 8px; border-radius: 3px; background: #e0e0e0; color: #666; }
  .badge-builtin { background: #e3f2fd; color: #1565c0; }
  .badge-default { background: #f3e5f5; color: #6a1b9a; }
  .badge-agent { background: #e8f5e9; color: #2e7d32; }
  .card-detail { font-size: 12px; color: #555; margin: 3px 0; line-height: 1.5; }
  .card-detail code { background: #efefef; padding: 1px 5px; border-radius: 2px; font-size: 12px; word-break: break-all; }
  .card-detail .prompt-preview { color: #777; font-style: italic; }
  .card-actions { margin-top: 10px; display: flex; justify-content: flex-end; gap: 6px; }
  .modal-bg { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.45); display: flex; align-items: center; justify-content: center; z-index: 100; padding: 16px; box-sizing: border-box; }
  .modal-box { background: white; padding: 24px; border-radius: 6px; width: 100%; max-width: 560px; max-height: 90vh; overflow-y: auto; box-sizing: border-box; }
  .modal-box h3 { margin: 0 0 16px; font-size: 16px; }
  .fg { margin-bottom: 12px; }
  .fg label { display: block; font-size: 13px; font-weight: 500; margin-bottom: 4px; color: #444; }
  .fg input, .fg select, .fg textarea { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-family: monospace; font-size: 13px; box-sizing: border-box; background: white; }
  .fg select { font-family: inherit; }
  .fg textarea { resize: vertical; min-height: 80px; }
  .fg .hint { font-size: 11px; color: #999; margin-top: 3px; }
  .fg input[readonly] { background: #f5f5f5; color: #888; cursor: default; }
  .fg input:focus, .fg textarea:focus { outline: none; border-color: #03a9f4; box-shadow: 0 0 0 2px rgba(3,169,244,0.15); }
  .section-title { font-size: 12px; font-weight: 600; color: #888; margin: 20px 0 8px; text-transform: uppercase; letter-spacing: 0.6px; }
  .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 0 12px; }
  .modal-footer { display: flex; gap: 8px; justify-content: flex-end; margin-top: 16px; padding-top: 16px; border-top: 1px solid #eee; }
  .empty-hint { color: #bbb; font-size: 13px; padding: 12px 0; }
</style>
</head>
<body>

<div class="header">
  <span style="font-size:24px">🐈</span>
  <h1>Nanobot</h1>
</div>

<div class="tabs">
  <div class="tab active" onclick="showTab('config')">Configuration</div>
  <div class="tab" onclick="showTab('agents')">Agents</div>
  <div class="tab" onclick="showTab('mcp')">MCP Servers</div>
  <div class="tab" onclick="showTab('logs')">Logs</div>
</div>

<div id="msg"></div>

<!-- Configuration -->
<div class="panel active" id="panel-config">
  <div class="toolbar">
    <button class="btn btn-primary" onclick="saveConfig()">Save</button>
    <button class="btn btn-secondary" onclick="loadConfig()">Reload</button>
    <div class="spacer"></div>
    <span class="status" id="configStatus"></span>
  </div>
  <textarea class="code" id="configEditor" spellcheck="false"></textarea>
</div>

<!-- Agents -->
<div class="panel" id="panel-agents">
  <div class="toolbar">
    <button class="btn btn-primary" onclick="openAgentModal(null)">+ Add Agent</button>
    <div class="spacer"></div>
    <span class="status" id="agentsStatus"></span>
  </div>
  <div class="section-title">Default Configuration</div>
  <div class="card-list" id="defaultAgentList"></div>
  <div class="section-title">Custom Agents</div>
  <div class="card-list" id="customAgentList"></div>
</div>

<!-- MCP Servers -->
<div class="panel" id="panel-mcp">
  <div class="toolbar">
    <button class="btn btn-primary" onclick="openMcpModal(null)">+ Add Server</button>
    <div class="spacer"></div>
    <span class="status" id="mcpStatus"></span>
  </div>
  <div class="section-title">Built-in</div>
  <div class="card-list" id="builtinList"></div>
  <div class="section-title">Custom</div>
  <div class="card-list" id="customList"></div>
</div>

<!-- Logs -->
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

<!-- Modal containers -->
<div id="agentModalCt" style="display:none"></div>
<div id="mcpModalCt" style="display:none"></div>

<script>
const basePath = window.location.pathname.replace(/\\/+$/, '');
function apiUrl(p) { return basePath + p; }

function showTab(name) {
  document.querySelectorAll('.tab').forEach(t =>
    t.classList.toggle('active', t.textContent.toLowerCase().includes(name))
  );
  document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
  document.getElementById('panel-' + name).classList.add('active');
  if (name === 'logs')   loadLogs();
  if (name === 'config') loadConfig();
  if (name === 'mcp')    loadMcpServers();
  if (name === 'agents') loadAgents();
}

function showMsg(text, ok) {
  const el = document.getElementById('msg');
  el.innerHTML = '<div class="msg ' + (ok ? 'msg-ok' : 'msg-err') + '">' + text + '</div>';
  setTimeout(() => el.innerHTML = '', 4000);
}

function esc(s) {
  const d = document.createElement('div');
  d.textContent = String(s == null ? '' : s);
  return d.innerHTML;
}

// ── Config ───────────────────────────────────────────────────────

async function loadConfig() {
  try {
    const r = await fetch(apiUrl('/api/config'));
    const data = await r.json();
    document.getElementById('configEditor').value = JSON.stringify(data, null, 2);
    document.getElementById('configStatus').textContent = 'Loaded';
  } catch(e) { showMsg('Failed to load config: ' + e.message, false); }
}

async function saveConfig() {
  const text = document.getElementById('configEditor').value;
  try { JSON.parse(text); } catch(e) { showMsg('Invalid JSON: ' + e.message, false); return; }
  try {
    const r = await fetch(apiUrl('/api/config'), {
      method: 'POST', headers: {'Content-Type':'application/json'}, body: text
    });
    if (r.ok) {
      showMsg('Config saved. Restart addon to apply changes.', true);
      document.getElementById('configStatus').textContent = 'Saved';
    } else showMsg('Save failed: ' + r.statusText, false);
  } catch(e) { showMsg('Save failed: ' + e.message, false); }
}

document.getElementById('configEditor').addEventListener('keydown', function(e) {
  if (e.key === 'Tab') {
    e.preventDefault();
    const s = this.selectionStart;
    this.value = this.value.substring(0, s) + '  ' + this.value.substring(this.selectionEnd);
    this.selectionStart = this.selectionEnd = s + 2;
  }
});

// ── Logs ─────────────────────────────────────────────────────────

async function loadLogs() {
  try {
    const r = await fetch(apiUrl('/api/logs'));
    const data = await r.json();
    const el = document.getElementById('logsView');
    el.textContent = (data.logs || []).join('\\n');
    if (document.getElementById('autoScroll').checked) el.scrollTop = el.scrollHeight;
    document.getElementById('logStatus').textContent = data.logs.length + ' lines';
  } catch(e) { document.getElementById('logsView').textContent = 'Error: ' + e.message; }
}

// ── Agents ───────────────────────────────────────────────────────

async function loadAgents() {
  try {
    const r = await fetch(apiUrl('/api/config'));
    const config = await r.json();
    const agents = config.agents || {};
    const defEntry  = agents.defaults !== undefined ? {defaults: agents.defaults} : {};
    const custom = Object.fromEntries(Object.entries(agents).filter(([k]) => k !== 'defaults'));
    renderAgentCards('defaultAgentList', defEntry, false);
    renderAgentCards('customAgentList', custom, true);
    document.getElementById('agentsStatus').textContent = Object.keys(agents).length + ' configured';
  } catch(e) { showMsg('Failed to load agents: ' + e.message, false); }
}

function agentSummaryHtml(a) {
  let h = '';
  if (a.model)    h += '<div class="card-detail"><strong>Model:</strong> <code>' + esc(a.model) + '</code></div>';
  if (a.maxTokens != null) h += '<div class="card-detail"><strong>Max Tokens:</strong> ' + a.maxTokens + '</div>';
  if (a.temperature != null) h += '<div class="card-detail"><strong>Temperature:</strong> ' + a.temperature + '</div>';
  if (a.maxToolIterations != null) h += '<div class="card-detail"><strong>Tool Iterations:</strong> ' + a.maxToolIterations + '</div>';
  if (a.memoryWindow != null) h += '<div class="card-detail"><strong>Memory Window:</strong> ' + a.memoryWindow + '</div>';
  if (a.workspace) h += '<div class="card-detail"><strong>Workspace:</strong> <code>' + esc(a.workspace) + '</code></div>';
  if (a.systemPrompt) {
    const prev = a.systemPrompt.length > 160 ? a.systemPrompt.slice(0, 160) + '…' : a.systemPrompt;
    h += '<div class="card-detail"><strong>Prompt:</strong> <span class="prompt-preview">' + esc(prev) + '</span></div>';
  }
  return h;
}

function renderAgentCards(containerId, agents, canDelete) {
  const el = document.getElementById(containerId);
  const entries = Object.entries(agents);
  if (!entries.length) {
    el.innerHTML = '<div class="empty-hint">' + (canDelete ? 'No custom agents defined' : 'Default config not set') + '</div>';
    return;
  }
  el.innerHTML = entries.map(([name, a]) => {
    const isDefault = name === 'defaults';
    const badge = isDefault
      ? '<span class="badge badge-default">default</span>'
      : '<span class="badge badge-agent">agent</span>';
    return '<div class="card">' +
      '<div class="card-head"><span class="card-name">' + esc(name) + '</span>' + badge + '</div>' +
      agentSummaryHtml(a) +
      '<div class="card-actions">' +
        '<button class="btn btn-secondary btn-sm" onclick=\'openAgentModal(' + JSON.stringify(name) + ')\'>Edit</button>' +
        (canDelete ? '<button class="btn btn-danger btn-sm" onclick=\'deleteAgent(' + JSON.stringify(name) + ')\'>Delete</button>' : '') +
      '</div></div>';
  }).join('');
}

async function openAgentModal(editName) {
  let agent = {};
  if (editName !== null) {
    try {
      const r = await fetch(apiUrl('/api/config'));
      const cfg = await r.json();
      agent = (cfg.agents || {})[editName] || {};
    } catch(e) { showMsg('Failed to load agent: ' + e.message, false); return; }
  }
  const isNew = editName === null;
  const ct = document.getElementById('agentModalCt');
  ct.style.display = '';

  const nameRow = isNew
    ? '<div class="fg"><label>Name *</label><input id="ag-name" placeholder="my-agent"><div class="hint">Letters, numbers, hyphens, underscores. Cannot be "defaults".</div></div>'
    : '<div class="fg"><label>Name</label><input id="ag-name" value="' + esc(editName) + '" readonly></div>';

  ct.innerHTML =
    '<div class="modal-bg" onclick="if(event.target===this)closeAgentModal()">' +
    '<div class="modal-box">' +
      '<h3>' + (isNew ? 'New Agent' : 'Edit Agent: ' + esc(editName)) + '</h3>' +
      nameRow +
      '<div class="fg"><label>Model</label><input id="ag-model" value="' + esc(agent.model || '') + '" placeholder="provider/model-name"><div class="hint">e.g. zai/glm-4-flash, gpt-4o, claude-sonnet-4-6, anthropic/claude-3-5-sonnet</div></div>' +
      '<div class="fg"><label>System Prompt</label><textarea id="ag-prompt" rows="7" placeholder="You are a helpful assistant...">' + esc(agent.systemPrompt || '') + '</textarea></div>' +
      '<div class="two-col">' +
        '<div class="fg"><label>Max Tokens</label><input id="ag-maxtokens" type="number" min="1" value="' + (agent.maxTokens != null ? agent.maxTokens : '') + '" placeholder="8192"></div>' +
        '<div class="fg"><label>Temperature</label><input id="ag-temp" type="number" step="0.1" min="0" max="2" value="' + (agent.temperature != null ? agent.temperature : '') + '" placeholder="0.7"></div>' +
      '</div>' +
      '<div class="two-col">' +
        '<div class="fg"><label>Tool Iterations</label><input id="ag-maxiter" type="number" min="1" value="' + (agent.maxToolIterations != null ? agent.maxToolIterations : '') + '" placeholder="20"><div class="hint">Max tool calls per turn</div></div>' +
        '<div class="fg"><label>Memory Window</label><input id="ag-memwin" type="number" min="1" value="' + (agent.memoryWindow != null ? agent.memoryWindow : '') + '" placeholder="50"><div class="hint">Messages kept in context</div></div>' +
      '</div>' +
      '<div class="fg"><label>Workspace</label><input id="ag-workspace" value="' + esc(agent.workspace || '') + '" placeholder="/config/nanobot/workspace"><div class="hint">Working directory for file operations</div></div>' +
      '<div class="modal-footer">' +
        '<button class="btn btn-secondary" onclick="closeAgentModal()">Cancel</button>' +
        '<button class="btn btn-primary" onclick=\'saveAgent(' + JSON.stringify(editName) + ',' + isNew + ')\'>Save</button>' +
      '</div>' +
    '</div></div>';
}

function closeAgentModal() {
  const c = document.getElementById('agentModalCt');
  c.style.display = 'none'; c.innerHTML = '';
}

async function saveAgent(originalName, isNew) {
  const nameVal    = document.getElementById('ag-name').value.trim();
  const model      = document.getElementById('ag-model').value.trim();
  const prompt     = document.getElementById('ag-prompt').value.trim();
  const maxTokens  = document.getElementById('ag-maxtokens').value.trim();
  const temp       = document.getElementById('ag-temp').value.trim();
  const maxIter    = document.getElementById('ag-maxiter').value.trim();
  const memWin     = document.getElementById('ag-memwin').value.trim();
  const workspace  = document.getElementById('ag-workspace').value.trim();

  if (isNew) {
    if (!nameVal) { showMsg('Name is required', false); return; }
    if (!/^[a-zA-Z0-9_-]+$/.test(nameVal)) { showMsg('Name: only letters, numbers, hyphens, underscores', false); return; }
    if (nameVal === 'defaults') { showMsg('Use the "defaults" entry to edit default settings', false); return; }
  }

  const agentName = isNew ? nameVal : originalName;
  const agent = {};
  if (model)    agent.model = model;
  if (prompt)   agent.systemPrompt = prompt;
  if (maxTokens) agent.maxTokens = parseInt(maxTokens, 10);
  if (temp !== '') agent.temperature = parseFloat(temp);
  if (maxIter)  agent.maxToolIterations = parseInt(maxIter, 10);
  if (memWin)   agent.memoryWindow = parseInt(memWin, 10);
  if (workspace) agent.workspace = workspace;

  try {
    const r = await fetch(apiUrl('/api/config'));
    const cfg = await r.json();
    if (!cfg.agents) cfg.agents = {};
    cfg.agents[agentName] = agent;
    const r2 = await fetch(apiUrl('/api/config'), {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(cfg, null, 2)
    });
    if (r2.ok) {
      showMsg('Agent "' + agentName + '" saved. Restart addon to apply.', true);
      closeAgentModal(); loadAgents();
    } else showMsg('Failed to save: ' + r2.statusText, false);
  } catch(e) { showMsg('Error: ' + e.message, false); }
}

async function deleteAgent(name) {
  if (!confirm('Delete agent "' + name + '"?')) return;
  try {
    const r = await fetch(apiUrl('/api/config'));
    const cfg = await r.json();
    if (cfg.agents) delete cfg.agents[name];
    const r2 = await fetch(apiUrl('/api/config'), {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(cfg, null, 2)
    });
    if (r2.ok) { showMsg('Agent "' + name + '" deleted. Restart to apply.', true); loadAgents(); }
    else showMsg('Delete failed: ' + r2.statusText, false);
  } catch(e) { showMsg('Error: ' + e.message, false); }
}

// ── MCP Servers ──────────────────────────────────────────────────

const BUILTIN_SERVERS = ['homeassistant', 'exchange'];

async function loadMcpServers() {
  try {
    const r = await fetch(apiUrl('/api/config'));
    const cfg = await r.json();
    const servers = (cfg.tools && cfg.tools.mcpServers) || {};
    const builtin = [], custom = [];
    for (const [name, srv] of Object.entries(servers)) {
      const entry = { name, command: srv.command || '', args: srv.args || [], env: srv.env || {} };
      (BUILTIN_SERVERS.includes(name) ? builtin : custom).push(entry);
    }
    renderMcpCards('builtinList', builtin, false);
    renderMcpCards('customList', custom, true);
    document.getElementById('mcpStatus').textContent = Object.keys(servers).length + ' servers';
  } catch(e) { showMsg('Failed to load MCP servers: ' + e.message, false); }
}

function mcpEnvHtml(env) {
  const keys = Object.keys(env);
  if (!keys.length) return '';
  const rows = keys.map(k => {
    const isSensitive = /password|token|secret|key/i.test(k);
    const val = isSensitive ? '••••••••' : esc(env[k]);
    return '<tr><td style="color:#888;padding-right:8px;white-space:nowrap">' + esc(k) + '</td><td style="color:#555">' + val + '</td></tr>';
  }).join('');
  return '<div class="card-detail" style="margin-top:4px"><strong>Env:</strong><table style="font-size:12px;font-family:monospace;margin-top:2px;border-collapse:collapse">' + rows + '</table></div>';
}

function renderMcpCards(containerId, servers, canDelete) {
  const el = document.getElementById(containerId);
  if (!servers.length) {
    el.innerHTML = '<div class="empty-hint">No servers configured</div>';
    return;
  }
  el.innerHTML = servers.map(s => {
    const badge = canDelete
      ? '<span class="badge">custom</span>'
      : '<span class="badge badge-builtin">built-in</span>';
    const argsHtml = s.args.length
      ? '<div class="card-detail"><strong>Args:</strong> <code>' + esc(s.args.join(' ')) + '</code></div>'
      : '';
    return '<div class="card">' +
      '<div class="card-head"><span class="card-name">' + esc(s.name) + '</span>' + badge + '</div>' +
      '<div class="card-detail"><strong>Command:</strong> <code>' + esc(s.command) + '</code></div>' +
      argsHtml +
      mcpEnvHtml(s.env) +
      '<div class="card-actions">' +
        '<button class="btn btn-secondary btn-sm" onclick=\'openMcpModal(' + JSON.stringify(s.name) + ')\'>Edit</button>' +
        (canDelete ? '<button class="btn btn-danger btn-sm" onclick=\'deleteMcpServer(' + JSON.stringify(s.name) + ')\'>Delete</button>' : '') +
      '</div></div>';
  }).join('');
}

async function openMcpModal(editName) {
  let srv = { command: '', args: [], env: {} };
  if (editName !== null) {
    try {
      const r = await fetch(apiUrl('/api/config'));
      const cfg = await r.json();
      const s = ((cfg.tools || {}).mcpServers || {})[editName] || {};
      srv = { command: s.command || '', args: s.args || [], env: s.env || {} };
    } catch(e) { showMsg('Failed to load server: ' + e.message, false); return; }
  }
  const isNew = editName === null;
  const envStr = Object.entries(srv.env).map(([k, v]) => k + '=' + v).join('\\n');
  const ct = document.getElementById('mcpModalCt');
  ct.style.display = '';

  const nameRow = isNew
    ? '<div class="fg"><label>Name *</label><input id="mcp-name" placeholder="my-server"><div class="hint">Letters, numbers, hyphens, underscores</div></div>'
    : '<div class="fg"><label>Name</label><input id="mcp-name" value="' + esc(editName) + '" readonly></div>';

  const builtinNote = (!isNew && BUILTIN_SERVERS.includes(editName))
    ? '<div style="background:#fff3e0;color:#e65100;font-size:12px;padding:8px 10px;border-radius:4px;margin-bottom:12px">⚠ Built-in server — changes will override the auto-generated config on next restart.</div>'
    : '';

  ct.innerHTML =
    '<div class="modal-bg" onclick="if(event.target===this)closeMcpModal()">' +
    '<div class="modal-box">' +
      '<h3>' + (isNew ? 'Add MCP Server' : 'Edit: ' + esc(editName)) + '</h3>' +
      builtinNote +
      nameRow +
      '<div class="fg"><label>Command *</label><input id="mcp-cmd" value="' + esc(srv.command) + '" placeholder="/usr/bin/mcp-server"><div class="hint">Full path to the MCP server binary or executable</div></div>' +
      '<div class="fg"><label>Arguments</label><input id="mcp-args" value="' + esc(srv.args.join(' ')) + '" placeholder="--transport=streamablehttp --stateless https://..."><div class="hint">Space-separated arguments</div></div>' +
      '<div class="fg"><label>Environment Variables</label><textarea id="mcp-env" rows="6" placeholder="API_ACCESS_TOKEN=abc123&#10;BASE_URL=https://example.com">' + esc(envStr) + '</textarea><div class="hint">One per line: KEY=value. Sensitive values are masked in the list but stored as-is.</div></div>' +
      '<div class="modal-footer">' +
        '<button class="btn btn-secondary" onclick="closeMcpModal()">Cancel</button>' +
        '<button class="btn btn-primary" onclick=\'saveMcpServer(' + JSON.stringify(editName) + ',' + isNew + ')\'>Save</button>' +
      '</div>' +
    '</div></div>';
}

function closeMcpModal() {
  const c = document.getElementById('mcpModalCt');
  c.style.display = 'none'; c.innerHTML = '';
}

async function saveMcpServer(originalName, isNew) {
  const nameVal = document.getElementById('mcp-name').value.trim();
  const cmd     = document.getElementById('mcp-cmd').value.trim();
  const argsStr = document.getElementById('mcp-args').value.trim();
  const envStr  = document.getElementById('mcp-env').value.trim();

  if (isNew) {
    if (!nameVal) { showMsg('Name is required', false); return; }
    if (!/^[a-zA-Z0-9_-]+$/.test(nameVal)) { showMsg('Name: only letters, numbers, hyphens, underscores', false); return; }
  }
  if (!cmd) { showMsg('Command is required', false); return; }

  const args = argsStr ? argsStr.trim().split(/\\s+/) : [];
  const env = {};
  if (envStr) {
    for (const line of envStr.split('\\n')) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const eq = trimmed.indexOf('=');
      if (eq > 0) env[trimmed.slice(0, eq).trim()] = trimmed.slice(eq + 1);
    }
  }

  const srvName = isNew ? nameVal : originalName;
  try {
    const r = await fetch(apiUrl('/api/config'));
    const cfg = await r.json();
    if (!cfg.tools) cfg.tools = {};
    if (!cfg.tools.mcpServers) cfg.tools.mcpServers = {};
    cfg.tools.mcpServers[srvName] = { command: cmd, args, env };
    const r2 = await fetch(apiUrl('/api/config'), {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(cfg, null, 2)
    });
    if (r2.ok) {
      showMsg('Server "' + srvName + '" saved. Restart addon to apply.', true);
      closeMcpModal(); loadMcpServers();
    } else showMsg('Failed to save: ' + r2.statusText, false);
  } catch(e) { showMsg('Error: ' + e.message, false); }
}

async function deleteMcpServer(name) {
  if (!confirm('Delete MCP server "' + name + '"?')) return;
  try {
    const r = await fetch(apiUrl('/api/config'));
    const cfg = await r.json();
    if (cfg.tools && cfg.tools.mcpServers) delete cfg.tools.mcpServers[name];
    const r2 = await fetch(apiUrl('/api/config'), {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(cfg, null, 2)
    });
    if (r2.ok) { showMsg('Server "' + name + '" deleted. Restart to apply.', true); loadMcpServers(); }
    else showMsg('Delete failed: ' + r2.statusText, false);
  } catch(e) { showMsg('Error: ' + e.message, false); }
}

// ── Init ─────────────────────────────────────────────────────────
loadConfig();
setInterval(() => {
  if (document.getElementById('panel-logs').classList.contains('active')) loadLogs();
}, 5000);
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
