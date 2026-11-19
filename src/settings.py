"""Preferenze per utente; nessun dato sensibile viene scritto nella repository."""
import json
import os
import sys
from pathlib import Path

def config_dir():
    if sys.platform == "win32":
        root = Path(os.environ.get("APPDATA", str(Path.home())))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    path = root / "IZI Transfer"
    path.mkdir(parents=True, exist_ok=True)
    return path

def load():
    path = config_dir() / "settings.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}

def save(data):
    path = config_dir() / "settings.json"
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    if os.name != "nt":
        os.chmod(temp, 0o600)
    temp.replace(path)

def downloads_dir():
    path = Path.home() / "Downloads"
    path.mkdir(parents=True, exist_ok=True)
    return path

def startup_enabled():
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            winreg.QueryValueEx(key, "IZI Transfer")
        return True
    except OSError:
        return False

def set_startup(enabled):
    if sys.platform != "win32":
        raise RuntimeError("Avvio automatico disponibile per Windows")
    import winreg
    import subprocess
    import sys
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Per l'avvio automatico installa prima la build Windows")
    command = subprocess.list2cmdline([sys.executable, "--background"])
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Run",
                        0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, "IZI Transfer", 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, "IZI Transfer")
            except FileNotFoundError:
                pass
