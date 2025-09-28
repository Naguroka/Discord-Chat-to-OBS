"""Discord channel bridge that relays messages to a local web endpoint for OBS overlays."""

from __future__ import annotations

import asyncio
import logging
import os
from collections import deque
from dataclasses import dataclass
from pathlib import Path as SysPath
from typing import Deque, Dict

import discord
from aiohttp import web

log = logging.getLogger("discord_chat_to_obs")


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def load_env_file(path: SysPath = SysPath(".env")) -> None:
    """Populate environment variables from a simple .env file if present."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Environment variable '{name}' is required. See README for setup details."
        )
    return value


def parse_int_env(name: str, default: int, *, minimum: int | None = None) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        parsed = int(raw_value)
    except ValueError as err:
        raise RuntimeError(f"Environment variable '{name}' must be an integer.") from err

    if minimum is not None and parsed < minimum:
        raise RuntimeError(f"Environment variable '{name}' must be >= {minimum}.")

    return parsed


@dataclass(frozen=True)
class Settings:
    token: str
    channel_id: int
    host: str = "127.0.0.1"
    port: int = 8080
    history_size: int = 200


def load_settings() -> Settings:
    load_env_file()

    token = require_env("DISCORD_BOT_TOKEN")
    channel_id_raw = require_env("DISCORD_CHANNEL_ID")
    try:
        channel_id = int(channel_id_raw)
    except ValueError as err:
        raise RuntimeError("DISCORD_CHANNEL_ID must be an integer.") from err

    host = os.getenv("CHAT_API_HOST", "127.0.0.1")
    port = parse_int_env("CHAT_API_PORT", 8080, minimum=1)
    history_size = parse_int_env("CHAT_HISTORY_SIZE", 200, minimum=1)

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
        if message.attachments:
            attachment_urls = "\n".join(attachment.url for attachment in message.attachments)
            content = f"{content}\n{attachment_urls}" if content else attachment_urls

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
        return web.json_response(list(history), headers=cors_headers())

    async def handle_options(request: web.Request) -> web.Response:
        return web.Response(headers=cors_headers())

    app = web.Application()
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
