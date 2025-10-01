from __future__ import annotations

from typing import Any, Optional

import customtkinter as ctk
import tkinter as tk


class PreviewMessage(ctk.CTkFrame):
    """Compact widget used to live-preview chat styling choices."""

    def __init__(self, master: tk.Widget) -> None:
        super().__init__(master, fg_color="#36393f", corner_radius=12)
        self.grid_columnconfigure(1, weight=1)

        self.avatar = ctk.CTkLabel(
            self,
            text=":-)",
            width=48,
            height=48,
            corner_radius=24,
            fg_color="#5865f2",
            font=ctk.CTkFont(size=24),
        )
        self.avatar.grid(row=0, column=0, padx=(16, 12), pady=16, sticky="n")

        self.bubble = ctk.CTkFrame(self, fg_color="#40444b", corner_radius=16)
        self.bubble.grid(row=0, column=1, padx=(0, 16), pady=16, sticky="nsew")
        self.bubble.grid_columnconfigure(0, weight=1)

        self.username_label = ctk.CTkLabel(
            self.bubble,
            text="Username (00:00)",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        self._header_grid = {"row": 0, "column": 0, "sticky": "w", "padx": 12, "pady": (10, 2)}
        self.username_label.grid(**self._header_grid)

        self.message_label = ctk.CTkLabel(
            self.bubble,
            text="Type a test message below to preview your settings.",
            wraplength=320,
            justify="left",
        )
        self.message_label.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 10))

    def update_preview(
        self,
        *,
        chat_bg: str,
        message_bg: str,
        message_color: str,
        username_color: str,
        font_family: str,
        header_text: str,
        body_text: str,
    ) -> None:
        try:
            self.configure(fg_color=chat_bg)
        except Exception:
            pass
        try:
            self.bubble.configure(fg_color=message_bg)
        except Exception:
            pass

        title_font = ctk.CTkFont(family=font_family or "Roboto", size=14, weight="bold")
        body_font = ctk.CTkFont(family=font_family or "Roboto", size=13)

        header = header_text or ""
        if header:
            self.username_label.configure(text=header, text_color=username_color or "#99aab5", font=title_font)
            if not self.username_label.winfo_ismapped():
                self.username_label.grid(**self._header_grid)
        else:
            if self.username_label.winfo_ismapped():
                self.username_label.grid_remove()
            self.username_label.configure(text="", text_color=username_color or "#99aab5", font=title_font)

        effective_body = body_text if body_text and body_text.strip() else "Type a test message below to preview your settings."
        self.message_label.configure(text=effective_body, text_color=message_color or "#dcddde", font=body_font)


class Tooltip:
    """Lightweight tooltip helper that shows contextual guidance on hover."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self._window: Optional[tk.Toplevel] = None
        if not text:
            return
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)
        widget.bind("<FocusOut>", self._hide)

    def _show(self, _event: Any) -> None:
        if self._window or not self.text:
            return
        try:
            x_pos = self.widget.winfo_rootx() + 20
            y_pos = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        except Exception:
            return
        window = tk.Toplevel(self.widget)
        window.overrideredirect(True)
        window.configure(background="#1f2933")
        label = tk.Label(
            window,
            text=self.text,
            justify="left",
            background="#1f2933",
            foreground="#f8fafc",
            relief="solid",
            borderwidth=1,
            wraplength=280,
            padx=8,
            pady=6,
            font=("Segoe UI", 9),
        )
        label.pack()
        window.wm_geometry(f"+{x_pos}+{y_pos}")
        self._window = window

    def _hide(self, _event: Any | None = None) -> None:
        if self._window is not None:
            self._window.destroy()
            self._window = None
