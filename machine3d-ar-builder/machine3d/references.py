"""Optional automatic reference discovery, with provenance and offline fallback.

Downloads only explicitly identified public-domain or Creative Commons works from
Wikimedia Commons. Images are for *visual guidance*, not dimensional authority.
"""
from __future__ import annotations
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
import json
import re
import urllib.parse
import urllib.request

API = "https://commons.wikimedia.org/w/api.php"
def allowed_license(license_name: str, license_url: str) -> bool:
    """Exclude NC/ND and unknown licenses; accept CC0, CC BY, CC BY-SA, and PD."""
    name = license_name.strip().casefold().replace("_", "-")
    url = license_url.strip().casefold()
    if "public domain" in name or name.startswith(("pd-self", "pd-old", "pd-us", "cc0")):
        return True
    if "/publicdomain/" in url or "/licenses/zero/" in url:
        return True
    if "-nc" in name or "-nd" in name or "/by-nc" in url or "/by-nd" in url:
        return False
    if name.startswith(("cc by-sa", "cc by ", "cc-by-sa", "cc-by ")):
        return True
    return "/licenses/by/" in url or "/licenses/by-sa/" in url
DEFAULT_QUERIES = [
    "two stroke engine diagram",
    "two stroke engine piston connecting rod",
    "two stroke engine cutaway",
]


def _plain(s: str) -> str:
    return re.sub(r"<[^>]+>", "", unescape(s or "")).strip()


def _request_json(params: dict, *, timeout: int = 9) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Machine3DARBuilder/0.1 (educational prototype; contact: local-user)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def collect_references(folder: Path, *, offline: bool = False, max_images: int = 3, queries: list[str] | None = None) -> dict:
    """Collect public reference images or record a documented fallback.

    The skill can additionally use an agent's own web/image tool and manually append
    sources to `reference_manifest.json`. Never infer dimensions from an image alone.
    """
    folder.mkdir(parents=True, exist_ok=True)
    manifest = {
        "createdUTC": datetime.now(timezone.utc).isoformat(),
        "policy": "Reference images are not dimensionally authoritative; verify licensing before redistribution.",
        "sources": [],
        "fallback": "procedural geometry from conceptual dimensions in geometry_spec.json",
        "mode": "offline" if offline else "auto-search",
    }
    if not offline:
        for query in (queries if queries is not None else DEFAULT_QUERIES):
            if len(manifest["sources"]) >= max_images:
                break
            try:
                search = _request_json({
                    "action": "query", "format": "json", "list": "search", "srnamespace": 6,
                    "srsearch": query, "srlimit": 8,
                })
                titles = [p["title"] for p in search.get("query", {}).get("search", [])]
                if not titles:
                    continue
                details = _request_json({
                    "action": "query", "format": "json", "prop": "imageinfo",
                    "iiprop": "url|extmetadata", "titles": "|".join(titles),
                })
                for page in details.get("query", {}).get("pages", {}).values():
                    if len(manifest["sources"]) >= max_images:
                        break
                    info = (page.get("imageinfo") or [{}])[0]
                    meta = info.get("extmetadata") or {}
                    license_name = _plain((meta.get("LicenseShortName") or {}).get("value", ""))
                    license_url = (meta.get("LicenseUrl") or {}).get("value", "")
                    if not allowed_license(license_name, license_url):
                        continue
                    source_url = info.get("url", "")
                    suffix = Path(urllib.parse.urlparse(source_url).path).suffix.lower()
                    if suffix not in (".png", ".jpg", ".jpeg", ".webp"):
                        continue
                    file_name = "reference_%02d%s" % (len(manifest["sources"]) + 1, suffix)
                    img_req = urllib.request.Request(source_url, headers={"User-Agent": "Machine3DARBuilder/0.1 (educational reference)"})
                    with urllib.request.urlopen(img_req, timeout=12) as response:
                        content = response.read(8 * 1024 * 1024 + 1)
                    if len(content) > 8 * 1024 * 1024:
                        continue
                    (folder / file_name).write_bytes(content)
                    manifest["sources"].append({
                        "file": file_name, "title": page.get("title", ""),
                        "pageURL": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(page.get("title", "").replace(" ", "_")),
                        "sourceURL": source_url,
                        "license": license_name, "licenseURL": license_url,
                        "attribution": _plain((meta.get("Artist") or {}).get("value", "")),
                        "purpose": "visual reference only; not verified engineering CAD",
                    })
            except (OSError, ValueError, KeyError, TimeoutError) as e:
                manifest.setdefault("errors", []).append(f"{query}: {type(e).__name__}: {e}")
    if not manifest["sources"]:
        manifest["status"] = "fallback-geometry-without-external-images"
    else:
        manifest["status"] = "reference-images-available"
    (folder / "reference_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
