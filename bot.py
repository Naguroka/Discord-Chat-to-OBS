"""Discord channel bridge that relays messages to a local web endpoint for OBS overlays."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Deque, Dict, Mapping

import discord
from aiohttp import web

log = logging.getLogger("discord_chat_to_obs")

SETTINGS_PATH = Path("settings.ini")
BASE_DIR = Path(__file__).parent
CUSTOM_EMOJI_DIR = BASE_DIR / "customEmojis"


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def load_settings_file(path: Path) -> Dict[str, str]:
    if not path.exists():
        raise RuntimeError(
            "settings.ini is missing. Copy settings.ini.example, fill it in, and rerun the bot."
        )

    result: Dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip().strip('"').strip("'")
    return result


def get_setting(store: Mapping[str, str], key: str, *, default: str | None = None) -> str | None:
    value = store.get(key)
    if value:
        return value
    env_value = os.getenv(key)
    if env_value:
        return env_value
    return default


def require_setting(store: Mapping[str, str], key: str) -> str:
    value = get_setting(store, key)
    if not value:
        raise RuntimeError(
            f"Configuration value '{key}' is required. See README for setup details."
        )
    return value


def parse_int(value: str, key: str, *, minimum: int | None = None) -> int:
    try:
        parsed = int(value)
    except ValueError as err:
        raise RuntimeError(f"Configuration value '{key}' must be an integer.") from err

    if minimum is not None and parsed < minimum:
        raise RuntimeError(f"Configuration value '{key}' must be >= {minimum}.")
    return parsed


@dataclass(frozen=True)
class Settings:
    token: str
    channel_id: int
    host: str = "127.0.0.1"
    port: int = 8080
    history_size: int = 200


def load_settings() -> Settings:
    store = load_settings_file(SETTINGS_PATH)

    token = require_setting(store, "DISCORD_BOT_TOKEN")
    channel_id_raw = require_setting(store, "DISCORD_CHANNEL_ID")
    channel_id = parse_int(channel_id_raw, "DISCORD_CHANNEL_ID", minimum=1)

    host = get_setting(store, "CHAT_API_HOST", default="127.0.0.1") or "127.0.0.1"
    port_raw = get_setting(store, "CHAT_API_PORT", default="8080") or "8080"
    port = parse_int(port_raw, "CHAT_API_PORT", minimum=1)

    history_raw = get_setting(store, "CHAT_HISTORY_SIZE", default="200") or "200"
    history_size = parse_int(history_raw, "CHAT_HISTORY_SIZE", minimum=1)

    return Settings(token=token, channel_id=channel_id, host=host, port=port, history_size=history_size)


def build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    return intents


MessagePayload = Dict[str, str]


class ChatRelayClient(discord.Client):
    def __init__(self, *, channel_id: int, history: Deque[MessagePayload], **kwargs) -> None:
        super().__init__(**kwargs)
        self._channel_id = channel_id
        self._history = history

    async def on_ready(self) -> None:
        if self.user:
            log.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        else:
            log.info("Logged in, but user information is unavailable.")

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return
        if message.channel.id != self._channel_id:
            return

        content = message.clean_content

        media_items: list[dict[str, str]] = []
        seen_media: set[str] = set()
        urls_to_strip: set[str] = set()

        def normalize(url: str) -> str:
            return url.split("?", 1)[0].lower()

        def remember_url(url: str | None) -> None:
            if not url:
                return
            urls_to_strip.add(url)
            urls_to_strip.add(normalize(url))

        def add_media(url: str | None, media_type: str, *, source_url: str | None = None) -> bool:
            if not url:
                return False
            normalized = normalize(url)
            if normalized in seen_media:
                return False
            seen_media.add(normalized)
            media_items.append({"type": media_type, "url": url})
            remember_url(url)
            remember_url(source_url)
            return True

        attachment_fallback: list[str] = []
        for attachment in message.attachments:
            url = attachment.url
            content_type = (attachment.content_type or "").lower()
            lower_url = url.lower()
            handled = False
            if content_type.startswith("image/") or lower_url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
                handled = add_media(url, "image", source_url=url)
            elif content_type.startswith("video/") or lower_url.endswith((".mp4", ".mov", ".webm")):
                handled = add_media(url, "video", source_url=url)
            if not handled:
                attachment_fallback.append(url)

        for embed in message.embeds:
            media_added = False
            embed_video = getattr(embed, "video", None)
            source_url = getattr(embed, "url", None)
            if embed_video and getattr(embed_video, "url", None):
                media_added = add_media(embed_video.url, "video", source_url=source_url) or media_added
            if not media_added:
                embed_image = getattr(embed, "image", None)
                if embed_image and getattr(embed_image, "url", None):
                    media_added = add_media(embed_image.url, "image", source_url=source_url) or media_added
                embed_thumbnail = getattr(embed, "thumbnail", None)
                if embed_thumbnail and getattr(embed_thumbnail, "url", None):
                    media_added = add_media(embed_thumbnail.url, "image", source_url=source_url) or media_added

        if attachment_fallback and not media_items:
            attachment_block = "\n".join(attachment_fallback)
            content = f"{content}\n{attachment_block}" if content else attachment_block

        if media_items:
            for match in re.findall(r"https?://\S+", content or ""):
                remember_url(match)

        if urls_to_strip and content:
            for url in sorted(urls_to_strip, key=len, reverse=True):
                if not url:
                    continue
                content = content.replace(url, "")
            content = re.sub(r"\s+", " ", content).strip()
            if not content:
                content = ""

        avatar_url = str(message.author.display_avatar.url)
        display_name = message.author.display_name
        top_role = getattr(message.author, "top_role", None)
        role_color = "#99aab5"
        if top_role and getattr(top_role, "colour", None):
            colour_value = top_role.colour.value
            if colour_value:
                role_color = f"#{colour_value:06x}"
        payload = {
            "content": content,
            "author": display_name,
            "avatar_url": avatar_url,
            "role_color": role_color,
            "media": media_items,
        }
        self._history.append(payload)
        log.debug("Stored message from %s", display_name)


def cors_headers() -> Dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }


def build_web_app(history: Deque[MessagePayload]) -> web.Application:
    async def handle_chat(request: web.Request) -> web.Response:
        if wants_html(request):
            return await handle_index(request)
        return web.json_response(list(history), headers=cors_headers())

    async def handle_options(request: web.Request) -> web.Response:
        return web.Response(headers=cors_headers())

    async def handle_index(request: web.Request) -> web.StreamResponse:
        return web.FileResponse(BASE_DIR / "index.html")

    async def handle_script(request: web.Request) -> web.StreamResponse:
        return web.FileResponse(BASE_DIR / "script.js")

    async def handle_styles(request: web.Request) -> web.StreamResponse:
        return web.FileResponse(BASE_DIR / "styles.css")

    def wants_html(request: web.Request) -> bool:
        accept = (request.headers.get("Accept") or "*/*").lower()
        if request.headers.get("Sec-Fetch-Dest") == "document":
            return True
        json_markers = ("application/json", "application/ld+json", "application/vnd.api+json", "text/json")
        if any(marker in accept for marker in json_markers):
            return False
        return True

    app = web.Application()
    emoji_dir = CUSTOM_EMOJI_DIR
    emoji_dir.mkdir(parents=True, exist_ok=True)
    app.router.add_static('/customEmojis', emoji_dir)
    app.router.add_get("/", handle_index)
    app.router.add_get("/script.js", handle_script)
    app.router.add_get("/styles.css", handle_styles)
    app.router.add_get("/chat", handle_chat)
    app.router.add_options("/chat", handle_options)
    return app


async def run_web_app(app: web.Application, *, host: str, port: int, shutdown_event: asyncio.Event) -> None:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    log.info("HTTP server running at http://%s:%s/chat", host, port)

    try:
        await shutdown_event.wait()
    finally:
        await runner.cleanup()
        log.info("HTTP server shut down")


async def main() -> None:
    configure_logging()

    try:
        settings = load_settings()
    except RuntimeError as err:
        log.critical(str(err))
        raise

    history: Deque[MessagePayload] = deque(maxlen=settings.history_size)
    client = ChatRelayClient(channel_id=settings.channel_id, history=history, intents=build_intents())
    app = build_web_app(history)

    shutdown_event = asyncio.Event()
    web_task = asyncio.create_task(
        run_web_app(app, host=settings.host, port=settings.port, shutdown_event=shutdown_event)
    )

    try:
        await client.start(settings.token)
    except discord.LoginFailure as err:
        log.critical("Discord login failed: %s", err)
        raise
    except Exception:
        log.exception("Unexpected error while running the Discord client")
        raise
    finally:
        shutdown_event.set()
        await client.close()
        await web_task


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutdown requested by user")
    except RuntimeError:
        # Error already logged in main()
        pass
    except Exception:
        log.exception("Fatal error")






