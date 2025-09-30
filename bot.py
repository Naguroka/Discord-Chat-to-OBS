"""Discord channel bridge that relays messages to a local web endpoint for OBS overlays."""

from __future__ import annotations

import asyncio
import logging
import os
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Deque, Dict, Mapping

import discord
from aiohttp import web

log = logging.getLogger("discord_chat_to_obs")

SETTINGS_PATH = Path("settings.ini")
BASE_DIR = Path(__file__).parent
CUSTOM_EMOJI_PATTERN = re.compile(r"<a?:([a-zA-Z0-9_]+)(?::(\d+))?>")


def configure_logging() -> None:
    """Initialize root logging so stdout matches the configured level."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def load_settings_file(path: Path) -> Dict[str, str]:
    """Read key=value pairs from a .ini style file into a dict."""
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
    """Fetch a configuration value, falling back to environment variables."""
    value = store.get(key)
    if value:
        return value
    env_value = os.getenv(key)
    if env_value:
        return env_value
    return default


def require_setting(store: Mapping[str, str], key: str) -> str:
    """Return a mandatory config value or raise a friendly error."""
    value = get_setting(store, key)
    if not value:
        raise RuntimeError(
            f"Configuration value '{key}' is required. See README for setup details."
        )
    return value


def parse_int(value: str, key: str, *, minimum: int | None = None) -> int:
    """Convert config strings to ints and enforce optional minimums."""
    try:
        parsed = int(value)
    except ValueError as err:
        raise RuntimeError(f"Configuration value '{key}' must be an integer.") from err

    if minimum is not None and parsed < minimum:
        raise RuntimeError(f"Configuration value '{key}' must be >= {minimum}.")
    return parsed


def build_content_segments(text: str) -> list[dict[str, str | bool]]:
    """Split raw Discord text into text and custom emoji segments."""
    if not text:
        return []

    segments: list[dict[str, str | bool]] = []
    last_index = 0

    for match in CUSTOM_EMOJI_PATTERN.finditer(text):
        start, end = match.span()
        if start > last_index:
            segments.append({"type": "text", "content": text[last_index:start]})

        name = match.group(1)
        emoji_id = match.group(2)
        if emoji_id:
            segments.append({"type": "emoji", "name": name, "id": emoji_id, "animated": match.group(0).startswith('<a:')})
        else:
            segments.append({"type": "text", "content": match.group(0)})
        last_index = end

    if last_index < len(text):
        segments.append({"type": "text", "content": text[last_index:]})

    # Prune empty text segments that might appear due to adjacent emojis
    return [segment for segment in segments if segment.get('type') != 'text' or segment.get('content')]



@dataclass(frozen=True)
class Settings:
    token: str
    obs_channel_id: int
    embed_channel_id: int
    host: str = "127.0.0.1"
    port: int = 8080
    history_size: int = 200


def sticker_cdn_candidates(sticker: Any | None) -> list[dict[str, Any]]:
    """Return probable CDN URLs and metadata for a Discord sticker."""
    candidates: list[dict[str, Any]] = []
    if sticker is None:
        return candidates

    sticker_id = getattr(sticker, 'id', None)
    format_type = getattr(sticker, 'format', None) or getattr(sticker, 'format_type', None)
    lottie_format = getattr(discord.StickerFormatType, 'lottie', None)
    seen_urls: set[str] = set()

    def append_candidate(
        url: str | None,
        media_type: str,
        *,
        source_url: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> None:
        if not url:
            return
        normalized = str(url)
        if normalized in seen_urls:
            return
        seen_urls.add(normalized)
        entry: dict[str, Any] = {
            'url': normalized,
            'type': media_type,
        }
        if source_url:
            entry['source_url'] = source_url
        if extra:
            entry['extra'] = dict(extra)
        candidates.append(entry)

    if lottie_format and format_type == lottie_format:
        image_templates = [
            'https://cdn.discordapp.com/stickers/{id}.{ext}?size=160',
            'https://media.discordapp.net/stickers/{id}.{ext}?size=160',
            'https://media.discordapp.net/sticker/{id}.{ext}?size=160',
        ]

        fallback_urls: list[str] = []
        if sticker_id:
            for ext in ('png', 'webp'):
                for template in image_templates:
                    fallback_urls.append(template.format(id=sticker_id, ext=ext))
        fallback_urls = list(dict.fromkeys(fallback_urls))
        # Prefer the animated JSON, but keep static fallbacks for browsers that cannot load it.

        lottie_urls: list[str] = []
        url_attr = getattr(sticker, 'url', None)
        if url_attr:
            lottie_urls.append(str(url_attr))
        if sticker_id:
            lottie_urls.extend([
                f'https://cdn.discordapp.com/stickers/{sticker_id}.json',
                f'https://media.discordapp.net/stickers/{sticker_id}.json',
                f'https://media.discordapp.net/sticker/{sticker_id}.json',
            ])
        lottie_urls = list(dict.fromkeys(lottie_urls))

        extra_base: dict[str, Any] = {'loop': True, 'autoplay': True}
        if fallback_urls:
            extra_base['fallback_url'] = fallback_urls[0]
            extra_base['fallback_urls'] = fallback_urls
        if lottie_urls:
            extra_base['lottie_urls'] = lottie_urls

        primary_lottie = lottie_urls[0] if lottie_urls else None
        if primary_lottie:
            append_candidate(primary_lottie, 'lottie', source_url=primary_lottie, extra=extra_base)
            return candidates

        for fallback in fallback_urls:
            append_candidate(fallback, 'image', source_url=fallback)

        return candidates

    url_attr = getattr(sticker, 'url', None)
    if url_attr:
        append_candidate(str(url_attr), 'image', source_url=str(url_attr))

    if not sticker_id:
        return candidates

    gif_format = getattr(discord.StickerFormatType, 'gif', None)
    if gif_format and format_type == gif_format:
        extensions = ('gif', 'png', 'webp')
    elif format_type == discord.StickerFormatType.apng:
        extensions = ('png',)
    else:
        extensions = ('png', 'webp')

    templates = [
        'https://cdn.discordapp.com/stickers/{id}.{ext}?size=160',
        'https://media.discordapp.net/stickers/{id}.{ext}?size=160',
        'https://media.discordapp.net/sticker/{id}.{ext}?size=160',
    ]

    for ext in extensions:
        for template in templates:
            url = template.format(id=sticker_id, ext=ext)
            append_candidate(url, 'image', source_url=url)

    return candidates


def load_settings() -> Settings:
    """Assemble runtime settings from disk and environment."""
    store = load_settings_file(SETTINGS_PATH)

    token = require_setting(store, "DISCORD_BOT_TOKEN")

    legacy_channel_raw = get_setting(store, "DISCORD_CHANNEL_ID")
    obs_channel_raw = get_setting(store, "DISCORD_CHANNEL_ID_OBS") or legacy_channel_raw
    if not obs_channel_raw:
        raise RuntimeError("Configuration value 'DISCORD_CHANNEL_ID_OBS' is required. See README for setup details.")
    obs_channel_id = parse_int(obs_channel_raw, "DISCORD_CHANNEL_ID_OBS", minimum=1)

    embed_channel_raw = get_setting(store, "DISCORD_CHANNEL_ID_EMBED")
    if embed_channel_raw:
        embed_channel_id = parse_int(embed_channel_raw, "DISCORD_CHANNEL_ID_EMBED", minimum=1)
    elif legacy_channel_raw:
        embed_channel_id = parse_int(legacy_channel_raw, "DISCORD_CHANNEL_ID_EMBED", minimum=1)
    else:
        embed_channel_id = obs_channel_id

    host = get_setting(store, "CHAT_API_HOST", default="127.0.0.1") or "127.0.0.1"
    port_raw = get_setting(store, "CHAT_API_PORT", default="8080") or "8080"
    port = parse_int(port_raw, "CHAT_API_PORT", minimum=1)

    history_raw = get_setting(store, "CHAT_HISTORY_SIZE", default="200") or "200"
    history_size = parse_int(history_raw, "CHAT_HISTORY_SIZE", minimum=1)

    return Settings(
        token=token,
        obs_channel_id=obs_channel_id,
        embed_channel_id=embed_channel_id,
        host=host,
        port=port,
        history_size=history_size,
    )


def build_intents() -> discord.Intents:
    """Enable the minimal gateway intents we rely on."""
    intents = discord.Intents.default()
    intents.messages = True
    intents.message_content = True
    return intents


MessagePayload = Dict[str, object]


class ChatRelayClient(discord.Client):
    """Discord client that mirrors messages into per-feed histories."""
    def __init__(
        self,
        *,
        channel_mapping: Mapping[int, str],
        histories: Mapping[str, Deque[MessagePayload]],
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._channel_mapping: Dict[int, str] = dict(channel_mapping)
        self._histories: Dict[str, Deque[MessagePayload]] = dict(histories)

    async def on_ready(self) -> None:
        if self.user:
            log.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        else:
            log.info("Logged in, but user information is unavailable.")

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return

        channel_key = self._channel_mapping.get(message.channel.id)
        if channel_key is None:
            return  # Not a channel we care about.
        history = self._histories.get(channel_key)
        if history is None:
            return  # Safety guard for missing history queues.

        raw_content = message.content or ""
        clean_content = message.clean_content or raw_content
        content_segments = build_content_segments(raw_content)
        content = clean_content

        media_items: list[dict[str, Any]] = []
        seen_media: set[str] = set()
        urls_to_strip: set[str] = set()

        def normalize(url: str) -> str:
            return url.split("?", 1)[0].lower()

        def remember_url(url: str | None) -> None:
            if not url:
                return
            urls_to_strip.add(url)
            urls_to_strip.add(normalize(url))

        def add_media(
            url: str | None,
            media_type: str,
            *,
            source_url: str | None = None,
            extra: Mapping[str, Any] | None = None,
        ) -> bool:
            """Insert a media entry once, tagging extras for the frontend."""
            if not url:
                return False
            normalized = normalize(url)
            if normalized in seen_media:
                return False
            seen_media.add(normalized)
            entry: dict[str, Any] = {"type": media_type, "url": url}
            if extra:
                entry.update({key: value for key, value in extra.items() if value is not None})
            media_items.append(entry)
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

        unsupported_stickers: list[str] = []
        for sticker in getattr(message, "stickers", ()):
            sticker_name = getattr(sticker, "name", "Sticker")
            added = False
            for candidate in sticker_cdn_candidates(sticker):
                candidate_url = candidate.get("url") if isinstance(candidate, dict) else None
                media_type = candidate.get("type", "image") if isinstance(candidate, dict) else "image"
                source_url = candidate.get("source_url") if isinstance(candidate, dict) else None
                extra = candidate.get("extra") if isinstance(candidate, dict) else None
                if not isinstance(extra, Mapping):
                    extra = None
                if add_media(candidate_url, media_type, source_url=source_url or candidate_url, extra=extra):
                    added = True
                    break
            if not added:
                unsupported_stickers.append(sticker_name)


        if unsupported_stickers:
            note = " ".join(f"[Sticker: {name} (not supported)]" for name in unsupported_stickers)
            had_content = bool(content)
            content = f"{content}\n{note}" if had_content else note
            if content_segments:
                content_segments.append({"type": "text", "content": f"\n{note}" if had_content else note})
            else:
                content_segments = [{"type": "text", "content": note}]

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
            had_content = bool(content)
            content = f"{content}\n{attachment_block}" if had_content else attachment_block
            if content_segments:
                content_segments.append({"type": "text", "content": f"\n{attachment_block}" if had_content else attachment_block})
            else:
                content_segments = [{"type": "text", "content": attachment_block}]

        if media_items:
            for match in re.findall(r"https?://\S+", content or ""):
                remember_url(match)

        if urls_to_strip and content:
            for url in sorted(urls_to_strip, key=len, reverse=True):
                if not url:
                    continue
                content = content.replace(url, "")
            content = re.sub(r"[ \t]+", " ", content)
            content = re.sub(r"\n{2,}", "\n", content).strip()
            if not content:
                content = ""

        if content_segments:
            cleaned_segments: list[dict[str, str | bool]] = []
            for segment in content_segments:
                if not isinstance(segment, dict):
                    continue
                if segment.get("type") == "text":
                    text_piece = str(segment.get("content") or "")
                    if text_piece:
                        for url in urls_to_strip:
                            if not url:
                                continue
                            text_piece = text_piece.replace(url, "")
                            normalized_url = normalize(url)
                            if normalized_url and normalized_url != url:
                                text_piece = text_piece.replace(normalized_url, "")
                    if text_piece.strip():
                        cleaned_segments.append({"type": "text", "content": text_piece})
                else:
                    cleaned_segments.append(segment)
            content_segments = cleaned_segments

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
            "content_segments": content_segments,
            "author": display_name,
            "avatar_url": avatar_url,
            "role_color": role_color,
            "media": media_items,
        }
        history.append(payload)
        log.debug("Stored message from %s", display_name)


def cors_headers() -> Dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }


def build_web_app(histories: Mapping[str, Deque[MessagePayload]]) -> web.Application:
    """Expose REST endpoints for both OBS and embed consumers."""
    history_obs = histories.get('obs')
    if history_obs is None:
        try:
            history_obs = next(iter(histories.values()))
        except StopIteration as err:
            raise RuntimeError('History collection is empty.') from err
    history_embed = histories.get('embed', history_obs)

    async def handle_chat(request: web.Request) -> web.Response:
        if wants_html(request):
            return await handle_index(request)
        target = (
            request.rel_url.query.get('target')
            or request.rel_url.query.get('feed')
            or request.rel_url.query.get('variant')
            or ''
        ).lower()
        selected_history = history_embed if target == 'embed' else history_obs
        return web.json_response(list(selected_history), headers=cors_headers())

    async def handle_embed_chat(request: web.Request) -> web.Response:
        """Dedicated endpoint for backwards-compatible embed polling."""
        return web.json_response(list(history_embed), headers=cors_headers())

    async def handle_options(request: web.Request) -> web.Response:
        return web.Response(headers=cors_headers())

    async def handle_index(request: web.Request) -> web.StreamResponse:
        return web.FileResponse(BASE_DIR / "index.html")

    async def handle_script(request: web.Request) -> web.StreamResponse:
        return web.FileResponse(BASE_DIR / "script.js")

    async def handle_styles(request: web.Request) -> web.StreamResponse:
        return web.FileResponse(BASE_DIR / "styles.css")

    async def handle_embed_script(request: web.Request) -> web.StreamResponse:
        return web.FileResponse(BASE_DIR / "embed.js")

    def wants_html(request: web.Request) -> bool:
        accept = (request.headers.get("Accept") or "*/*").lower()
        if request.headers.get("Sec-Fetch-Dest") == "document":
            return True
        json_markers = ("application/json", "application/ld+json", "application/vnd.api+json", "text/json")
        if any(marker in accept for marker in json_markers):
            return False
        return True

    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/script.js", handle_script)
    app.router.add_get("/styles.css", handle_styles)
    app.router.add_get("/embed.js", handle_embed_script)
    app.router.add_get("/chat", handle_chat)
    app.router.add_options("/chat", handle_options)
    app.router.add_get("/embed-chat", handle_embed_chat)
    app.router.add_options("/embed-chat", handle_options)
    return app


async def run_web_app(app: web.Application, *, host: str, port: int, shutdown_event: asyncio.Event) -> None:
    """Spin up the aiohttp server until the Discord client signals shutdown."""
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
    """Bootstrap configuration, Discord client, and web server."""
    configure_logging()

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
    # Keep separate history buffers so OBS and embeds can diverge cleanly.

    histories: Dict[str, Deque[MessagePayload]] = {
        'obs': history_obs,
        'embed': history_embed,
    }

    channel_mapping: Dict[int, str] = {settings.obs_channel_id: 'obs'}
    if settings.embed_channel_id != settings.obs_channel_id:
        channel_mapping[settings.embed_channel_id] = 'embed'
    # The mapping lets the Discord client decide which history deque to fan out into.

    client = ChatRelayClient(
        channel_mapping=channel_mapping,
        histories=histories,
        intents=build_intents(),
    )
    app = build_web_app(histories)

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






