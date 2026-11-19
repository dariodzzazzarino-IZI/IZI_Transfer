"""IZI Transfer standalone graphical installer (one product, Collect visual style)."""
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QProgressBar, QMessageBox
from PySide6.QtGui import QIcon

from version import APP_VERSION
VERSION = APP_VERSION
NAME = "IZI Transfer"
STYLE = """
QWidget { background: #1e1f22; color: #eceef2; font-family: 'Segoe UI', 'Inter'; font-size: 13px; }
QLabel#title { font-size: 28px; font-weight: 650; }
QLabel#detail { color: #a8aeba; }
QLabel#product { font-size: 16px; font-weight: 650; }
QPushButton { background: #393c43; padding: 9px 18px; border: 0; border-radius: 8px; }
QPushButton:hover { background: #484b54; }
QPushButton#primary { background: #7896d0; color: #141820; font-weight: 650; }
QProgressBar { background: #1c1e23; border: 1px solid #383c45; border-radius: 4px; min-height: 7px; max-height: 7px; }
QProgressBar::chunk { background: #7896d0; border-radius: 4px; }
"""
BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
PAYLOAD = BASE / "payload.zip"

def destination():
    if sys.platform == "win32":
        return Path(os.environ["LOCALAPPDATA"]) / "Programs" / NAME
    return Path.home() / "Applications" / (NAME + ".app")

def desktop_shortcut(target):
    if sys.platform == "win32":
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
            desktop = Path(winreg.QueryValueEx(key, "Desktop")[0])
        # Use a PowerShell script with named parameters; -Command does not
        # reliably populate $args for trailing subprocess arguments.
        import base64
        def ps_quote(value):
            return "'" + str(value).replace("'", "''") + "'"
        shortcut = desktop / (NAME + ".lnk")
        executable = target / (NAME + ".exe")
        script = (
            "$w=New-Object -ComObject WScript.Shell;"
            "$s=$w.CreateShortcut(" + ps_quote(shortcut) + ");"
            "$s.TargetPath=" + ps_quote(executable) + ";"
            "$s.WorkingDirectory=" + ps_quote(target) + ";"
            "$s.Save()"
        )
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive",
                        "-EncodedCommand", encoded],
                       check=True, timeout=30, capture_output=True, text=True)
    else:
        link = Path.home() / "Desktop" / NAME
        if link.is_symlink():
            link.unlink()
        if not link.exists():
            link.symlink_to(target)

def register_windows(target):
    import winreg
    key = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\IZITransfer"
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key) as reg:
        for name, value in [("DisplayName", NAME), ("DisplayVersion", VERSION),
                            ("Publisher", "IZI Studio by Zazzarino Photography"),
                            ("InstallLocation", str(target)),
                            ("DisplayIcon", str(target / (NAME + ".exe")))]:
            winreg.SetValueEx(reg, name, 0, winreg.REG_SZ, value)

def install(progress):
    if not PAYLOAD.is_file():
        raise RuntimeError("Pacchetto di installazione incompleto")
    target = destination()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(target.parent), prefix=".izi-transfer-") as tmp:
        staging = Path(tmp) / "new"
        staging.mkdir()
        with zipfile.ZipFile(PAYLOAD) as archive:
            for member in archive.infolist():
                resolved = (staging / member.filename).resolve()
                if not resolved.is_relative_to(staging.resolve()):
                    raise RuntimeError("Archivio non valido")
            archive.extractall(staging)
        progress.emit(40)
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/IM", NAME + ".exe"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            source = staging / NAME
        else:
            subprocess.run(["pkill", "-x", NAME], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
            source = staging / (NAME + ".app")
        if not source.exists():
            raise RuntimeError("Applicazione mancante nel pacchetto")
        backup = Path(tmp) / "backup"
        if target.exists():
            target.rename(backup)
        try:
            shutil.move(str(source), str(target))
        except Exception:
            if backup.exists():
                backup.rename(target)
            raise
        progress.emit(75)
        if sys.platform == "win32":
            register_windows(target)
        try:
            desktop_shortcut(target)
        except (OSError, subprocess.SubprocessError) as exc:
            # A desktop shortcut is optional; never mark an installed app as failed.
            print("Collegamento desktop non creato:", exc, file=sys.stderr)
        progress.emit(100)
    return target

class Worker(QThread):
    progress = Signal(int)
    done = Signal(str)
    failed = Signal(str)
    def run(self):
        try:
            self.done.emit(str(install(self.progress)))
        except Exception as exc:
            self.failed.emit(str(exc))

class Installer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IZI Transfer · Installazione")
        self.resize(600, 340)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 18)
        layout.setSpacing(15)
        title = QLabel("IZI Transfer")
        title.setObjectName("title")
        layout.addWidget(title)
        sub = QLabel("Installer · Versione " + VERSION + " · IZI Collection")
        sub.setObjectName("detail")
        layout.addWidget(sub)
        product = QLabel("IZI Transfer")
        product.setObjectName("product")
        layout.addWidget(product)
        self.state = QLabel("Installazione in: " + str(destination()))
        self.state.setObjectName("detail")
        self.state.setWordWrap(True)
        layout.addWidget(self.state)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        layout.addStretch()
        row = QHBoxLayout()
        self.close_button = QPushButton("Chiudi")
        self.close_button.clicked.connect(self.close)
        row.addWidget(self.close_button)
        self.action = QPushButton("Installa / Aggiorna")
        self.action.setObjectName("primary")
        self.action.clicked.connect(self.start)
        row.addWidget(self.action)
        layout.addLayout(row)
        if "--auto" in sys.argv:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(400, self.start)

    def start(self):
        if hasattr(self, "worker") and self.worker.isRunning():
            return
        self.action.setEnabled(False)
        self.state.setText("Installazione in corso...")
        self.worker = Worker(self)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.done.connect(self.complete)
        self.worker.failed.connect(self.fail)
        self.worker.start()

    def complete(self, path):
        self.state.setText("Installazione completata: " + path)
        self.action.setEnabled(True)
        try:
            if sys.platform == "win32":
                subprocess.Popen([str(Path(path) / (NAME + ".exe"))])
            else:
                subprocess.Popen(["open", path])
        except OSError as exc:
            self.state.setText("Installazione completata; avvio manuale necessario: " + str(exc))

    def fail(self, error):
        self.state.setText("Errore: " + error)
        self.action.setEnabled(True)
        QMessageBox.critical(self, "Installazione", error)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = Installer()
    window.show()
    sys.exit(app.exec())
