"""
Autoclicker - a simple, configurable autoclicker with a GUI.

Features:
  - Adjustable click speed (clicks per second or fixed interval in ms)
  - Optional random jitter added to the interval, for more natural timing
  - Left / right / middle mouse button selection
  - Single or double click per tick
  - Configurable global hotkeys to start and stop clicking (works even when
    another window, like Minecraft, has focus)
  - Settings are saved to config.json next to this script and reloaded on
    the next launch
"""

import json
import os
import threading
import time
import random
import tkinter as tk
from tkinter import ttk, messagebox

from pynput import mouse, keyboard
from pynput.mouse import Button

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "cps": 10.0,
    "jitter_ms": 0,
    "button": "left",
    "click_type": "single",
    "start_hotkey": "f6",
    "stop_hotkey": "f7",
}

BUTTON_MAP = {
    "left": Button.left,
    "right": Button.right,
    "middle": Button.middle,
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                data = json.load(f)
            merged = dict(DEFAULT_CONFIG)
            merged.update(data)
            return merged
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_CONFIG)


def save_config(config):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
    except OSError:
        pass


class ClickerEngine:
    """Runs the click loop on a background thread."""

    def __init__(self):
        self._mouse = mouse.Controller()
        self._thread = None
        self._stop_event = threading.Event()
        self.running = False

    def start(self, cps, jitter_ms, button, click_type, on_state_change=None):
        if self.running:
            return
        self.running = True
        self._stop_event.clear()

        def loop():
            base_interval = 1.0 / cps if cps > 0 else 0.1
            btn = BUTTON_MAP.get(button, Button.left)
            clicks = 2 if click_type == "double" else 1
            while not self._stop_event.is_set():
                self._mouse.click(btn, clicks)
                jitter = random.uniform(-jitter_ms, jitter_ms) / 1000.0 if jitter_ms > 0 else 0.0
                delay = max(0.0, base_interval + jitter)
                self._stop_event.wait(delay)
            self.running = False
            if on_state_change:
                on_state_change(False)

        self._thread = threading.Thread(target=loop, daemon=True)
        self._thread.start()
        if on_state_change:
            on_state_change(True)

    def stop(self):
        self._stop_event.set()
        self.running = False


class HotkeyManager:
    """Listens globally for the configured start/stop key presses."""

    def __init__(self, on_start, on_stop):
        self.on_start = on_start
        self.on_stop = on_stop
        self.start_key = None
        self.stop_key = None
        self._listener = None

    @staticmethod
    def _parse_key(name):
        name = name.strip().lower()
        try:
            return keyboard.Key[name]
        except KeyError:
            if len(name) == 1:
                return keyboard.KeyCode.from_char(name)
            return None

    def set_hotkeys(self, start_name, stop_name):
        self.start_key = self._parse_key(start_name)
        self.stop_key = self._parse_key(stop_name)

    def _on_press(self, key):
        if self.start_key is not None and key == self.start_key:
            self.on_start()
        elif self.stop_key is not None and key == self.stop_key:
            self.on_stop()

    def run(self):
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()


class HotkeyCaptureDialog(tk.Toplevel):
    """Modal dialog that captures the next key pressed."""

    def __init__(self, parent, title):
        super().__init__(parent)
        self.title(title)
        self.geometry("300x100")
        self.resizable(False, False)
        self.result = None
        self.transient(parent)
        self.grab_set()

        label = ttk.Label(self, text="Press any key...", font=("Segoe UI", 11))
        label.pack(expand=True, pady=20)

        self._listener = keyboard.Listener(on_press=self._on_key)
        self._listener.start()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _on_key(self, key):
        name = None
        if isinstance(key, keyboard.KeyCode) and key.char:
            name = key.char.lower()
        elif isinstance(key, keyboard.Key):
            name = key.name
        if name:
            self.result = name
        self.after(1, self._close)

    def _close(self):
        try:
            self._listener.stop()
        except Exception:
            pass
        self.grab_release()
        self.destroy()


class AutoclickerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Autoclicker")
        self.root.geometry("360x420")
        self.root.resizable(False, False)

        self.config = load_config()
        self.engine = ClickerEngine()
        self.hotkeys = HotkeyManager(self.request_start, self.request_stop)

        self._build_ui()
        self._apply_hotkeys()
        self.hotkeys.run()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI ----------

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        frame = ttk.Frame(self.root)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Autoclicker", font=("Segoe UI", 16, "bold")).pack(pady=(12, 4))

        # Speed
        speed_frame = ttk.LabelFrame(frame, text="Click Speed")
        speed_frame.pack(fill="x", **pad)

        ttk.Label(speed_frame, text="Clicks per second:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.cps_var = tk.StringVar(value=str(self.config["cps"]))
        ttk.Entry(speed_frame, textvariable=self.cps_var, width=10).grid(row=0, column=1, padx=8, pady=4)

        ttk.Label(speed_frame, text="Random jitter (ms):").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.jitter_var = tk.StringVar(value=str(self.config["jitter_ms"]))
        ttk.Entry(speed_frame, textvariable=self.jitter_var, width=10).grid(row=1, column=1, padx=8, pady=4)

        # Click options
        click_frame = ttk.LabelFrame(frame, text="Click Options")
        click_frame.pack(fill="x", **pad)

        ttk.Label(click_frame, text="Mouse button:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.button_var = tk.StringVar(value=self.config["button"])
        ttk.Combobox(
            click_frame, textvariable=self.button_var, values=["left", "right", "middle"],
            state="readonly", width=8
        ).grid(row=0, column=1, padx=8, pady=4)

        ttk.Label(click_frame, text="Click type:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.click_type_var = tk.StringVar(value=self.config["click_type"])
        ttk.Combobox(
            click_frame, textvariable=self.click_type_var, values=["single", "double"],
            state="readonly", width=8
        ).grid(row=1, column=1, padx=8, pady=4)

        # Hotkeys
        hotkey_frame = ttk.LabelFrame(frame, text="Hotkeys")
        hotkey_frame.pack(fill="x", **pad)

        ttk.Label(hotkey_frame, text="Start:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        self.start_hotkey_var = tk.StringVar(value=self.config["start_hotkey"])
        ttk.Entry(hotkey_frame, textvariable=self.start_hotkey_var, width=10, state="readonly").grid(
            row=0, column=1, padx=8, pady=4
        )
        ttk.Button(hotkey_frame, text="Set", command=lambda: self._capture_hotkey("start")).grid(
            row=0, column=2, padx=8, pady=4
        )

        ttk.Label(hotkey_frame, text="Stop:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self.stop_hotkey_var = tk.StringVar(value=self.config["stop_hotkey"])
        ttk.Entry(hotkey_frame, textvariable=self.stop_hotkey_var, width=10, state="readonly").grid(
            row=1, column=1, padx=8, pady=4
        )
        ttk.Button(hotkey_frame, text="Set", command=lambda: self._capture_hotkey("stop")).grid(
            row=1, column=2, padx=8, pady=4
        )

        # Status + controls
        self.status_var = tk.StringVar(value="Stopped")
        status_label = ttk.Label(frame, textvariable=self.status_var, font=("Segoe UI", 12, "bold"))
        status_label.pack(pady=(10, 4))
        self.status_label = status_label

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=6)
        ttk.Button(btn_frame, text="Start", command=self.request_start).grid(row=0, column=0, padx=6)
        ttk.Button(btn_frame, text="Stop", command=self.request_stop).grid(row=0, column=1, padx=6)
        ttk.Button(btn_frame, text="Save Settings", command=self._save_settings).grid(row=0, column=2, padx=6)

        self._update_status(False)

    def _capture_hotkey(self, which):
        dialog = HotkeyCaptureDialog(self.root, f"Set {which} hotkey")
        self.root.wait_window(dialog)
        if dialog.result:
            if which == "start":
                self.start_hotkey_var.set(dialog.result)
            else:
                self.stop_hotkey_var.set(dialog.result)
            self._apply_hotkeys()

    def _apply_hotkeys(self):
        self.hotkeys.set_hotkeys(self.start_hotkey_var.get(), self.stop_hotkey_var.get())

    def _read_settings(self):
        try:
            cps = float(self.cps_var.get())
            if cps <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid input", "Clicks per second must be a positive number.")
            return None

        try:
            jitter_ms = float(self.jitter_var.get())
            if jitter_ms < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid input", "Jitter must be zero or a positive number.")
            return None

        return {
            "cps": cps,
            "jitter_ms": jitter_ms,
            "button": self.button_var.get(),
            "click_type": self.click_type_var.get(),
            "start_hotkey": self.start_hotkey_var.get(),
            "stop_hotkey": self.stop_hotkey_var.get(),
        }

    def _save_settings(self):
        settings = self._read_settings()
        if settings is None:
            return
        self.config = settings
        save_config(self.config)
        messagebox.showinfo("Saved", "Settings saved.")

    def _update_status(self, running):
        if running:
            self.status_var.set("Running")
            self.status_label.configure(foreground="green")
        else:
            self.status_var.set("Stopped")
            self.status_label.configure(foreground="red")

    # ---------- Actions ----------

    def request_start(self):
        if self.engine.running:
            return
        settings = self._read_settings()
        if settings is None:
            return
        self.root.after(0, lambda: self._update_status(True))
        self.engine.start(
            cps=settings["cps"],
            jitter_ms=settings["jitter_ms"],
            button=settings["button"],
            click_type=settings["click_type"],
            on_state_change=lambda running: self.root.after(0, self._update_status, running),
        )

    def request_stop(self):
        self.engine.stop()
        self.root.after(0, lambda: self._update_status(False))

    def _on_close(self):
        self.engine.stop()
        self.hotkeys.stop()
        self.root.destroy()


def main():
    root = tk.Tk()
    style = ttk.Style()
    try:
        style.theme_use("vista")
    except tk.TclError:
        pass
    AutoclickerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
