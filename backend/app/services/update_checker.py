import json
import re
import time
import urllib.request
import urllib.error
from typing import Optional, Dict, Any
from app.config import get_settings

# In-memory cache for GitHub release checks (30 minutes TTL)
_UPDATE_CACHE: Dict[str, Any] = {
    "data": None,
    "timestamp": 0,
    "ttl_seconds": 1800,  # 30 minutes
}

GITHUB_REPO = "prasadshinde10/MHTCET-cap-allotment"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def parse_semver(v_str: str) -> tuple:
    """
    Parses a version string like 'v1.1.0' or '1.0.0-beta' into a tuple of ints (1, 1, 0).
    """
    cleaned = re.sub(r'^[vV]', '', v_str.strip())
    match = re.match(r'^(\d+)(?:\.(\d+))?(?:\.(\d+))?', cleaned)
    if not match:
        return (0, 0, 0)
    parts = match.groups()
    return tuple(int(p) if p is not None else 0 for p in parts)


def check_github_releases(force_refresh: bool = False) -> Dict[str, Any]:
    """
    Checks GitHub Releases for the latest version and compares with current local APP_VERSION.
    Results are cached for 30 minutes unless force_refresh is True.
    """
    now = time.time()
    settings = get_settings()
    current_version_str = getattr(settings, "APP_VERSION", "1.0.0")
    current_semver = parse_semver(current_version_str)

    if not force_refresh and _UPDATE_CACHE["data"] and (now - _UPDATE_CACHE["timestamp"] < _UPDATE_CACHE["ttl_seconds"]):
        cached = _UPDATE_CACHE["data"].copy()
        # Recalculate update_available in case app_version changed
        latest_semver = parse_semver(cached.get("latest_version", "0.0.0"))
        cached["current_version"] = current_version_str
        cached["update_available"] = latest_semver > current_semver
        return cached

    req = urllib.request.Request(
        GITHUB_API_URL,
        headers={
            "User-Agent": "MHTCET-Cutoff-Portal-Updater",
            "Accept": "application/vnd.github.v3+json",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            if response.status == 200:
                raw_data = json.loads(response.read().decode("utf-8"))
                
                tag_name = raw_data.get("tag_name", "")
                latest_semver = parse_semver(tag_name)
                update_available = latest_semver > current_semver

                # Find the primary desktop download asset (.zip or .exe)
                assets = raw_data.get("assets", [])
                primary_asset = None
                for a in assets:
                    name_lower = a.get("name", "").lower()
                    if name_lower.endswith(".zip") or name_lower.endswith(".exe"):
                        primary_asset = a
                        break
                
                download_url = None
                asset_name = None
                asset_size_mb = None

                if primary_asset:
                    download_url = primary_asset.get("browser_download_url")
                    asset_name = primary_asset.get("name")
                    size_bytes = primary_asset.get("size")
                    if size_bytes:
                        asset_size_mb = round(size_bytes / (1024 * 1024), 1)
                else:
                    download_url = raw_data.get("html_url")

                result = {
                    "current_version": current_version_str,
                    "latest_version": tag_name,
                    "update_available": update_available,
                    "release_title": raw_data.get("name") or tag_name,
                    "release_notes": raw_data.get("body") or "",
                    "published_at": raw_data.get("published_at"),
                    "release_url": raw_data.get("html_url"),
                    "download_url": download_url,
                    "asset_name": asset_name,
                    "asset_size_mb": asset_size_mb,
                    "cached": False,
                    "checked_at": int(now),
                    "error": None,
                }

                _UPDATE_CACHE["data"] = result
                _UPDATE_CACHE["timestamp"] = now
                return result

    except urllib.error.HTTPError as e:
        error_msg = f"GitHub API error HTTP {e.code}"
        if e.code == 403:
            error_msg = "GitHub API rate limit exceeded. Please try again later."
        elif e.code == 404:
            error_msg = "No releases found on GitHub repository."
    except urllib.error.URLError as e:
        error_msg = f"Network connection issue: {e.reason}"
    except Exception as e:
        error_msg = f"Update check failed: {str(e)}"

    fallback = {
        "current_version": current_version_str,
        "latest_version": current_version_str,
        "update_available": False,
        "release_title": None,
        "release_notes": None,
        "published_at": None,
        "release_url": f"https://github.com/{GITHUB_REPO}/releases",
        "download_url": None,
        "asset_name": None,
        "asset_size_mb": None,
        "cached": False,
        "checked_at": int(now),
        "error": error_msg,
    }
    return fallback
