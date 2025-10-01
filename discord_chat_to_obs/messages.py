from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Set, TypedDict, cast

import discord

from .config import INCLUDE_MESSAGE_TIMESTAMPS

CUSTOM_EMOJI_PATTERN = re.compile(r"<a?:([a-zA-Z0-9_]+)(?::(\d+))?>")


class ContentSegment(TypedDict, total=False):
    type: str
    content: str
    name: str
    id: str
    animated: bool


class MediaItem(TypedDict, total=False):
    type: str
    url: str
    source_url: str
    loop: bool
    autoplay: bool
    fallback_url: str
    fallback_urls: List[str]
    lottie_urls: List[str]


class EmbedFooterPayload(TypedDict, total=False):
    text: str
    icon_url: str


class EmbedAuthorPayload(TypedDict, total=False):
    name: str
    url: str
    icon_url: str


class EmbedFieldPayload(TypedDict, total=False):
    name: str
    value: str
    inline: bool


class EmbedPayload(TypedDict, total=False):
    title: str
    description: str
    url: str
    author: EmbedAuthorPayload
    footer: EmbedFooterPayload
    color: str
    timestamp: str
    fields: List[EmbedFieldPayload]
    thumbnail_url: str
    image_url: str
    video_url: str


class MessagePayload(TypedDict, total=False):
    id: str
    channel_id: str
    guild_id: str | None
    author_id: str
    author: str
    avatar_url: str
    role_color: str
    content: str
    clean_content: str
    raw_content: str
    content_segments: List[ContentSegment]
    media: List[MediaItem]
    embeds: List[EmbedPayload]
    timestamp: str | None


SegmentList = List[ContentSegment]


def build_content_segments(text: str) -> SegmentList:
    """Split raw Discord text into text and custom emoji segments."""
    if not text:
        return []

    segments: SegmentList = []
    last_index = 0

    for match in CUSTOM_EMOJI_PATTERN.finditer(text):
        start, end = match.span()
        if start > last_index:
            segments.append({"type": "text", "content": text[last_index:start]})

        name = match.group(1)
        emoji_id = match.group(2)
        if emoji_id:
            segments.append(
                {
                    "type": "emoji",
                    "name": name,
                    "id": emoji_id,
                    "animated": match.group(0).startswith('<a:'),
                }
            )
        else:
            segments.append({"type": "text", "content": match.group(0)})
        last_index = end

    if last_index < len(text):
        segments.append({"type": "text", "content": text[last_index:]})

    return [segment for segment in segments if segment.get("type") != "text" or segment.get("content")]


