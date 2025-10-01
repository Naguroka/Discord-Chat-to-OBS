from __future__ import annotations

import json
import atexit
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import customtkinter as ctk
except ImportError as exc:
    raise SystemExit("CustomTkinter is required to run DOBS. Install it with 'pip install customtkinter'.") from exc

import tkinter as tk
import tkinter.font as tkfont
from tkinter import filedialog, messagebox
from .config_manager import ConfigManager
from .constants import DEFAULT_FONT_STACK
from .paths import ASSETS_DIR, BACKGROUND_LIBRARY_DIR, BASE_DIR
from .utils import decode_js_string, encode_js_string, escape_js_basic, normalize_tk_color
from .variables import VARIABLE_MAP, VARIABLES, Variable
from .service import ServiceController
from .widgets import PreviewMessage, Tooltip

try:
    DEFAULT_MESSAGE_TEMPLATE = VARIABLE_MAP['message_layout_template'].getter() or '{{author}}{{timestamp}}: {{message}}'
except Exception:
    DEFAULT_MESSAGE_TEMPLATE = '{{author}}{{timestamp}}: {{message}}'

try:
    DEFAULT_HIDE_TEMPLATE = VARIABLE_MAP['message_hide_username_template'].getter() or '{{message}}'
except Exception:
    DEFAULT_HIDE_TEMPLATE = '{{message}}'


try:
    DEFAULT_TIMESTAMP_TEMPLATE = VARIABLE_MAP['timestamp_template'].getter() or ' ({{time}})'
except Exception:
    DEFAULT_TIMESTAMP_TEMPLATE = ' ({{time}})'

