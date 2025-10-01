from __future__ import annotations

from typing import Deque, Dict, Iterable, Mapping

from aiohttp import web
from time import time

from .messages import MessagePayload
from .paths import ASSETS_DIR, ensure_static_dir


def cors_headers() -> Dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }


def _serialise_history(history: Iterable[MessagePayload]) -> list[MessagePayload]:
    return [dict(item) for item in history]


def build_web_app(histories: Mapping[str, Deque[MessagePayload]]) -> web.Application:
    static_dir = ensure_static_dir()
    index_path = static_dir / "index.html"
    styles_path = static_dir / "styles.css"
    embed_script_path = static_dir / "embed.js"
    scripts_dir = static_dir / "scripts"

    build_rev = str(int(time()))

    history_obs = histories.get("obs")
    if history_obs is None and histories:
        history_obs = next(iter(histories.values()))
    history_embed = histories.get("embed", history_obs)

    async def handle_chat(request: web.Request) -> web.Response:
        if _wants_html(request):
            return await handle_index(request)
        target = (
            request.rel_url.query.get("target")
            or request.rel_url.query.get("feed")
            or request.rel_url.query.get("variant")
            or ""
        ).lower()
        selected = history_embed if target == "embed" else history_obs
        if selected is None:
            return web.json_response([], headers=cors_headers())
        return web.json_response(_serialise_history(selected), headers=cors_headers())

    async def handle_embed_chat(request: web.Request) -> web.Response:
        if history_embed is None:
            return web.json_response([], headers=cors_headers())
        return web.json_response(_serialise_history(history_embed), headers=cors_headers())

    async def handle_index(request: web.Request) -> web.StreamResponse:
        if not index_path.exists():
            raise web.HTTPNotFound(text="index.html is missing from the web/ directory")
        # Add a version query to break caches whenever the service restarts.
        text = index_path.read_text(encoding="utf-8")
        text = text.replace("styles.css", f"styles.css?v={build_rev}")
        text = text.replace("scripts/main.js", f"scripts/main.js?v={build_rev}")
        return web.Response(text=text, content_type="text/html", headers={**cors_headers(), "Cache-Control": "no-store"})

    async def handle_styles(request: web.Request) -> web.StreamResponse:
        return web.FileResponse(styles_path, headers={**cors_headers(), "Cache-Control": "no-store"})

    async def handle_embed_script(request: web.Request) -> web.StreamResponse:
        return web.FileResponse(embed_script_path, headers={**cors_headers(), "Cache-Control": "no-store"})

    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/index.html", handle_index)
    app.router.add_get("/chat", handle_chat)
    app.router.add_options("/chat", _handle_options)
    app.router.add_get("/embed-chat", handle_embed_chat)
    app.router.add_options("/embed-chat", _handle_options)
    app.router.add_get("/styles.css", handle_styles)
    app.router.add_get("/embed.js", handle_embed_script)

    if scripts_dir.exists():
        app.router.add_static("/scripts", str(scripts_dir), show_index=False)
    if ASSETS_DIR.exists():
        app.router.add_static("/assets", str(ASSETS_DIR), show_index=False)

    return app


async def _handle_options(request: web.Request) -> web.Response:
    return web.Response(headers=cors_headers())


def _wants_html(request: web.Request) -> bool:
    accept = (request.headers.get("Accept") or "*/*").lower()
    if request.headers.get("Sec-Fetch-Dest") == "document":
        return True
    json_markers = ("application/json", "application/ld+json", "application/vnd.api+json", "text/json")
    return not any(marker in accept for marker in json_markers)
