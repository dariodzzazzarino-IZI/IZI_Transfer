"""Release metadata and verified installer download."""
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import requests
from packaging.version import Version, InvalidVersion

RELEASE_API = "https://api.github.com/repos/dariodzzazzarino-IZI/IZI_Transfer/releases/latest"

def latest_release(current):
    response = requests.get(RELEASE_API, headers={"Accept": "application/vnd.github+json"}, timeout=12)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    data = response.json()
    tag = str(data.get("tag_name", "")).lstrip("vV")
    try:
        newer = Version(tag) > Version(current)
    except InvalidVersion:
        return None
    if not newer:
        return None
    platform = "Windows" if sys.platform == "win32" else "macOS" if sys.platform == "darwin" else None
    filename = f"IZI-Transfer-{tag}-{platform}-Setup.exe" if platform == "Windows" else f"IZI-Transfer-{tag}-{platform}-Setup.zip"
    asset = next((a for a in data.get("assets", []) if a.get("name") == filename), None)
    digest = asset.get("digest", "") if asset else ""
    return {"version": tag, "url": data.get("html_url", ""), "notes": data.get("body", ""),
            "asset": asset.get("browser_download_url") if asset else None,
            "digest": digest, "filename": filename}

def download_installer(release):
    url = release.get("asset")
    digest = release.get("digest", "")
    if not url or not url.startswith(
            "https://github.com/dariodzzazzarino-IZI/IZI_Transfer/releases/download/"):
        raise RuntimeError("Installer ufficiale non disponibile")
    if not digest.startswith("sha256:"):
        raise RuntimeError("Checksum SHA-256 della release non disponibile")
    folder = Path(tempfile.mkdtemp(prefix="izi-transfer-update-"))
    path = folder / release["filename"]
    sha = hashlib.sha256()
    with requests.get(url, stream=True, timeout=(15, 90)) as response:
        response.raise_for_status()
        with path.open("wb") as output:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output.write(chunk)
                    sha.update(chunk)
    if sha.hexdigest().lower() != digest[7:].lower():
        path.unlink(missing_ok=True)
        raise RuntimeError("Verifica integrità dell'aggiornamento non riuscita")
    return path

def launch_installer(path):
    if sys.platform == "win32":
        subprocess.Popen([str(path), "--auto"], close_fds=True)
    elif sys.platform == "darwin":
        import zipfile
        with zipfile.ZipFile(path) as archive:
            archive.extractall(path.parent)
        app = path.parent / "IZI-Transfer-Setup.app"
        if not app.is_dir():
            raise RuntimeError("Installer macOS non trovato nell’archivio")
        subprocess.Popen(["open", str(app)])
    else:
        raise RuntimeError("Sistema operativo non supportato")