class DOBSApp(ctk.CTk):
    def __init__(self, manager: ConfigManager, controller: ServiceController) -> None:
        super().__init__()
        self.title("DOBS - Discord to OBS")
        self.geometry("1200x720")
        self.minsize(1100, 640)

        # Apply custom window/taskbar icons when assets are available.
        icon_path = BASE_DIR / "assets" / "dobslogo.ico"
        if icon_path.exists():
            try:
                self.iconbitmap(default=str(icon_path))
            except Exception:
                pass

        # Prepare scaled logo variants for in-app branding.
        self._logo_raw_image: Optional[tk.PhotoImage] = None
        self._icon_image: Optional[tk.PhotoImage] = None
        self._header_logo_image: Optional[tk.PhotoImage] = None
        logo_png_path = BASE_DIR / "assets" / "dobslogo.png"
        if logo_png_path.exists():
            try:
                raw_logo = tk.PhotoImage(file=str(logo_png_path))
                self._logo_raw_image = raw_logo
                icon_scale = max(raw_logo.width() // 256, 1)
                self._icon_image = raw_logo.subsample(icon_scale, icon_scale) if icon_scale > 1 else raw_logo
                header_scale = max(raw_logo.width() // 96, 1)
                self._header_logo_image = raw_logo.subsample(header_scale, header_scale) if header_scale > 1 else raw_logo
                if self._icon_image is not None:
                    self.iconphoto(True, self._icon_image)
            except Exception:
                self._logo_raw_image = None
                self._icon_image = None
                self._header_logo_image = None

        self.manager = manager
        self.controller = controller
        self._loading = False
        self._auto_stopping = False
        self._user_stopping = False

        self.controls: Dict[str, Dict[str, Any]] = {}
        self._tooltips: List[Tooltip] = []
        self._font_choices = self._build_font_choices()

        self.test_message_var = tk.StringVar(value="This is a preview of your overlay settings!")

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_config_panel()
        self._build_preview_panel()

        self.controller.set_log_callback(self.log_message)
        self.controller.set_status_callback(lambda: self.after(0, self._update_service_label))
        self.controller.set_exit_callback(lambda name, code: self.after(0, self._handle_process_exit, name, code))

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self._apply_config_to_ui(self.manager.current_values)
        self.refresh_favorite_buttons()
        self.refresh_favorites_tab()
        self.update_preview()
        self._update_service_label()
        self.log_message(f"Loaded configuration '{self.manager.current_name}'")

    def _bind_combobox_scroll(self, combobox: ctk.CTkComboBox, choices: list[str], variable: tk.Variable) -> None:
        if combobox is None or not choices:
            return

        def adjust(step: int) -> None:
            if not choices:
                return
            current = combobox.get()
            try:
                index = choices.index(current)
            except ValueError:
                index = 0
            index = max(0, min(len(choices) - 1, index + step))
            value = choices[index]
            combobox.set(value)
            if variable is not None:
                variable.set(value)

        def on_mousewheel(event):
            delta = -1 if getattr(event, 'delta', 0) > 0 else 1
            adjust(delta)
            return 'break'

        def on_button_up(event):
            adjust(-1)
            return 'break'

        def on_button_down(event):
            adjust(1)
            return 'break'

        combobox.bind('<MouseWheel>', on_mousewheel)
        combobox.bind('<Button-4>', on_button_up)
        combobox.bind('<Button-5>', on_button_down)

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=(14, 8), padx=18)
        header.grid_columnconfigure(2, weight=1)

        if self._header_logo_image is not None:
            logo = ctk.CTkLabel(header, text="", image=self._header_logo_image)
            logo.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))

        title = ctk.CTkLabel(
            header,
            text="Discord to OBS Control Center",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=1, sticky="w")

        subtitle = ctk.CTkLabel(
            header,
            text="Configure templates, backgrounds, fonts, and favorites without editing files.",
            text_color="#95a5a6",
            font=ctk.CTkFont(size=13),
            anchor="w",
            justify="left",
        )
        subtitle.grid(row=1, column=1, sticky="w", pady=(0, 4))

        self.theme_var = tk.StringVar(value="System")

        def on_theme_change(choice: str) -> None:
            ctk.set_appearance_mode(choice.lower())
            self.theme_var.set(choice)

        theme_menu = ctk.CTkOptionMenu(
            header,
            variable=self.theme_var,
            values=["System", "Light", "Dark"],
            command=on_theme_change,
        )
        theme_menu.grid(row=0, column=3, sticky="e", padx=(0, 12))

        service_frame = ctk.CTkFrame(header, corner_radius=12, fg_color="#1f2933")
        service_frame.grid(row=0, column=4, rowspan=2, sticky="e", padx=(0, 0))
        service_frame.grid_columnconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(service_frame, text="Services stopped", text_color="#ff6b6b")
        self.status_label.grid(row=0, column=0, padx=12, pady=12, sticky="w")

        self.start_button = ctk.CTkButton(service_frame, text="Start Services", command=self.start_services)
        self.start_button.grid(row=0, column=1, padx=(0, 6), pady=12)

        self.stop_button = ctk.CTkButton(service_frame, text="Stop Services", command=self.stop_services)
        self.stop_button.grid(row=0, column=2, padx=(0, 12), pady=12)
    def _build_config_panel(self) -> None:
        panel = ctk.CTkFrame(self)
        panel.grid(row=1, column=0, sticky="nsew", padx=(18, 9), pady=(0, 18))
        panel.grid_rowconfigure(1, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        selector_frame = ctk.CTkFrame(panel, fg_color="transparent")
        selector_frame.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 12))
        selector_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(selector_frame, text="Configuration").grid(row=0, column=0, sticky="w")

        self.config_var = tk.StringVar(value=self.manager.current_name)
        self.config_menu = ctk.CTkOptionMenu(selector_frame, variable=self.config_var, values=self.manager.list_configs(), command=self.on_config_change)
        self.config_menu.grid(row=0, column=1, sticky="ew", padx=(12, 12))

        new_button = ctk.CTkButton(selector_frame, text="New", width=60, command=self.create_config)
        new_button.grid(row=0, column=2, padx=(0, 8))

        delete_button = ctk.CTkButton(selector_frame, text="Delete", width=60, command=self.delete_config)
        delete_button.grid(row=0, column=3)

        self.tabview = ctk.CTkTabview(panel)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

        self.tabview.add("Favorites")
        favorites_tab = self.tabview.tab("Favorites")
        self.favorites_scroll = ctk.CTkScrollableFrame(favorites_tab)
        self.favorites_scroll.pack(fill="both", expand=True, padx=6, pady=6)

        self.controls.clear()

        categories: Dict[str, List[Variable]] = {}
        for var in VARIABLES:
            categories.setdefault(var.category, []).append(var)

        category_order = ["Discord Bot Settings", "Backend Defaults", "Overlay Script", "Overlay Styling", "Embed Defaults"]
        for category in categories:
            if category not in category_order:
                category_order.append(category)

        for category in category_order:
            if category == "Favorites" or category not in categories:
                continue
            self.tabview.add(category)
            tab_container = self.tabview.tab(category)
            scroll = ctk.CTkScrollableFrame(tab_container)
            scroll.pack(fill="both", expand=True, padx=6, pady=6)
            for var in categories[category]:
                self._create_variable_control(scroll, var, primary=True)



    def _create_variable_control(self, parent: tk.Widget, variable: Variable, *, primary: bool = False) -> None:
        control = self.controls.get(variable.key)
        if control is None:
            tk_var = tk.BooleanVar() if variable.dtype == "bool" else tk.StringVar()
            control = {
                "variable": variable,
                "tk_var": tk_var,
                "widgets": [],
                "favorite_buttons": [],
            }
            self.controls[variable.key] = control

            def callback(*_args: Any) -> None:
                self._on_variable_change(variable.key)

            tk_var.trace_add("write", callback)
        else:
            tk_var = control["tk_var"]

        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=6, pady=6)
        frame.grid_columnconfigure(1, weight=1)

        label = ctk.CTkLabel(frame, text=variable.label, font=ctk.CTkFont(weight="bold"))
        label.grid(row=0, column=0, sticky="w", padx=12, pady=(10, 0))

        if primary:
            desc = ctk.CTkLabel(frame, text=variable.description, wraplength=420, justify="left", text_color="#95a5a6")
            desc.grid(row=1, column=0, columnspan=4, sticky="w", padx=12, pady=(2, 10))

        star_column = 2

        if variable.dtype == "bool":
            widget: tk.Widget = ctk.CTkSwitch(frame, variable=tk_var, text="")
            widget.grid(row=0, column=1, sticky="e", padx=12, pady=(10, 0))
        else:
            if variable.key in {"message_layout_template", "message_hide_username_template"}:
                widget = ctk.CTkTextbox(frame, height=96, wrap="word")
                widget.insert("1.0", tk_var.get())
                widget.grid(row=0, column=1, sticky="ew", padx=12, pady=(10, 0))
                widget.bind("<KeyRelease>", lambda _event, w=widget, var=tk_var: self._sync_textbox(w, var))
                widget.bind("<<Paste>>", lambda _event, w=widget, var=tk_var: self.after(5, lambda: self._sync_textbox(w, var)))
                self._ensure_tooltip(widget, "Supports HTML markup (e.g. <strong>, <em>, <span style='color:#ffeb3b'>) plus {{author}}, {{timestamp}}, {{timestamp_raw}}, {{message}}, and {{newline}} tokens.")
            elif variable.key == "css_font_family":
                widget = ctk.CTkComboBox(frame, variable=tk_var, values=self._font_choices, state="normal")
                widget.grid(row=0, column=1, sticky="ew", padx=12, pady=(10, 0))
                self._bind_combobox_scroll(widget, self._font_choices, tk_var)
                widget.bind("<FocusOut>", lambda _event, var=tk_var, w=widget: var.set(w.get()))
                widget.bind("<Return>", lambda _event, var=tk_var, w=widget: var.set(w.get()))
            elif variable.key == "background_media_url":
                widget = ctk.CTkEntry(frame, textvariable=tk_var)
                widget.grid(row=0, column=1, sticky="ew", padx=12, pady=(10, 0))

                browse = ctk.CTkButton(
                    frame,
                    text="Browse…",
                    width=90,
                    command=lambda var=tk_var: self._select_background_media(var),
                )
                browse.grid(row=0, column=2, sticky="e", padx=6, pady=(10, 0))

                clear = ctk.CTkButton(
                    frame,
                    text="Clear",
                    width=60,
                    command=lambda var=tk_var: self._clear_background_media(var),
                )
                clear.grid(row=0, column=3, sticky="e", padx=(0, 6), pady=(10, 0))

                star_column = 4
                self._ensure_tooltip(widget, "Use a URL or choose a local file to mirror into the overlay background.")
            else:
                widget = ctk.CTkEntry(frame, textvariable=tk_var)
                widget.grid(row=0, column=1, sticky="ew", padx=12, pady=(10, 0))

        star_button = ctk.CTkButton(
            frame,
            text="⭐" if self.manager.is_favorite(variable.key) else "☆",
            width=32,
            command=lambda key=variable.key: self.toggle_favorite(key),
        )
        star_button.grid(row=0, column=star_column, sticky="e", padx=12, pady=(10, 0))

        control["widgets"].append(widget)
        control["favorite_buttons"].append(star_button)

    def _sync_textbox(self, widget: ctk.CTkTextbox, tk_var: tk.StringVar) -> None:
        """Mirror textbox edits back into the tracked Tk variable."""
        if self._loading:
            return
        value = widget.get("1.0", "end-1c")
        if tk_var.get() != value:
            tk_var.set(value)

    def _set_textbox(self, widget: ctk.CTkTextbox, value: str | None) -> None:
        """Push the latest config value into all linked textbox widgets."""
        desired = "" if value is None else str(value)
        current = widget.get("1.0", "end-1c")
        if current != desired:
            widget.delete("1.0", "end")
            if desired:
                widget.insert("1.0", desired)

    def _ensure_tooltip(self, widget: tk.Widget, text: str) -> None:
        """Attach a single tooltip helper to the supplied widget."""
        if not text:
            return
        tooltip = Tooltip(widget, text)
        self._tooltips.append(tooltip)

    def _build_font_choices(self) -> List[str]:
        """Generate a sorted list of installed fonts plus helpful fallbacks."""
        try:
            families = sorted({name for name in tkfont.families() if name and not name.startswith('@')})
        except Exception:
            families = []
        choices: List[str] = [DEFAULT_FONT_STACK]
        for generic in ("sans-serif", "serif", "monospace"):
            if generic not in choices:
                choices.append(generic)
        for family in families:
            formatted = f"'{family}'" if " " in family and not family.startswith("'") else family
            if formatted not in choices:
                choices.append(formatted)
        return choices

    def _import_background_media(self, source: Path) -> str:
        """Copy user-selected media into assets/backgrounds and return a served URL."""
        if not source.exists():
            raise FileNotFoundError(f"File not found: {source}")
        destination_dir = BACKGROUND_LIBRARY_DIR
        destination_dir.mkdir(parents=True, exist_ok=True)
        sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "_", source.name) or 'background'
        destination = destination_dir / sanitized
        counter = 1
        while destination.exists() and destination.resolve() != source.resolve():
            destination = destination_dir / f"{source.stem}_{counter}{source.suffix}"
            counter += 1
        if not destination.exists() or destination.resolve() != source.resolve():
            shutil.copy2(source, destination)
        return f"/assets/backgrounds/{destination.name}"

    def _select_background_media(self, tk_var: tk.StringVar) -> None:
        """Prompt the user to pick a media file and update the Tk variable."""
        initial_dir = BACKGROUND_LIBRARY_DIR if BACKGROUND_LIBRARY_DIR.exists() else ASSETS_DIR
        filetypes = [
            ("Media files", "*.png *.jpg *.jpeg *.gif *.webp *.svg *.mp4 *.webm *.mov *.m4v"),
            ("Images", "*.png *.jpg *.jpeg *.gif *.webp *.svg"),
            ("Videos", "*.mp4 *.webm *.mov *.m4v"),
            ("All files", "*.*"),
        ]
        chosen = filedialog.askopenfilename(
            title="Choose background media",
            initialdir=str(initial_dir),
            filetypes=filetypes,
        )
        if not chosen:
            return
        try:
            url = self._import_background_media(Path(chosen))
        except Exception as exc:
            messagebox.showerror("Import failed", f"Could not import background media:\n{exc}")
            return
        tk_var.set(url)

    def _clear_background_media(self, tk_var: tk.StringVar) -> None:
        """Reset the background media selection."""
        tk_var.set("")

    def _on_variable_change(self, key: str) -> None:
        if self._loading:
            return
        control = self.controls.get(key)
        if not control:
            return
        variable = control["variable"]
        tk_var = control["tk_var"]
        raw_value = tk_var.get()
        was_valid = self.manager.set_raw_value(variable, raw_value)
        if was_valid:
            self.log_message(f"{variable.label} set to {self._describe_value(variable, self.manager.current_values.get(key))}")
        self.update_preview()
    def _describe_value(self, variable: Variable, value: Any) -> str:
            if variable.dtype == "bool":
                return "enabled" if value else "disabled"
            if value in (None, ""):
                return "default"
            return str(value)
    
    def _build_preview_panel(self) -> None:
            panel = ctk.CTkFrame(self)
            panel.grid(row=1, column=1, sticky="nsew", padx=(9, 18), pady=(0, 18))
            panel.grid_rowconfigure(1, weight=1)
            panel.grid_rowconfigure(3, weight=1)
            panel.grid_columnconfigure(0, weight=1)
    
            top_frame = ctk.CTkFrame(panel, fg_color="transparent")
            top_frame.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 6))
            top_frame.grid_columnconfigure(1, weight=1)
    
            ctk.CTkLabel(top_frame, text="Live Preview", font=ctk.CTkFont(size=16, weight="bold")).grid(row=0, column=0, sticky="w")
            preview_entry = ctk.CTkEntry(top_frame, textvariable=self.test_message_var)
            preview_entry.grid(row=0, column=1, sticky="ew", padx=(12, 0))
            self.test_message_var.trace_add("write", lambda *_args: self.update_preview())
    
            self.preview = PreviewMessage(panel)
            self.preview.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))
    
            ctk.CTkLabel(panel, text="Console Log", font=ctk.CTkFont(size=15, weight="bold")).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 6))
    
            self.console_text = ctk.CTkTextbox(panel, wrap="word")
            self.console_text.grid(row=3, column=0, sticky="nsew", padx=18, pady=(0, 18))
            self.console_text.configure(state="disabled")
    
    def _render_preview_parts(self, template: str, context: Dict[str, str]) -> tuple[str, str]:
        """Split the template at {{message}} to emulate the web's column layout."""
        decoded = decode_js_string(template or DEFAULT_MESSAGE_TEMPLATE)
        # Find the first {{message}} (with optional whitespace)
        message_re = re.compile(r'{{\s*message\s*}}', re.I)
        m = message_re.search(decoded)
        before = decoded[: m.start()] if m else decoded
        after  = decoded[m.end():] if m else ''

        def _clean(html: str) -> str:
            h = html.replace('{{newline}}', '\n')
            for key, value in context.items():
                if key == 'message':
                    continue
                h = h.replace(f'{{{{{key}}}}}', value or '')
            h = re.sub(r'{{\s*[a-z_]+\s*}}', '', h)
            h = h.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
            h = re.sub(r'<[^>]+>', '', h)
            parts = [seg.strip() for seg in h.splitlines() if seg.strip()]
            return '\n'.join(parts).strip()

        header_text = _clean(before)
        # Body is the user's test message, plus any suffix after {{message}}.
        suffix = _clean(after)
        body_text = (self.test_message_var.get() or '').strip()
        if suffix:
            body_text = (body_text + '\n' + suffix).strip()
        return header_text, body_text
    
    def _apply_config_to_ui(self, config: Dict[str, Any]) -> None:
            self._loading = True
            try:
                for key, control in self.controls.items():
                    variable = control["variable"]
                    tk_var = control["tk_var"]
                    value = config.get(key)
                    display_value = variable.to_display(value)
                    if isinstance(tk_var, tk.BooleanVar):
                        tk_var.set(bool(display_value))
                    else:
                        tk_var.set("" if display_value is None else str(display_value))
                    widgets = [widget for widget in control.get("widgets", []) if widget.winfo_exists()]
                    control["widgets"] = widgets
                    for widget in widgets:
                        if isinstance(widget, ctk.CTkTextbox):
                            self._set_textbox(widget, tk_var.get())
                        elif isinstance(widget, ctk.CTkComboBox):
                            const_value = tk_var.get()
                            const_value = const_value if const_value is not None else ''
                            try:
                                current_values = list(widget.cget('values'))
                            except Exception:
                                current_values = []
                            if const_value and const_value not in current_values:
                                widget.configure(values=current_values + [const_value])
                            widget.set(const_value)
            finally:
                self._loading = False
    
    def on_config_change(self, name: str) -> None:
            values = self.manager.load(name)
            self.config_var.set(name)
            self.config_menu.configure(values=self.manager.list_configs())
            self._apply_config_to_ui(values)
            self.refresh_favorite_buttons()
            self.refresh_favorites_tab()
            self.update_preview()
            self.log_message(f"Activated configuration '{name}'")
    
    def create_config(self) -> None:
            dialog = ctk.CTkInputDialog(text="Name for the new configuration:", title="New Configuration")
            name = dialog.get_input()
            if not name:
                return
            safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()) or "config"
            path = self.manager.config_path(safe_name)
            if path.exists():
                messagebox.showerror("Duplicate name", "A configuration with that name already exists.")
                return
            path.write_text(json.dumps({"values": self.manager.current_values}, indent=2), encoding="utf-8")
            self.manager.load(safe_name)
            self.config_var.set(safe_name)
            self.config_menu.configure(values=self.manager.list_configs())
            self._apply_config_to_ui(self.manager.current_values)
            self.refresh_favorite_buttons()
            self.refresh_favorites_tab()
            self.update_preview()
            self.log_message(f"Created configuration '{safe_name}'")
    
    def delete_config(self) -> None:
            name = self.config_var.get()
            if name == "default":
                messagebox.showinfo("Protected configuration", "The default configuration cannot be deleted.")
                return
            path = self.manager.config_path(name)
            if not path.exists():
                return
            if messagebox.askyesno("Delete configuration", f"Delete the configuration '{name}'?"):
                path.unlink()
                self.manager.load("default")
                self.config_var.set(self.manager.current_name)
                self.config_menu.configure(values=self.manager.list_configs())
                self._apply_config_to_ui(self.manager.current_values)
                self.refresh_favorite_buttons()
                self.refresh_favorites_tab()
                self.update_preview()
                self.log_message(f"Deleted configuration '{name}'")
    
    def _handle_process_exit(self, name: str, exit_code: Optional[int]) -> None:
            if self._auto_stopping or self._user_stopping:
                return
            friendly = 'Bot' if name == 'bot' else 'Static file server'
            code_display = exit_code if exit_code is not None else 'unknown'
            self.log_message(f"{friendly} process exited (code {code_display}).")
            other_proc = None
            if name == 'bot':
                other_proc = self.controller.http_process
            elif name == 'http':
                other_proc = self.controller.bot_process
            other_running = bool(other_proc and other_proc.poll() is None)
            self._update_service_label()
            if other_running:
                self.log_message('Stopping remaining services...')
                self._auto_stopping = True
                try:
                    self.controller.stop()
                finally:
                    self._update_service_label()
                    self.after(150, lambda: setattr(self, '_auto_stopping', False))
            if name == 'bot':
                self.log_message('If this was not intentional, double-check your Discord bot token and channel IDs.')
    
    def _resolve_setting(self, *keys: str) -> Any:
        for key in keys:
            if not key:
                continue
            value = self.manager.current_values.get(key)
            if isinstance(value, str):
                trimmed = value.strip()
                if trimmed:
                    return trimmed
            elif value:
                return value
        return None

    def start_services(self) -> None:
        if self.controller.is_running:
            self.log_message("Services already running.")
            return
        try:
            self.manager.apply_pending()
        except ValueError as exc:
            messagebox.showerror("Invalid settings", str(exc))
            self.log_message("Start aborted: invalid settings")
            return
        required = [
            (("settings.DISCORD_BOT_TOKEN", "DISCORD_BOT_TOKEN"), "Bot Token"),
            (("settings.DISCORD_CHANNEL_ID_OBS", "DISCORD_CHANNEL_ID_OBS"), "OBS Channel ID"),
            (("settings.DISCORD_CHANNEL_ID_EMBED", "DISCORD_CHANNEL_ID_EMBED"), "Embed Channel ID"),
        ]
        missing = [label for keys, label in required if not self._resolve_setting(*keys)]
        if missing:
            messagebox.showerror("Missing settings", "Please fill in: " + ", ".join(missing))
            self.log_message("Start aborted: missing required settings")
            return
        self._user_stopping = False
        self._auto_stopping = False
        self.log_message("Starting services...")
        try:
            self.controller.start()
        except Exception as exc:
            self.log_message(f"Failed to start services: {exc}")
            messagebox.showerror("Failed to start services", str(exc))
        finally:
            self._update_service_label()
    def stop_services(self) -> None:
            self.log_message("Stopping services...")
            self._user_stopping = True
            try:
                self.controller.stop()
            finally:
                self._update_service_label()
                self.after(150, lambda: setattr(self, '_user_stopping', False))
    
    def _update_service_label(self) -> None:
            running = self.controller.is_running
            if running:
                self.status_label.configure(text="Services running", text_color="#2ecc71")
                self.start_button.configure(state="disabled")
                self.stop_button.configure(state="normal")
            else:
                self.status_label.configure(text="Services stopped", text_color="#ff6b6b")
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
    
    def toggle_favorite(self, key: str) -> None:
            variable = VARIABLE_MAP.get(key)
            if not variable:
                return
            if self.manager.is_favorite(key):
                self.manager.remove_favorite(key)
                self.log_message(f"Removed '{variable.label}' from favorites.")
            else:
                self.manager.add_favorite(key)
                self.log_message(f"Added '{variable.label}' to favorites.")
            self.refresh_favorite_buttons(key)
            self.refresh_favorites_tab()
    
    def refresh_favorites_tab(self) -> None:
            for control in self.controls.values():
                buttons = control.get("favorite_buttons", [])
                control["favorite_buttons"] = [button for button in buttons if button.winfo_exists()]
            for child in self.favorites_scroll.winfo_children():
                child.destroy()
            valid_favorites = [entry for entry in self.manager.favorites if entry in VARIABLE_MAP]
            favorites = sorted(valid_favorites, key=lambda entry: VARIABLE_MAP[entry].label.lower())
            displayed = False
            for key in favorites:
                variable = VARIABLE_MAP[key]
                self._create_variable_control(self.favorites_scroll, variable, primary=False)
                displayed = True
            if not displayed:
                placeholder = ctk.CTkLabel(
                    self.favorites_scroll,
                    text="No favourites yet. Click ☆ beside a setting to pin it here.",
                    wraplength=360,
                    justify="left",
                    text_color="#95a5a6",
                )
                placeholder.pack(anchor="w", padx=6, pady=6)
    
    def refresh_favorite_buttons(self, key: Optional[str] = None) -> None:
            targets = [key] if key else list(self.controls.keys())
            for target in targets:
                control = self.controls.get(target)
                if not control:
                    continue
                is_favorite = self.manager.is_favorite(target)
                text = "⭐" if is_favorite else "☆"
                for button in control.get("favorite_buttons", []):
                    button.configure(text=text)
    
    def update_preview(self) -> None:
            values = self.manager.current_values
            chat_bg = values.get("css_chat_background") or "#36393f"
            message_bg = values.get("css_message_background") or "#40444b"
            message_color = values.get("css_message_color") or "#dcddde"
            username_color = values.get("css_username_color") or "#99aab5"
            font_family_raw = values.get("css_font_family") or "'Roboto', sans-serif"
            primary_font = font_family_raw.replace("'", "").split(",")[0].strip()
    
            include_ts = bool(values.get("include_timestamps", True))
            show_ts = bool(values.get("show_message_timestamps", True))
            timestamp_raw = "05:42" if include_ts and show_ts else ""

            hide_usernames = bool(values.get("embed_hide_usernames", False))
            template_key = "message_hide_username_template" if hide_usernames else "message_layout_template"
            template = values.get(template_key) or (DEFAULT_HIDE_TEMPLATE if hide_usernames else DEFAULT_MESSAGE_TEMPLATE)

            timestamp_template_value = values.get("timestamp_template") or DEFAULT_TIMESTAMP_TEMPLATE
            timestamp_display = ""
            if timestamp_raw and not hide_usernames:
                timestamp_display = (timestamp_template_value or "").replace("{{time}}", timestamp_raw)

            context = {
                "author": "Username",
                "timestamp": timestamp_display,
                "timestamp_raw": timestamp_raw,
                "message": self.test_message_var.get(),
            }
            header_text, preview_text = self._render_preview_parts(template, context)

    
            if not preview_text.strip():
                preview_text = 'Type a test message below to preview your settings.'
    
            self.preview.update_preview(
                chat_bg=normalize_tk_color(chat_bg, '#36393f'),
                message_bg=normalize_tk_color(message_bg, '#40444b'),
                message_color=normalize_tk_color(message_color, '#dcddde'),
                username_color=normalize_tk_color(username_color, '#99aab5'),
                font_family=primary_font,
                header_text=header_text,
                body_text=preview_text,
            )
    

    def log_message(self, message: str) -> None:
        if not message or not hasattr(self, "console_text"):
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"

        def append() -> None:
            widget = getattr(self, "console_text", None)
            if widget is None:
                return
            widget.configure(state="normal")
            widget.insert("end", entry + "\n")
            try:
                current_lines = int(widget.index("end-1c").split(".")[0])
            except Exception:
                current_lines = 0
            max_lines = 400
            if current_lines > max_lines:
                cutoff = current_lines - max_lines
                if cutoff > 0:
                    widget.delete("1.0", f"{cutoff}.0")
            widget.see("end")
            widget.configure(state="disabled")

        self.after(0, append)

    def on_close(self) -> None:
        self.log_message("Closing DOBS...")
        self._user_stopping = True
        self.controller.stop()
        self.destroy()
def main() -> None:
    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("dark-blue")
    manager = ConfigManager(VARIABLES)
    manager.apply_all()
    controller = ServiceController()
    atexit.register(lambda: controller.stop())
    app = DOBSApp(manager, controller)
    try:
        app.mainloop()
    finally:
        controller.stop()


if __name__ == "__main__":
    main()










