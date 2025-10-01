from __future__ import annotations

import logging
from typing import Deque, Dict, Mapping

import discord

from .config import INCLUDE_MESSAGE_TIMESTAMPS
from .messages import MessagePayload, build_message_payload

log = logging.getLogger("discord_chat_to_obs.client")


class ChatRelayClient(discord.Client):
    """Discord client that mirrors messages into per-feed histories."""

    def __init__(
        self,
        *,
        channel_mapping: Mapping[int, str],
        histories: Mapping[str, Deque[MessagePayload]],
        include_timestamps: bool = INCLUDE_MESSAGE_TIMESTAMPS,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._channel_mapping: Dict[int, str] = dict(channel_mapping)
        self._histories: Dict[str, Deque[MessagePayload]] = dict(histories)
        self._include_timestamps = include_timestamps

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
            return

        history = self._histories.get(channel_key)
        if history is None:
            return

        payload = build_message_payload(message, include_timestamps=self._include_timestamps)
        history.append(payload)

        preview = _summarise_payload(payload)
        channel_name = getattr(message.channel, "name", message.channel.id)
        log.info("Relayed message from %s in #%s: %s", payload["author"], channel_name, preview)

    def histories(self) -> Dict[str, Deque[MessagePayload]]:
        return self._histories


def _summarise_payload(payload: MessagePayload) -> str:
    content = payload.get("content") or payload.get("clean_content") or payload.get("raw_content") or ""
    if content:
        summary = str(content).replace("\n", " ").strip()
        return summary[:200] if summary else "(no text)"
    media = payload.get("media")
    if isinstance(media, list) and media:
        return f"[{len(media)} media attachment(s)]"
    return "(no text)"
