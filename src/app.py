"""IZI Transfer - interfaccia PySide6 nello stile originale IZI Retrieve."""
import ipaddress
import socket
import sys
from pathlib import Path
from urllib.parse import urlsplit

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QListWidget, QFileDialog, QComboBox, QStackedWidget,
    QFrame, QMessageBox, QProgressBar,
)
from izi_style import QSS
from discovery import Discovery
from nas import Synology
from lan import start_receiver, send_file


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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IZI Transfer")
        self.resize(760, 660)
        self.files = []
        self.devices = {}
        self.receiver = None
        self.worker = None
        self.discovery = Discovery(socket.gethostname(), self.on_discovery)
        self.build()
        self.discovery.start()

    def build(self):
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(20, 20, 20, 16)
        outer.setSpacing(12)

        title = QLabel("IZI TRANSFER")
        title.setObjectName("titleLabel")
        outer.addWidget(title)
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
        ll.addWidget(self.peers)
        self.peers.addItem("Ricerca automatica dei dispositivi...", None)
        receive = QPushButton("Attiva ricezione su questo computer")
        receive.clicked.connect(self.receive)
        ll.addWidget(receive)
        self.receiver_info = QLabel("Per ricevere, attiva la ricezione sul computer destinatario.")
        self.receiver_info.setObjectName("hint")
        self.receiver_info.setWordWrap(True)
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
        footer = QLabel("IZI Transfer  ·  versione di prova")
        footer.setObjectName("footer")
        outer.addWidget(footer)
        self.change_mode()

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
        self.peers.clear()
        for ip, (name, port, _) in sorted(self.devices.items()):
            self.peers.addItem(f"{name}  ·  disponibile", (ip, port))
        if not self.devices:
            self.peers.addItem("Nessun dispositivo rilevato", None)
        else:
            for i in range(self.peers.count()):
                if self.peers.itemData(i) == previous:
                    self.peers.setCurrentIndex(i)
                    break

    def receive(self):
        if self.receiver:
            return
        folder = QFileDialog.getExistingDirectory(self, "Scegli cartella di ricezione")
        if not folder:
            return
        try:
            self.receiver, token = start_receiver(folder)
            self.receiver_info.setText("Ricezione attiva. Codice temporaneo: " + token +
                                       "\nIl mittente dovrà inserire il codice di autorizzazione.")
            self.status.setText("Ricezione attiva")
        except Exception as e:
            QMessageBox.critical(self, "Errore", str(e))

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
            from PySide6.QtWidgets import QInputDialog
            token, ok = QInputDialog.getText(self, "Autorizzazione", "Codice mostrato dal destinatario:")
            if not ok or not token:
                return
            options = {"host": target[0], "port": target[1], "token": token}
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
        self.status.setText(text)
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.send.setEnabled(True)

    def error(self, text):
        self.status.setText("Errore: " + text)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.send.setEnabled(True)

    def closeEvent(self, event):
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
    window.show()
    sys.exit(app.exec())
