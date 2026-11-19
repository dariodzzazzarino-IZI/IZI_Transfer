"""Controllo aggiornamenti su GitHub Releases, senza eseguire file scaricati."""
import requests
from packaging.version import Version, InvalidVersion

RELEASE_API = "https://api.github.com/repos/dariodzzazzarino-IZI/IZI_Transfer/releases/latest"

def latest_release(current):
    response = requests.get(RELEASE_API, headers={"Accept": "application/vnd.github+json"},
                            timeout=12)
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
    return {"version": tag, "url": data.get("html_url", ""),
            "notes": data.get("body", "")}
