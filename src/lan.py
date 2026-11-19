import http.server
import os
import secrets
import threading
import urllib.parse
from pathlib import Path
import requests

class Receiver(http.server.ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, address, directory, token):
        super().__init__(address, UploadHandler)
        self.directory = Path(directory).resolve()
        self.token = token

class UploadHandler(http.server.BaseHTTPRequestHandler):
    def do_PUT(self):
        if self.headers.get("X-IZI-Token") != self.server.token:
            self.send_error(403)
            return
        length = int(self.headers.get("Content-Length", "-1"))
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

def start_receiver(directory, port=8765):
    token = secrets.token_urlsafe(18)
    server = Receiver(("0.0.0.0", port), directory, token)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, token

def send_file(host, port, token, file_path):
    path = Path(file_path)
    url = f"http://{host}:{port}/" + urllib.parse.quote(path.name)
    with path.open("rb") as f:
        response = requests.put(url, data=f,
                                headers={"X-IZI-Token": token,
                                         "Content-Length": str(path.stat().st_size)},
                                timeout=(10, 3600))
        response.raise_for_status()