def sticker_cdn_candidates(sticker: Any | None) -> List[Dict[str, Any]]:
    """Return probable CDN URLs and metadata for a Discord sticker."""
    candidates: List[Dict[str, Any]] = []
    if sticker is None:
        return candidates

    sticker_id = getattr(sticker, "id", None)
    format_type = getattr(sticker, "format", None) or getattr(sticker, "format_type", None)
    lottie_format = getattr(discord.StickerFormatType, "lottie", None)
    seen_urls: Set[str] = set()

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
        entry: Dict[str, Any] = {
            "url": normalized,
            "type": media_type,
        }
        if source_url:
            entry["source_url"] = source_url
        if extra:
            entry["extra"] = dict(extra)
        candidates.append(entry)

    if lottie_format and format_type == lottie_format:
        image_templates = [
            "https://cdn.discordapp.com/stickers/{id}.{ext}?size=160",
            "https://media.discordapp.net/stickers/{id}.{ext}?size=160",
            "https://media.discordapp.net/sticker/{id}.{ext}?size=160",
        ]

        fallback_urls: List[str] = []
        if sticker_id:
            for ext in ("png", "webp"):
                for template in image_templates:
                    fallback_urls.append(template.format(id=sticker_id, ext=ext))
        fallback_urls = list(dict.fromkeys(fallback_urls))

        lottie_urls: List[str] = []
        url_attr = getattr(sticker, "url", None)
        if url_attr:
            lottie_urls.append(str(url_attr))
        if sticker_id:
            lottie_urls.extend(
                [
                    f"https://cdn.discordapp.com/stickers/{sticker_id}.json",
                    f"https://media.discordapp.net/stickers/{sticker_id}.json",
                    f"https://media.discordapp.net/sticker/{sticker_id}.json",
                ]
            )
        lottie_urls = list(dict.fromkeys(lottie_urls))

        extra_base: Dict[str, Any] = {"loop": True, "autoplay": True}
        if fallback_urls:
            extra_base["fallback_url"] = fallback_urls[0]
            extra_base["fallback_urls"] = fallback_urls
        if lottie_urls:
            extra_base["lottie_urls"] = lottie_urls

        primary_lottie = lottie_urls[0] if lottie_urls else None
        if primary_lottie:
            append_candidate(primary_lottie, "lottie", source_url=primary_lottie, extra=extra_base)
            return candidates

        for fallback in fallback_urls:
            append_candidate(fallback, "image", source_url=fallback)

        return candidates

    url_attr = getattr(sticker, "url", None)
    if url_attr:
        append_candidate(str(url_attr), "image", source_url=str(url_attr))

    if not sticker_id:
        return candidates

    gif_format = getattr(discord.StickerFormatType, "gif", None)
    if gif_format and format_type == gif_format:
        extensions = ("gif", "png", "webp")
    elif format_type == discord.StickerFormatType.apng:
        extensions = ("png",)
    else:
        extensions = ("png", "webp")

    templates = [
        "https://cdn.discordapp.com/stickers/{id}.{ext}?size=160",
        "https://media.discordapp.net/stickers/{id}.{ext}?size=160",
        "https://media.discordapp.net/sticker/{id}.{ext}?size=160",
    ]

    for ext in extensions:
        for template in templates:
            url = template.format(id=sticker_id, ext=ext)
            append_candidate(url, "image", source_url=url)

    return candidates


def _normalize_url(url: str | None) -> str:
    return (url or "").split("?", 1)[0].lower()


def _strip_urls(text: str, urls: Iterable[str]) -> str:
    cleaned = text
    for url in sorted(set(u for u in urls if u), key=len, reverse=True):
        normalized = _normalize_url(url)
        cleaned = cleaned.replace(url, "")
        if normalized and normalized != url:
            cleaned = cleaned.replace(normalized, "")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
    return cleaned


def _pick_role_color(member: Any) -> str:
    """Return the highest-positioned role with a non-default color; fallback to a neutral."""
    default_color = "#99aab5"
    try:
        roles = list(getattr(member, "roles", []) or [])
        # Highest roles first
        roles.sort(key=lambda r: getattr(r, "position", 0), reverse=True)
        for role in roles:
            colour = getattr(role, "colour", None) or getattr(role, "color", None)
            value = getattr(colour, "value", None) if colour else None
            if isinstance(value, int) and value not in (0, 0x000000):
                return f"#{value:06x}"
        # Fallback to top_role if present
        top_role = getattr(member, "top_role", None)
        colour = getattr(top_role, "colour", None) or getattr(top_role, "color", None)
        value = getattr(colour, "value", None) if colour else None
        if isinstance(value, int) and value not in (0, 0x000000):
            return f"#{value:06x}"
    except Exception:
        pass
    return default_color


_EMBED_EMPTY_MARKER = getattr(discord.Embed, "Empty", object())


def _coerce_embed_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        if value is _EMBED_EMPTY_MARKER:
            return None
    except Exception:
        pass
    text_value = str(value)
    stripped = text_value.strip()
    return stripped if stripped else None


