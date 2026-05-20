#!/usr/bin/env python3
"""HA Ingress → nanobot WebUI reverse proxy.

Why this exists:

The nanobot WebUI (bundled with nanobot-ai) requires that `/webui/bootstrap`
either come from `localhost`, or carry an `Authorization: Bearer <secret>`
header matching `channels.websocket.token_issue_secret`. The Home Assistant
Supervisor's Ingress proxy is in a different network namespace, so its
connections appear to nanobot as non-loopback IPs and it has no way to
inject auth headers per-addon. To bridge that, this script:

  1. Listens on 0.0.0.0:INGRESS_PORT (the addon's `ingress_port`).
  2. Accepts only requests that look like they came from HA Ingress:
     either carrying the `X-Ingress-Path` header, or originating from the
     known Supervisor docker-bridge range. Everything else → 403.
  3. Forwards the request to nanobot on 127.0.0.1:NANOBOT_PORT, adding
     `Authorization: Bearer <secret>` so `/webui/bootstrap` succeeds. The
     short-lived `nbwt_…` token nanobot issues then carries through to the
     `/api/*` and WebSocket handshake requests automatically (the WebUI
     client passes it as the `?token=` query parameter / Bearer header).
  4. Transparently upgrades to a WebSocket relay when the client asks for it.

Nanobot itself stays bound to 127.0.0.1, so the WebUI is unreachable from
the LAN; the only entrypoint is HA Ingress, which is gated by Home
Assistant's own authentication.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import os
import re
import secrets
from typing import Iterable

from aiohttp import (
    ClientSession,
    ClientTimeout,
    ClientWebSocketResponse,
    WSMessage,
    WSMsgType,
    web,
)

# --- Configuration ----------------------------------------------------------

INGRESS_HOST = os.environ.get("INGRESS_PROXY_HOST", "0.0.0.0")
INGRESS_PORT = int(os.environ.get("INGRESS_PROXY_PORT", "8099"))
NANOBOT_HOST = os.environ.get("NANOBOT_WS_HOST", "127.0.0.1")
NANOBOT_PORT = int(os.environ.get("NANOBOT_WS_PORT", "8765"))
SECRET_FILE = os.environ.get("PROXY_SECRET_FILE", "/data/.nanobot/proxy_secret")

# HA Supervisor's docker bridge network. Connections from this range plus the
# loopback are treated as "from Ingress". The standard hassio docker network
# is 172.30.32.0/23; we also allow 127.0.0.0/8 for host-network setups where
# Supervisor's nginx talks to the addon over loopback.
TRUSTED_NETWORKS: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...] = (
    ipaddress.ip_network("172.30.32.0/23"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
)

# Headers HA Supervisor always sets when proxying via Ingress. Presence of any
# one of these is a strong signal the request actually came from Ingress and
# not a random LAN client poking the port directly.
INGRESS_MARKER_HEADERS = ("X-Ingress-Path", "X-Hass-Source")

# Hop-by-hop headers that must not be forwarded (RFC 7230 §6.1).
HOP_BY_HOP = frozenset({
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailer", "transfer-encoding", "upgrade",
})

# Endpoints that need the secret injected as Authorization: Bearer <secret>.
# Everything else either uses an issued `nbwt_…` token from the client (which
# we forward unchanged) or is public static content.
SECRET_AUTH_PATHS = ("/webui/bootstrap",)

logger = logging.getLogger("ingress_proxy")


# --- Helpers ---------------------------------------------------------------

def _load_secret() -> str:
    """Read the shared secret from disk; generate one if missing.

    The secret must match `channels.websocket.token_issue_secret` in nanobot's
    runtime config. `generate_config.py` writes the same value to both this
    file and the runtime config on every addon boot.
    """
    if os.path.exists(SECRET_FILE):
        with open(SECRET_FILE, "r") as f:
            value = f.read().strip()
        if value:
            return value
    # Cold start: generate and persist.
    value = secrets.token_urlsafe(32)
    os.makedirs(os.path.dirname(SECRET_FILE), exist_ok=True)
    with open(SECRET_FILE, "w") as f:
        f.write(value)
    os.chmod(SECRET_FILE, 0o600)
    return value


def _is_from_ingress(request: web.Request) -> bool:
    """Return True if the request looks like it came from HA Supervisor's Ingress.

    Strict rule: a request must carry one of the Ingress marker headers AND
    arrive from a trusted source IP (Supervisor's bridge or the host loopback,
    in case Supervisor's nginx runs in host mode). Either check on its own is
    spoofable from the LAN — the marker headers because anyone can set HTTP
    headers, the IP check because the addon listens on 0.0.0.0 — so we require
    both.
    """
    if not any(header in request.headers for header in INGRESS_MARKER_HEADERS):
        return False
    peer = request.transport.get_extra_info("peername") if request.transport else None
    if not peer:
        return False
    try:
        ip = ipaddress.ip_address(peer[0])
    except ValueError:
        return False
    return any(ip in net for net in TRUSTED_NETWORKS)


def _filter_headers(headers: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    """Strip hop-by-hop headers; keep everything else."""
    return [(k, v) for k, v in headers if k.lower() not in HOP_BY_HOP]


def _needs_secret_injection(path: str) -> bool:
    return any(path == p or path.startswith(p + "?") for p in SECRET_AUTH_PATHS)


# Absolute-path prefixes the SPA bakes into its HTML/JS/CSS that must be
# rewritten back through the Ingress URL. Matched only when immediately
# preceded by a string/template-literal boundary (`"`, `'`, `` ` ``, or `}`
# from `${…}` interpolation close) to avoid hitting unrelated `/`-prefixed
# substrings.
_ABS_PATH_DIRS = ("assets", "brand", "api", "webui")

_ABS_PATH_RE = re.compile(
    rb"(?P<boundary>[\"'`}])/(?P<dir>"
    + b"|".join(d.encode() for d in _ABS_PATH_DIRS)
    + rb")/"
)

# Content types whose bodies we buffer + rewrite. JS bundle ~550 kB, HTML
# shell ~6 kB, CSS small — all fine to load fully.
_REWRITABLE_TYPES = (
    "text/html",
    "text/javascript",
    "application/javascript",
    "text/css",
)


def _is_rewritable(content_type: str) -> bool:
    ct = content_type.lower().split(";", 1)[0].strip()
    return ct in _REWRITABLE_TYPES


def _rewrite_paths(body: bytes, content_type: str, ingress_prefix: str) -> bytes:
    """Inject the Ingress prefix into baked-in absolute paths.

    - For every `<boundary>/<dir>/…` occurrence (where boundary is `"`, `'`,
      `` ` ``, or `}`), rewrite `/<dir>/` → `{prefix}/<dir>/`.
    - For HTML responses only, additionally inject `<base href="{prefix}/">`
      right after `<head>` so anything still using relative URLs (or
      `document.baseURI`) resolves against the Ingress URL too. The base tag
      is added after the regex pass so it isn't itself rewritten.
    """
    prefix = ingress_prefix.rstrip("/").encode("utf-8")
    if not prefix:
        return body

    def _sub(m: re.Match) -> bytes:
        return m.group("boundary") + prefix + b"/" + m.group("dir") + b"/"

    out = _ABS_PATH_RE.sub(_sub, body)

    if content_type.lower().startswith("text/html") and b"<base " not in out:
        base_tag = b'<head><base href="' + prefix + b'/">'
        out = out.replace(b"<head>", base_tag, 1)

    return out


# --- HTTP proxy ------------------------------------------------------------

async def _proxy_http(request: web.Request, secret: str) -> web.StreamResponse:
    client: ClientSession = request.app["client"]

    upstream_url = f"http://{NANOBOT_HOST}:{NANOBOT_PORT}{request.rel_url}"

    fwd_headers = _filter_headers(request.headers.items())
    if _needs_secret_injection(request.path):
        # Replace any pre-existing Authorization to make sure the bootstrap
        # uses our shared secret rather than a stale client-supplied value.
        fwd_headers = [(k, v) for k, v in fwd_headers if k.lower() != "authorization"]
        fwd_headers.append(("Authorization", f"Bearer {secret}"))

    body = await request.read() if request.body_exists else None
    ingress_prefix = request.headers.get("X-Ingress-Path", "").strip()

    async with client.request(
        request.method,
        upstream_url,
        headers=fwd_headers,
        data=body,
        allow_redirects=False,
        timeout=ClientTimeout(total=120),
    ) as upstream:
        upstream_ct = upstream.headers.get("Content-Type", "")
        should_rewrite = ingress_prefix and _is_rewritable(upstream_ct)

        if should_rewrite:
            # Buffer the full body to rewrite paths; re-emit with new
            # Content-Length and without the upstream's content-encoding
            # (aiohttp transparently decompresses, so we send plain bytes).
            raw = await upstream.read()
            patched = _rewrite_paths(raw, upstream_ct, ingress_prefix)
            out_headers = []
            for k, v in _filter_headers(upstream.headers.items()):
                lk = k.lower()
                if lk in ("content-length", "content-encoding"):
                    continue
                out_headers.append((k, v))
            out_headers.append(("Content-Length", str(len(patched))))
            return web.Response(
                body=patched,
                status=upstream.status,
                reason=upstream.reason,
                headers=dict(out_headers),
            )

        response = web.StreamResponse(
            status=upstream.status,
            reason=upstream.reason,
            headers=_filter_headers(upstream.headers.items()),
        )
        await response.prepare(request)
        async for chunk in upstream.content.iter_chunked(64 * 1024):
            await response.write(chunk)
        await response.write_eof()
        return response


# --- WebSocket proxy -------------------------------------------------------

async def _pump_client_to_upstream(
    ws_client: web.WebSocketResponse,
    ws_upstream: ClientWebSocketResponse,
) -> None:
    async for msg in ws_client:
        if msg.type == WSMsgType.TEXT:
            await ws_upstream.send_str(msg.data)
        elif msg.type == WSMsgType.BINARY:
            await ws_upstream.send_bytes(msg.data)
        elif msg.type == WSMsgType.CLOSE:
            break


async def _pump_upstream_to_client(
    ws_client: web.WebSocketResponse,
    ws_upstream: ClientWebSocketResponse,
) -> None:
    async for msg in ws_upstream:
        if msg.type == WSMsgType.TEXT:
            await ws_client.send_str(msg.data)
        elif msg.type == WSMsgType.BINARY:
            await ws_client.send_bytes(msg.data)
        elif msg.type == WSMsgType.CLOSE:
            break


async def _proxy_websocket(request: web.Request) -> web.WebSocketResponse:
    client: ClientSession = request.app["client"]
    ws_client = web.WebSocketResponse(autoping=False, max_msg_size=40 * 1024 * 1024)
    await ws_client.prepare(request)

    upstream_url = f"ws://{NANOBOT_HOST}:{NANOBOT_PORT}{request.rel_url}"
    # Pass through the client's WS subprotocols and a minimal set of headers.
    upstream_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP
        and k.lower() not in ("host", "sec-websocket-key", "sec-websocket-version",
                              "sec-websocket-extensions", "sec-websocket-protocol")
    }

    try:
        async with client.ws_connect(
            upstream_url,
            headers=upstream_headers,
            heartbeat=20,
            max_msg_size=40 * 1024 * 1024,
        ) as ws_upstream:
            await asyncio.gather(
                _pump_client_to_upstream(ws_client, ws_upstream),
                _pump_upstream_to_client(ws_client, ws_upstream),
                return_exceptions=True,
            )
    except Exception as exc:
        logger.warning("WebSocket upstream failed: %s", exc)
    finally:
        if not ws_client.closed:
            await ws_client.close()
    return ws_client


# --- Request dispatcher ----------------------------------------------------

async def _handle(request: web.Request) -> web.StreamResponse:
    if not _is_from_ingress(request):
        return web.Response(status=403, text="403: not from HA Ingress")

    upgrade = request.headers.get("Upgrade", "").lower()
    if upgrade == "websocket":
        return await _proxy_websocket(request)
    return await _proxy_http(request, request.app["secret"])


# --- App lifecycle ---------------------------------------------------------

async def _on_startup(app: web.Application) -> None:
    app["secret"] = _load_secret()
    app["client"] = ClientSession()


async def _on_cleanup(app: web.Application) -> None:
    await app["client"].close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | ingress_proxy | %(message)s",
    )
    app = web.Application()
    app.on_startup.append(_on_startup)
    app.on_cleanup.append(_on_cleanup)
    app.router.add_route("*", "/{path:.*}", _handle)
    logger.info(
        "Starting on %s:%d → forwarding to %s:%d",
        INGRESS_HOST, INGRESS_PORT, NANOBOT_HOST, NANOBOT_PORT,
    )
    web.run_app(app, host=INGRESS_HOST, port=INGRESS_PORT, access_log=None)


if __name__ == "__main__":
    main()
