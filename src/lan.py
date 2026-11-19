"""Ricevitore LAN con codice scelto dall'utente e credenziali per mittente."""
import hashlib
import hmac
import http.server
import secrets
import threading
import urllib.parse
from pathlib import Path
import requests

MAX_FAILED = 10

def token_for(code):
    if not isinstance(code, str) or len(code) < 4 or len(code) > 64:
        raise ValueError("Il codice deve avere da 4 a 64 caratteri")
    return hashlib.sha256(("IZI-TRANSFER-LAN-V2:" + code).encode("utf-8")).hexdigest()

class Receiver(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    def __init__(self, address, directory, code):
        super().__init__(address, UploadHandler)
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.token = token_for(code)
        self.failures = {}
        self.lock = threading.Lock()

class UploadHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if urllib.parse.urlsplit(self.path).path != "/pair":
            self.send_error(404)
            return
        peer = self.client_address[0]
        with self.server.lock:
            if self.server.failures.get(peer, 0) >= MAX_FAILED:
                self.send_error(429, "Troppi tentativi")
                return
        supplied = self.headers.get("X-IZI-Token", "")
        if not hmac.compare_digest(supplied, self.server.token):
            with self.server.lock:
                self.server.failures[peer] = self.server.failures.get(peer, 0) + 1
            self.send_error(403, "Codice non valido")
            return
        self.send_response(204)
        self.end_headers()

    def do_PUT(self):
        peer = self.client_address[0]
        with self.server.lock:
            if self.server.failures.get(peer, 0) >= MAX_FAILED:
                self.send_error(429, "Troppi tentativi")
                return
        supplied = self.headers.get("X-IZI-Token", "")
        if not hmac.compare_digest(supplied, self.server.token):
            with self.server.lock:
                self.server.failures[peer] = self.server.failures.get(peer, 0) + 1
            self.send_error(403, "Codice non valido")
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            self.send_error(400)
            return
        if length < 0:
            self.send_error(411)
            return
        name = urllib.parse.unquote(urllib.parse.urlsplit(self.path).path.lstrip("/"))
        if not name or "/" in name or "\\" in name or name in (".", ".."):
            self.send_error(400)
            return
        target = self.server.directory / name
        if target.exists():
            self.send_error(409, "File esistente")
            return
        try:
            with target.open("xb") as f:
                remaining = length
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ConnectionError("Invio interrotto")
                    f.write(chunk)
                    remaining -= len(chunk)
            self.send_response(201)
            self.end_headers()
        except Exception:
            target.unlink(missing_ok=True)
            self.send_error(500)

def start_receiver(directory, code, port=8765):
    server = Receiver(("0.0.0.0", port), directory, code)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server

def send_file(host, port, code, file_path):
    path = Path(file_path)
    url = f"http://{host}:{port}/" + urllib.parse.quote(path.name)
    with path.open("rb") as f:
        response = requests.put(url, data=f,
                                headers={"X-IZI-Token": token_for(code),
                                         "Content-Length": str(path.stat().st_size)},
                                timeout=(10, 3600))
        response.raise_for_status()

def verify_pairing(host, port, code):
    """Confirm the recipient is online and accepts the code before remembering it."""
    url = f"http://{host}:{port}/pair"
    response = requests.get(url, headers={"X-IZI-Token": token_for(code)}, timeout=(4, 8))
    response.raise_for_status()
    return True