def _serialise_embed(embed: Any) -> Optional[EmbedPayload]:
    if embed is None:
        return None
    payload: Dict[str, Any] = {}

    title = _coerce_embed_str(getattr(embed, "title", None))
    if title:
        payload["title"] = title

    url_value = _coerce_embed_str(getattr(embed, "url", None))
    if url_value:
        payload["url"] = url_value

    description = _coerce_embed_str(getattr(embed, "description", None))
    if description:
        payload["description"] = description

    colour_obj = getattr(embed, "colour", None) or getattr(embed, "color", None)
    colour_value = getattr(colour_obj, "value", None)
    if isinstance(colour_value, int) and colour_value:
        payload["color"] = f"#{colour_value:06x}"

    timestamp_value = getattr(embed, "timestamp", None)
    if timestamp_value:
        try:
            payload["timestamp"] = timestamp_value.isoformat()
        except Exception:
            pass

    author = getattr(embed, "author", None)
    author_payload: Dict[str, Any] = {}
    if author:
        name = _coerce_embed_str(getattr(author, "name", None))
        if name:
            author_payload["name"] = name
        author_url = _coerce_embed_str(getattr(author, "url", None))
        if author_url:
            author_payload["url"] = author_url
        icon_url = _coerce_embed_str(getattr(author, "icon_url", None))
        if icon_url:
            author_payload["icon_url"] = icon_url
    if author_payload:
        payload["author"] = cast(EmbedAuthorPayload, author_payload)

    footer = getattr(embed, "footer", None)
    footer_payload: Dict[str, Any] = {}
    if footer:
        footer_text = _coerce_embed_str(getattr(footer, "text", None))
        if footer_text:
            footer_payload["text"] = footer_text
        footer_icon = _coerce_embed_str(getattr(footer, "icon_url", None))
        if footer_icon:
            footer_payload["icon_url"] = footer_icon
    if footer_payload:
        payload["footer"] = cast(EmbedFooterPayload, footer_payload)

    fields_payload: List[EmbedFieldPayload] = []
    for field in getattr(embed, "fields", []):
        name = _coerce_embed_str(getattr(field, "name", None))
        value = _coerce_embed_str(getattr(field, "value", None))
        if not name and not value:
            continue
        field_entry: Dict[str, Any] = {}
        if name:
            field_entry["name"] = name
        if value:
            field_entry["value"] = value
        inline_flag = getattr(field, "inline", None)
        if isinstance(inline_flag, bool):
            field_entry["inline"] = inline_flag
        elif inline_flag:
            field_entry["inline"] = True
        fields_payload.append(cast(EmbedFieldPayload, field_entry))
    if fields_payload:
        payload["fields"] = fields_payload

    thumbnail = getattr(embed, "thumbnail", None)
    thumb_url = _coerce_embed_str(getattr(thumbnail, "url", None))
    if thumb_url:
        payload["thumbnail_url"] = thumb_url

    image = getattr(embed, "image", None)
    image_url = _coerce_embed_str(getattr(image, "url", None))
    if image_url:
        payload["image_url"] = image_url

    video = getattr(embed, "video", None)
    video_url = _coerce_embed_str(getattr(video, "url", None))
    if video_url:
        payload["video_url"] = video_url

    return cast(EmbedPayload, payload) if payload else None


def _summarise_embed_text(embed: Mapping[str, Any]) -> str:
    lines: List[str] = []

    author = embed.get("author")
    if isinstance(author, Mapping):
        author_name = author.get("name")
        if author_name:
            lines.append(str(author_name))

    title = embed.get("title")
    if title:
        url_value = embed.get("url")
        title_line = str(title)
        if url_value and url_value != title:
            title_line = f"{title_line} ({url_value})"
        lines.append(title_line)

    description = embed.get("description")
    if description:
        lines.append(str(description))

    fields = embed.get("fields")
    if isinstance(fields, list):
        for field in fields:
            if not isinstance(field, Mapping):
                continue
            field_name = field.get("name")
            field_value = field.get("value")
            if field_name and field_value:
                lines.append(f"{field_name}: {field_value}")
            elif field_value:
                lines.append(str(field_value))
            elif field_name:
                lines.append(str(field_name))

    footer = embed.get("footer")
    footer_text = None
    if isinstance(footer, Mapping):
        footer_text = footer.get("text")

    timestamp_value = embed.get("timestamp")
    footer_parts = [str(part) for part in (footer_text, timestamp_value) if part]
    if footer_parts:
        lines.append(" - ".join(footer_parts))

    return "\n".join(line.strip() for line in lines if str(line).strip()).strip()


