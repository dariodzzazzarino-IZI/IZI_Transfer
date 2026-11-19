"""Rilevamento dispositivi IZI Transfer tramite UDP broadcast nella LAN."""
import json
import socket
import threading
import time

PORT = 37654
MAGIC = "IZI_TRANSFER_DISCOVERY_V1"

class Discovery:
    def __init__(self, name, on_update, receive_port=8765):
        self.name = name
        self.on_update = on_update
        self.receive_port = receive_port
        self.devices = {}
        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self.listen, daemon=True).start()
        threading.Thread(target=self.announce, daemon=True).start()

    def stop(self):
        self.running = False

    def listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("", PORT))
            sock.settimeout(1)
            while self.running:
                try:
                    raw, addr = sock.recvfrom(2048)
                    data = json.loads(raw.decode("utf-8"))
                    if data.get("magic") != MAGIC or data.get("name") == self.name:
                        continue
                    self.devices[data["name"]] = (addr[0], int(data.get("port", 8765)), time.time())
                    self.on_update(dict(self.devices))
                except (socket.timeout, ValueError, KeyError, UnicodeError):
                    pass
        finally:
            sock.close()

    def announce(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            while self.running:
                data = json.dumps({"magic": MAGIC, "name": self.name, "port": self.receive_port}).encode()
                try:
                    sock.sendto(data, ("255.255.255.255", PORT))
                except OSError:
                    pass
                now = time.time()
                self.devices = {name: v for name, v in self.devices.items() if now - v[2] < 12}
                self.on_update(dict(self.devices))
                time.sleep(3)
        finally:
            sock.close()
