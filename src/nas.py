import os
import re
import requests
from pathlib import Path

class NasError(Exception):
    pass

class Synology:
    def __init__(self, base_url, username, password, shared_folder="IZI-Transfer"):
        self.base = base_url.rstrip("/")
        if not self.base.startswith(("http://", "https://")):
            raise NasError("Indirizzo NAS non valido")
        self.username = username
        self.password = password
        self.shared = shared_folder.strip("/")
        self.http = requests.Session()
        self.sid = None

    def call(self, api, version, method, **params):
        data = dict(api=api, version=version, method=method, **params)
        if self.sid:
            data["_sid"] = self.sid
        try:
            r = self.http.post(self.base + "/webapi/entry.cgi", data=data, timeout=40)
            r.raise_for_status()
            result = r.json()
        except (requests.RequestException, ValueError) as e:
            raise NasError(str(e)) from e
        if not result.get("success"):
            raise NasError(f"{api}.{method}: {result.get('error')}")
        return result.get("data", {})

    def login(self):
        result = self.call("SYNO.API.Auth", 6, "login", account=self.username,
                           passwd=self.password, session="FileStation", format="sid")
        self.sid = result["sid"]

    def logout(self):
        if self.sid:
            try:
                self.call("SYNO.API.Auth", 6, "logout", session="FileStation")
            finally:
                self.sid = None
                self.http.close()

    @staticmethod
    def clean_name(name):
        name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "_", name).strip().strip(".")
        if not name or name in (".", ".."):
            raise NasError("Inserisci un nome valido")
        return name[:100]

    def create_transfer(self, name):
        name = self.clean_name(name)
        parent = "/" + self.shared
        for i in range(1, 1000):
            folder = name if i == 1 else f"{name} ({i})"
            try:
                self.call("SYNO.FileStation.CreateFolder", 2, "create",
                          folder_path=parent, name=folder, force_parent="false")
                return parent + "/" + folder
            except NasError as e:
                # Only retry if Synology reports an already existing folder (error 1100).
                if "1100" not in str(e):
                    raise
        raise NasError("Troppi trasferimenti con lo stesso nome")

    def upload(self, destination, file_path):
        path = Path(file_path)
        with path.open("rb") as stream:
            data = dict(api="SYNO.FileStation.Upload", version="3", method="upload",
                        path=destination, create_parents="false", overwrite="false")
            if self.sid:
                data["_sid"] = self.sid
            try:
                r = self.http.post(self.base + "/webapi/entry.cgi", data=data,
                                   files={"file": (path.name, stream)}, timeout=(15, 3600))
                r.raise_for_status()
                result = r.json()
            except (requests.RequestException, ValueError) as e:
                raise NasError(str(e)) from e
            if not result.get("success"):
                raise NasError(f"Upload {path.name}: {result.get('error')}")

    def share(self, path):
        data = self.call("SYNO.FileStation.Sharing", 3, "create", path=path)
        links = data.get("links", [])
        if not links:
            raise NasError("Link non restituito dal NAS")
        return links[0].get("url", "")