def build_message_payload(message: discord.Message, *, include_timestamps: bool | None = None) -> MessagePayload:
    """Convert a Discord message into a serialisable history payload."""
    include_ts = INCLUDE_MESSAGE_TIMESTAMPS if include_timestamps is None else include_timestamps

    raw_content = message.content or ""
    clean_content = message.clean_content or raw_content
    segments = build_content_segments(raw_content)

    media_items: List[MediaItem] = []
    seen_media: Set[str] = set()
    urls_to_strip: Set[str] = set()
    embed_payloads: List[EmbedPayload] = []
    embed_summaries: List[str] = []

    def add_media(
        url: str | None,
        media_type: str,
        *,
        source_url: str | None = None,
        extra: Mapping[str, Any] | None = None,
    ) -> bool:
        if not url:
            return False
        normalized = _normalize_url(url)
        if normalized in seen_media:
            return False
        seen_media.add(normalized)
        entry: MutableMapping[str, Any] = {"type": media_type, "url": url}
        if source_url:
            entry["source_url"] = source_url
        if extra:
            entry.update({key: value for key, value in extra.items() if value is not None})
        media_items.append(entry)  # type: ignore[arg-type]
        urls_to_strip.add(url)
        if source_url:
            urls_to_strip.add(source_url)
        return True

    attachment_fallback: List[str] = []
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

    unsupported_stickers: List[str] = []
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
        if segments:
            segments.append({"type": "text", "content": f"\n{note}"})
        else:
            segments = [{"type": "text", "content": note}]
        clean_content = f"{clean_content}\n{note}" if clean_content else note


    for embed in message.embeds:
        embed_data = _serialise_embed(embed)
        if embed_data:
            embed_payloads.append(embed_data)
            summary = _summarise_embed_text(embed_data)
            if summary:
                embed_summaries.append(summary)

        embed_video = getattr(embed, "video", None)
        video_url = getattr(embed_video, "url", None) if embed_video else None
        source_url = getattr(embed, "url", None)
        if video_url:
            add_media(video_url, "video", source_url=source_url)

    if embed_summaries:
        embed_text = "\n\n".join(embed_summaries)
        clean_content = f"{clean_content}\n\n{embed_text}" if clean_content else embed_text
        if segments:
            segments.append({"type": "text", "content": f"\n\n{embed_text}"})
        else:
            segments = [{"type": "text", "content": embed_text}]

    if attachment_fallback and not media_items:
        attachment_block = "\n".join(attachment_fallback)
        clean_content = f"{clean_content}\n{attachment_block}" if clean_content else attachment_block
        if segments:
            segments.append({"type": "text", "content": f"\n{attachment_block}"})
        else:
            segments = [{"type": "text", "content": attachment_block}]

    if media_items:
        for match in re.findall(r"https?://\S+", clean_content or ""):
            urls_to_strip.add(match)

    stripped_content = _strip_urls(clean_content, urls_to_strip) if urls_to_strip else clean_content

    if segments:
        cleaned_segments: SegmentList = []
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            if segment.get("type") == "text":
                text_piece = str(segment.get("content") or "")
                if urls_to_strip:
                    text_piece = _strip_urls(text_piece, urls_to_strip)
                if text_piece.strip():
                    cleaned_segments.append({"type": "text", "content": text_piece})
            else:
                cleaned_segments.append(segment)
        segments = cleaned_segments

    author = message.author
    avatar_url = str(author.display_avatar.url)
    display_name = author.display_name
    role_color = _pick_role_color(author)

    timestamp_value: str | None = None
    if include_ts and getattr(message, "created_at", None):
        try:
            timestamp_value = message.created_at.isoformat()
        except Exception:
            timestamp_value = None

    payload: MessagePayload = {
        "id": str(message.id),
        "channel_id": str(getattr(message.channel, "id", "")),
        "guild_id": str(getattr(getattr(message, "guild", None), "id", "")) or None,
        "author": display_name,
        "author_id": str(getattr(author, "id", "")),
        "avatar_url": avatar_url,
        "role_color": role_color,
        "raw_content": raw_content,
        "clean_content": clean_content,
        "content": stripped_content,
        "content_segments": segments,
        "media": media_items,
        "embeds": embed_payloads,
        "timestamp": timestamp_value,
    }

    return payload
