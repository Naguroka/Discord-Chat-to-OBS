from __future__ import annotations

import subprocess
import sys
import threading
from typing import Callable, List, Optional

from .paths import BASE_DIR


class ServiceController:
    """Manage lifecycle of the local HTTP server and Discord bot processes."""

    def __init__(self) -> None:
        self.http_process: Optional[subprocess.Popen] = None
        self.bot_process: Optional[subprocess.Popen] = None
        self._threads: list[threading.Thread] = []
        self._log_callback: Callable[[str], None] = lambda message: None
        self._status_callback: Callable[[], None] = lambda: None
        self._exit_callback: Callable[[str, Optional[int]], None] = lambda _name, _code: None

    def set_log_callback(self, callback: Optional[Callable[[str], None]]) -> None:
        self._log_callback = callback or (lambda message: None)

    def set_status_callback(self, callback: Optional[Callable[[], None]]) -> None:
        self._status_callback = callback or (lambda: None)

    def set_exit_callback(self, callback: Optional[Callable[[str, Optional[int]], None]]) -> None:
        self._exit_callback = callback or (lambda _name, _code: None)

    def _log(self, message: str) -> None:
        try:
            self._log_callback(message)
        except Exception:
            pass

    def _notify_status(self) -> None:
        try:
            self._status_callback()
        except Exception:
            pass

    @property
    def is_running(self) -> bool:
        processes = (self.http_process, self.bot_process)
        return all(proc is not None and proc.poll() is None for proc in processes)

    def _start_watcher(self, process: subprocess.Popen, name: str) -> None:
        def pump() -> None:
            stream = process.stdout
            login_hint_sent = False
            if stream is not None:
                for raw_line in stream:
                    line = raw_line.rstrip()
                    if not line:
                        continue
                    lower_line = line.lower()
                    if name == "bot" and not login_hint_sent and "improper token has been passed" in lower_line:
                        self._log(
                            "Discord rejected the token. Update DISCORD_BOT_TOKEN under Discord Bot Settings and try again."
                        )
                        login_hint_sent = True
                    skip_access = False
                    if "aiohttp.access" in lower_line:
                        for path_hint in (
                            ' "get /chat',
                            ' "get /embed-chat',
                            ' "get /script.js',
                            ' "get /styles.css',
                            ' "get /embed.js',
                        ):
                            if path_hint in lower_line:
                                skip_access = True
                                break
                    if not skip_access:
                        self._log(f"[{name}] {line}")
            exit_code = process.wait()
            self._log(f"[{name}] exited with code {exit_code}")
            self._notify_status()
            try:
                self._exit_callback(name, exit_code)
            except Exception:
                pass

        thread = threading.Thread(target=pump, name=f"dobs-{name}-pump", daemon=True)
        self._threads.append(thread)
        thread.start()

    def _launch_process(self, name: str, args: List[str]) -> subprocess.Popen:
        creation_flags = 0
        start_new_session = False
        if sys.platform.startswith("win"):
            if hasattr(subprocess, "CREATE_NO_WINDOW"):
                creation_flags |= subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
                creation_flags |= subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            start_new_session = True

        process = subprocess.Popen(
            args,
            cwd=str(BASE_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
            start_new_session=start_new_session,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        self._log(f"[{name}] started (PID {process.pid})")
        self._start_watcher(process, name)
        return process

    def start(self) -> None:
        if self.is_running:
            self._log("Services already running.")
            return
        python_exe = sys.executable
        try:
            self.http_process = self._launch_process("http", [python_exe, "-m", "http.server", "8000", "--directory", str(BASE_DIR / "web")])
            self.bot_process = self._launch_process("bot", [python_exe, "bot.py"])
            self._log(
                "Overlay available at http://127.0.0.1:8080/ (OBS) and http://127.0.0.1:8080/?embed=1 (embed preview)."
            )
        except Exception as exc:
            self._log(f"Failed to start services: {exc}")
            self.stop()
            raise
        finally:
            self._notify_status()

    def stop(self) -> None:
        for name, attr in (("bot", "bot_process"), ("http", "http_process")):
            proc = getattr(self, attr)
            if proc and proc.poll() is None:
                self._log(f"Stopping {name} service (PID {proc.pid})")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._log(f"Forcing {name} service to stop.")
                    proc.kill()
            setattr(self, attr, None)
        for thread in list(self._threads):
            if thread.is_alive():
                thread.join(timeout=1)
        self._threads = []
        self._notify_status()
