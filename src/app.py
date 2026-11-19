"""IZI Transfer - interfaccia PySide6 nello stile originale IZI Retrieve."""
import ipaddress
import socket
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from PySide6.QtCore import Qt, QThread, Signal, QTimer, QUrl
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QListWidget, QFileDialog, QComboBox, QStackedWidget,
    QFrame, QMessageBox, QProgressBar, QCheckBox, QSystemTrayIcon, QMenu, QInputDialog, QDialog, QDialogButtonBox, QStyle,
)
from izi_style import QSS
from window_chrome import TitleBar
from version import APP_VERSION, COPYRIGHT, RELEASES
from updater import latest_release, download_installer, launch_installer
from PySide6.QtGui import QDesktopServices
from discovery import Discovery
from nas import Synology
from lan import start_receiver, send_file
from settings import load, save, downloads_dir, startup_enabled, set_startup


class Job(QThread):
    progress = Signal(str)
    done = Signal(str)
    failed = Signal(str)
    def __init__(self, mode, files, options):
        super().__init__()
        self.mode, self.files, self.options = mode, files, options

    def run(self):
        try:
            if self.mode == "local":
                for i, file in enumerate(self.files, 1):
                    self.progress.emit(f"Invio {i}/{len(self.files)}: {Path(file).name}")
                    send_file(self.options["host"], self.options["port"], self.options["token"], file)
                self.done.emit("Trasferimento locale completato")
                return
            nas = Synology(self.options["url"], self.options["user"], self.options["password"])
            try:
                self.progress.emit("Connessione al NAS...")
                nas.login()
                folder = nas.create_transfer(self.options["name"])
                for i, file in enumerate(self.files, 1):
                    self.progress.emit(f"Caricamento {i}/{len(self.files)}: {Path(file).name}")
                    nas.upload(folder, file)
                self.done.emit("Trasferimento completato. Link: " + nas.share(folder))
            finally:
                nas.logout()
        except Exception as exc:
            self.failed.emit(str(exc))


class UpdateCheck(QThread):
    result = Signal(object)
    failed = Signal(str)
    def run(self):
        try:
            self.result.emit(latest_release(APP_VERSION))
        except Exception as exc:
            self.failed.emit(str(exc))


class DownloadUpdate(QThread):
    done = Signal(str)
    failed = Signal(str)
    def __init__(self, release, parent=None):
        super().__init__(parent)
        self.release = release
    def run(self):
        try:
            self.done.emit(str(download_installer(self.release)))
        except Exception as exc:
            self.failed.emit(str(exc))


class PreferencesDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Impostazioni · IZI Transfer")
        self.resize(440, 190)
        layout = QVBoxLayout(self)
        self.auto = QCheckBox("Controlla automaticamente gli aggiornamenti all'avvio")
        self.auto.setChecked(parent.preferences.get("auto_updates", True))
        layout.addWidget(self.auto)
        info = QLabel("Gli aggiornamenti vengono cercati su GitHub Releases. "
                      "Dopo conferma vengono scaricati e installati automaticamente.")
        info.setWordWrap(True)
        info.setObjectName("hint")
        layout.addWidget(info)
        check = QPushButton("Controlla aggiornamenti adesso")
        check.clicked.connect(lambda: parent.check_updates(False))
        layout.addWidget(check)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)
        self.auto.toggled.connect(self.save_choice)
    def save_choice(self, checked):
        self.parent().preferences["auto_updates"] = checked
        save(self.parent().preferences)


class AboutDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("About IZI Transfer")
        self.resize(480, 310)
        layout = QVBoxLayout(self)
        title = QLabel("IZI Transfer")
        title.setObjectName("aboutName")
        layout.addWidget(title)
        version = QLabel("Version " + APP_VERSION)
        version.setObjectName("aboutSub")
        layout.addWidget(version)
        layout.addWidget(QLabel("Trasferimento file tra computer e tramite Synology NAS."))
        section = QLabel("WHAT'S NEW")
        section.setObjectName("sectionLabel")
        layout.addWidget(section)
        for _, _, notes in RELEASES[:1]:
            for note in notes:
                item = QLabel("• " + note)
                item.setWordWrap(True)
                layout.addWidget(item)
        layout.addStretch()
        layout.addWidget(QLabel("IZI Collection"))
        layout.addWidget(QLabel(COPYRIGHT))
        close = QPushButton("OK")
        close.setObjectName("primary")
        close.clicked.connect(self.accept)
        layout.addWidget(close)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IZI Transfer")
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.setMouseTracking(True)
        self.resize(760, 760)
        self.setMinimumSize(650, 670)
        self.files = []
        self.preferences = load()
        self.preferences.setdefault('device_id', uuid.uuid4().hex)
        self.preferences.setdefault('paired', {})
        save(self.preferences)
        self.devices = {}
        self.receiver = None
        self.worker = None
        self.discovery = Discovery(socket.gethostname() + "@" + self.preferences["device_id"], self.on_discovery)
        self.build()
        self.discovery.start()
        self.configure_tray()
        if self.preferences.get("auto_updates", True):
            QTimer.singleShot(2500, lambda: self.check_updates(True))
        if self.preferences.get('receive_enabled') and self.preferences.get('receive_code'):
            QTimer.singleShot(0, self.start_saved_receiver)

    def build(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        self.chrome = TitleBar("IZI Transfer")
        self.chrome.about.connect(self.open_about)
        outer.addWidget(self.chrome)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 12, 20, 16)
        content_layout.setSpacing(12)
        outer.addWidget(content, 1)
        outer = content_layout
        outer.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("IZI TRANSFER")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()
        self.menu_button = QPushButton("☰")
        self.menu_button.setObjectName("ghost")
        self.menu_button.setToolTip("Menu")
        menu = QMenu(self.menu_button)
        menu.addAction("Impostazioni", self.open_preferences)
        menu.addAction("About IZI Transfer", self.open_about)
        self.menu_button.setMenu(menu)
        header.addWidget(self.menu_button)
        outer.addLayout(header)
        subtitle = QLabel("Trasferimento file  ·  IZI Suite")
        subtitle.setObjectName("hint")
        outer.addWidget(subtitle)

        panel = QFrame()
        panel.setObjectName("panel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(11)
        outer.addWidget(panel, 1)

        heading = QLabel("TIPO DI TRASFERIMENTO")
        heading.setObjectName("sectionLabel")
        layout.addWidget(heading)
        self.mode = QComboBox()
        self.mode.addItems(["Locale · diretto", "Internet · Synology NAS"])
        self.mode.currentIndexChanged.connect(self.change_mode)
        layout.addWidget(self.mode)

        label = QLabel("NOME DEL TRASFERIMENTO")
        label.setObjectName("sectionLabel")
        layout.addWidget(label)
        self.name = QLineEdit()
        self.name.setPlaceholderText("Es. Matrimonio Marco e Giulia")
        layout.addWidget(self.name)

        label = QLabel("FILE")
        label.setObjectName("sectionLabel")
        layout.addWidget(label)
        self.file_list = QListWidget()
        layout.addWidget(self.file_list, 1)
        row = QHBoxLayout()
        add = QPushButton("Aggiungi file")
        add.clicked.connect(self.add_files)
        clear = QPushButton("Svuota elenco")
        clear.setObjectName("ghost")
        clear.clicked.connect(self.clear_files)
        row.addWidget(add)
        row.addWidget(clear)
        row.addStretch()
        layout.addLayout(row)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        local = QWidget()
        ll = QVBoxLayout(local)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.addWidget(QLabel("DISPOSITIVI DISPONIBILI"))
        self.peers = QComboBox()
        self.peers.setToolTip("Scegli il computer a cui inviare i file")
        ll.addWidget(self.peers)
        self.peers.addItem("Ricerca automatica dei dispositivi...", None)
        ll.addWidget(QLabel("CODICE SCELTO DAL DESTINATARIO"))
        self.receive_code = QLineEdit(self.preferences.get("receive_code", ""))
        self.receive_code.setPlaceholderText("Almeno 4 caratteri")
        ll.addWidget(self.receive_code)
        ll.addWidget(QLabel("CARTELLA DI RICEZIONE"))
        self.folder_mode = QComboBox()
        self.folder_mode.addItems(["Download", "Percorso personalizzato"])
        self.folder_mode.setCurrentIndex(1 if self.preferences.get("folder_mode") == "custom" else 0)
        ll.addWidget(self.folder_mode)
        self.folder_path = QLineEdit(self.preferences.get("folder_path", str(downloads_dir())))
        ll.addWidget(self.folder_path)
        self.choose_folder = QPushButton("Scegli percorso...")
        self.choose_folder.clicked.connect(self.pick_folder)
        ll.addWidget(self.choose_folder)
        self.folder_mode.currentIndexChanged.connect(self.update_folder_controls)
        self.update_folder_controls()
        receive = QPushButton("Attiva ricezione su questo computer")
        receive.clicked.connect(self.receive)
        ll.addWidget(receive)
        self.auto_receive = QCheckBox("Ricezione automatica all'avvio")
        self.auto_receive.setChecked(bool(self.preferences.get("receive_enabled")))
        self.auto_receive.toggled.connect(self.update_receive_preference)
        ll.addWidget(self.auto_receive)
        if sys.platform == "win32":
            self.startup = QCheckBox("Avvia in background con Windows")
            self.startup.setChecked(startup_enabled())
            self.startup.toggled.connect(self.change_startup)
            ll.addWidget(self.startup)
        self.receiver_info = QLabel("Ricezione non attiva")
        self.receiver_info.setObjectName("hint")
        self.receiver_info.setWordWrap(True)
        self.receiver_info.setMinimumHeight(24)
        ll.addWidget(self.receiver_info)
        self.stack.addWidget(local)

        internet = QWidget()
        il = QVBoxLayout(internet)
        il.setContentsMargins(0, 0, 0, 0)
        for text, attr, initial in [
            ("INDIRIZZO NAS (LAN)", "nas_url", "http://192.168.1.31:5000"),
            ("UTENTE", "nas_user", "izi-transfer"),
            ("PASSWORD", "nas_password", ""),
        ]:
            lab = QLabel(text)
            lab.setObjectName("sectionLabel")
            il.addWidget(lab)
            edit = QLineEdit(initial)
            if attr == "nas_password":
                edit.setEchoMode(QLineEdit.Password)
            setattr(self, attr, edit)
            il.addWidget(edit)
        note = QLabel("Accesso remoto non ancora disponibile. Non esporre DSM a Internet.")
        note.setObjectName("warn")
        il.addWidget(note)
        self.stack.addWidget(internet)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        outer.addWidget(self.progress)
        self.status = QLabel("Pronto")
        self.status.setObjectName("status")
        self.status.setWordWrap(True)
        outer.addWidget(self.status)
        self.send = QPushButton("Avvia trasferimento")
        self.send.setObjectName("primary")
        self.send.clicked.connect(self.start)
        outer.addWidget(self.send)
        footer = QLabel("IZI Transfer  ·  v" + APP_VERSION)
        footer.setObjectName("footer")
        outer.addWidget(footer)
        self.change_mode()

    def open_preferences(self):
        PreferencesDialog(self).exec()

    def open_about(self):
        AboutDialog(self).exec()

    def check_updates(self, silent=False):
        if hasattr(self, "update_worker") and self.update_worker.isRunning():
            return
        self.update_silent = silent
        self.update_worker = UpdateCheck(self)
        self.update_worker.result.connect(self.update_result)
        self.update_worker.failed.connect(self.update_error)
        self.update_worker.start()

    def update_result(self, release):
        if release:
            if not release.get("asset") or not release.get("digest"):
                if not self.update_silent:
                    QMessageBox.information(self, "Aggiornamenti", "Installer non ancora disponibile.")
                return
            answer = QMessageBox.question(self, "Aggiornamento disponibile",
                "IZI Transfer " + release["version"] +
                " è disponibile. Scaricare e installare automaticamente?")
            if answer == QMessageBox.Yes:
                self.status.setText("Download e verifica aggiornamento...")
                self.download_worker = DownloadUpdate(release, self)
                self.download_worker.done.connect(self.install_update)
                self.download_worker.failed.connect(self.update_error)
                self.download_worker.start()
        elif not self.update_silent:
            QMessageBox.information(self, "Aggiornamenti",
                                    "Nessun aggiornamento pubblicato su GitHub Releases.")

    def install_update(self, path):
        try:
            launch_installer(Path(path))
            self.status.setText("Installer avviato. IZI Transfer verrà aggiornato.")
            self.allow_close = True
            self.close()
        except Exception as exc:
            QMessageBox.warning(self, "Aggiornamento", str(exc))

    def update_error(self, error):
        if not self.update_silent:
            QMessageBox.warning(self, "Aggiornamenti", "Controllo non riuscito: " + error)

    def change_mode(self):
        self.stack.setCurrentIndex(self.mode.currentIndex())

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Seleziona file")
        for path in paths:
            if path not in self.files:
                self.files.append(path)
                self.file_list.addItem(Path(path).name)

    def clear_files(self):
        self.files.clear()
        self.file_list.clear()

    def on_discovery(self, devices):
        # Discovery runs on worker threads; no Qt widgets are accessed here.
        self.devices = devices

    def refresh_peers(self):
        previous = self.peers.currentData()
        selected_id = previous[2] if previous else None
        self.peers.blockSignals(True)
        self.peers.clear()
        for ip, (name, port, _) in sorted(self.devices.items()):
            self.peers.addItem(f"{name.split('@')[0]}  ·  disponibile", (ip, port, name.split("@")[-1]))
        if not self.devices:
            self.peers.addItem("Nessun dispositivo rilevato", None)
        else:
            for i in range(self.peers.count()):
                item = self.peers.itemData(i)
                if item and item[2] == selected_id:
                    self.peers.setCurrentIndex(i)
                    break
        self.peers.blockSignals(False)

    def pick_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Cartella di ricezione")
        if folder:
            self.folder_path.setText(folder)
            self.preferences["folder_path"] = folder
            save(self.preferences)

    def update_folder_controls(self):
        custom = self.folder_mode.currentIndex() == 1
        self.folder_path.setVisible(custom)
        self.choose_folder.setVisible(custom)
        self.preferences["folder_mode"] = "custom" if custom else "downloads"
        save(self.preferences)

    def update_receive_preference(self, enabled):
        self.preferences["receive_enabled"] = enabled
        save(self.preferences)
        if enabled and not self.receiver:
            self.receive()

    def change_startup(self, enabled):
        try:
            set_startup(enabled)
        except Exception as exc:
            QMessageBox.warning(self, "Avvio automatico", str(exc))
            self.startup.blockSignals(True)
            self.startup.setChecked(startup_enabled())
            self.startup.blockSignals(False)

    def receive(self):
        if self.receiver:
            self.status.setText("Ricezione già attiva. Riavvia per cambiare codice o cartella.")
            return
        code = self.receive_code.text().strip()
        if len(code) < 4:
            QMessageBox.warning(self, "Codice", "Scegli almeno 4 caratteri")
            return
        folder = str(downloads_dir()) if self.folder_mode.currentIndex() == 0 else self.folder_path.text().strip()
        if not folder or not Path(folder).is_dir():
            QMessageBox.warning(self, "Cartella", "Scegli una cartella esistente")
            return
        try:
            self.receiver = start_receiver(folder, code)
            self.preferences.update(receive_code=code, receive_enabled=True,
                                    folder_mode="custom" if self.folder_mode.currentIndex() else "downloads",
                                    folder_path=self.folder_path.text())
            save(self.preferences)
            self.auto_receive.setChecked(True)
            self.receiver_info.setText("Ricezione attiva · " + folder)
            self.status.setText("Ricezione attiva anche con finestra nascosta")
        except Exception as exc:
            QMessageBox.critical(self, "Ricezione", str(exc))

    def start_saved_receiver(self):
        self.receive_code.setText(self.preferences.get("receive_code", ""))
        self.receive()

    def configure_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon))
        menu = QMenu()
        menu.addAction("Apri IZI Transfer", self.show_normal)
        menu.addAction("Esci", self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.show_normal()
                                    if reason == QSystemTrayIcon.DoubleClick else None)
        self.tray.show()
        self.allow_close = False

    def show_normal(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def quit_app(self):
        self.allow_close = True
        self.close()


    def start(self):
        if not self.files:
            QMessageBox.warning(self, "IZI Transfer", "Aggiungi almeno un file")
            return
        if self.mode.currentIndex() == 0:
            self.refresh_peers()
            target = self.peers.currentData()
            if not target:
                QMessageBox.warning(self, "IZI Transfer", "Nessun dispositivo trovato nella LAN")
                return
            peer_key = target[2]
            code = self.preferences["paired"].get(peer_key)
            if not code:
                code, ok = QInputDialog.getText(self, "Prima autorizzazione",
                                                 "Codice scelto dal destinatario:")
                if not ok or not code:
                    return
            options = {"host": target[0], "port": target[1], "token": code}
            self.pending_pair = (peer_key, code)
            mode = "local"
        else:
            url = self.nas_url.text().strip()
            parsed = urlsplit(url)
            try:
                safe = parsed.scheme == "https" or (
                    parsed.scheme == "http" and ipaddress.ip_address(parsed.hostname).is_private
                )
            except ValueError:
                safe = False
            if not safe:
                QMessageBox.warning(self, "IZI Transfer", "Usa HTTPS o un indirizzo IP privato LAN")
                return
            if not self.name.text().strip():
                QMessageBox.warning(self, "IZI Transfer", "Inserisci il nome del trasferimento")
                return
            options = {"url": url, "user": self.nas_user.text().strip(),
                       "password": self.nas_password.text(), "name": self.name.text()}
            mode = "internet"
        self.worker = Job(mode, list(self.files), options)
        self.worker.progress.connect(self.status.setText)
        self.worker.done.connect(self.finish)
        self.worker.failed.connect(self.error)
        self.send.setEnabled(False)
        self.progress.setRange(0, 0)
        self.worker.start()

    def finish(self, text):
        if text == "Trasferimento locale completato" and hasattr(self, "pending_pair"):
            peer, code = self.pending_pair
            self.preferences["paired"][peer] = code
            save(self.preferences)
            del self.pending_pair
        self.status.setText(text)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.send.setEnabled(True)

    def error(self, text):
        self.status.setText("Errore: " + text)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.send.setEnabled(True)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and not self.isMaximized():
            margin = 7
            edges = Qt.Edge(0)
            if event.position().x() <= margin:
                edges |= Qt.LeftEdge
            elif event.position().x() >= self.width() - margin:
                edges |= Qt.RightEdge
            if event.position().y() <= margin:
                edges |= Qt.TopEdge
            elif event.position().y() >= self.height() - margin:
                edges |= Qt.BottomEdge
            if edges and self.windowHandle():
                self.windowHandle().startSystemResize(edges)
                event.accept()
                return
        super().mousePressEvent(event)

    def changeEvent(self, event):
        super().changeEvent(event)
        if hasattr(self, "chrome"):
            self.chrome.sync()

    def closeEvent(self, event):
        if not getattr(self, "allow_close", False) and self.tray.isVisible():
            self.hide()
            event.ignore()
            return
        self.discovery.stop()
        if self.receiver:
            self.receiver.shutdown()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    window = MainWindow()
    from PySide6.QtCore import QTimer
    timer = QTimer()
    timer.timeout.connect(window.refresh_peers)
    timer.start(1500)
    app.setQuitOnLastWindowClosed(False)
    if "--background" not in sys.argv:
        window.show()
    sys.exit(app.exec())
