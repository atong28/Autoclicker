# Autoclicker

A simple, configurable autoclicker with a GUI, built for Minecraft (works with
any game/app). Runs on Windows (and Linux/macOS with a display).

## Features

- Adjustable clicks-per-second
- Optional random jitter (ms) so timing isn't perfectly robotic
- Left / right / middle mouse button
- Single or double click per tick
- Configurable global hotkeys to start/stop — these work even while
  Minecraft (or any other window) has focus, since they're captured at the
  OS level via `pynput`
- Settings are saved to `config.json` next to the script and reloaded on
  next launch

## Running it (Python)

Requires Python 3.8+ (Windows installer from python.org includes Tk, so no
extra install needed for the GUI toolkit).

```
pip install -r requirements.txt
python autoclicker.py
```

## Building a standalone Windows .exe

You need to run this step **on a Windows machine** (PyInstaller builds for
whatever OS it runs on — it can't cross-compile a Windows .exe from Linux/Mac).

```
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --name Autoclicker autoclicker.py
```

The .exe will be in `dist\Autoclicker.exe`. Copy that single file anywhere —
no Python install needed on the target machine.

## Usage

1. Set your desired clicks-per-second and (optionally) jitter.
2. Choose the mouse button and click type.
3. Click "Set" next to Start/Stop and press the key you want for each hotkey
   (defaults are F6 to start, F7 to stop).
4. Click "Save Settings" to persist your configuration.
5. Switch focus to Minecraft, then press your start hotkey to begin
   clicking at the current cursor position, and your stop hotkey to stop.

## Notes

- The autoclicker clicks at the mouse's current screen position — position
  your cursor over the game window before starting.
- Some anticheat systems or server rules restrict autoclicking; check the
  rules of any server you play on before using this in multiplayer.
- On Windows, some games run with elevated privileges and may block input
  from non-elevated processes — if hotkeys/clicks don't register, try running
  the autoclicker as Administrator.
