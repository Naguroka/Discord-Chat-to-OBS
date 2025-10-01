from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import Deque, Dict

import discord
from aiohttp import web

from .client import ChatRelayClient
from .config import Settings, load_settings
from .logging_utils import configure_logging
from .messages import MessagePayload
from .web import build_web_app

log = logging.getLogger("discord_chat_to_obs.runner")


def build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    return intents


async def run(settings: Settings | None = None) -> None:
    configure_logging()

    if settings is None:
        try:
            settings = load_settings()
        except RuntimeError as err:
            log.critical(str(err))
            raise

    log.info("OBS channel: %s | Embed channel: %s", settings.obs_channel_id, settings.embed_channel_id)

    history_obs: Deque[MessagePayload] = deque(maxlen=settings.history_size)
    if settings.embed_channel_id == settings.obs_channel_id:
        history_embed = history_obs
    else:
        history_embed = deque(maxlen=settings.history_size)

    histories: Dict[str, Deque[MessagePayload]] = {
        "obs": history_obs,
        "embed": history_embed,
    }

    channel_mapping: Dict[int, str] = {settings.obs_channel_id: "obs"}
    if settings.embed_channel_id != settings.obs_channel_id:
        channel_mapping[settings.embed_channel_id] = "embed"

    client = ChatRelayClient(
        channel_mapping=channel_mapping,
        histories=histories,
        intents=build_intents(),
    )
    app = build_web_app(histories)

    shutdown_event = asyncio.Event()
    web_task = asyncio.create_task(
        _run_web_app(app, host=settings.host, port=settings.port, shutdown_event=shutdown_event)
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


def main() -> None:
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("Shutdown requested by user")
    except RuntimeError:
        pass
    except Exception:
        log.exception("Fatal error")


async def _run_web_app(app: web.Application, *, host: str, port: int, shutdown_event: asyncio.Event) -> None:
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
