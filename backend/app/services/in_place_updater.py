import os
import sys
import time
import shutil
import zipfile
import tempfile
import threading
import subprocess
import urllib.request
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from app.services.update_checker import check_github_releases

logger = logging.getLogger("in_place_updater")

_UPDATE_LOCK = threading.Lock()

_PROGRESS: Dict[str, Any] = {
    "status": "idle",  # "idle" | "downloading" | "extracting" | "ready" | "failed"
    "progress_percent": 0,
    "downloaded_bytes": 0,
    "total_bytes": 0,
    "downloaded_mb": 0.0,
    "total_mb": 0.0,
    "message": "",
    "target_version": "",
    "error": None,
    "staging_dir": None,
}


def get_current_progress() -> Dict[str, Any]:
    with _UPDATE_LOCK:
        return _PROGRESS.copy()


def _set_progress(**kwargs):
    with _UPDATE_LOCK:
        _PROGRESS.update(kwargs)


def _get_app_directory() -> str:
    """Returns the base root directory of the application."""
    if getattr(sys, "frozen", False):
        # PyInstaller packaged executable
        return os.path.dirname(os.path.abspath(sys.executable))
    # Source / script repository root
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _download_and_stage_worker(download_url: str, target_version: str):
    temp_dir = None
    try:
        _set_progress(
            status="downloading",
            progress_percent=0,
            downloaded_bytes=0,
            total_bytes=0,
            downloaded_mb=0.0,
            total_mb=0.0,
            message="Connecting to download server...",
            target_version=target_version,
            error=None,
        )

        temp_dir = tempfile.mkdtemp(prefix="cap_portal_update_")
        zip_path = os.path.join(temp_dir, "update.zip")
        staging_dir = os.path.join(temp_dir, "staged")
        os.makedirs(staging_dir, exist_ok=True)

        req = urllib.request.Request(
            download_url,
            headers={
                "User-Agent": "MHTCET-Cutoff-Portal-Updater",
                "Accept": "*/*",
            }
        )

        with urllib.request.urlopen(req, timeout=30) as response, open(zip_path, "wb") as out_file:
            total_size_hdr = response.headers.get("Content-Length")
            total_bytes = int(total_size_hdr) if total_size_hdr and total_size_hdr.isdigit() else 0
            total_mb = round(total_bytes / (1024 * 1024), 1) if total_bytes else 0.0

            downloaded = 0
            chunk_size = 64 * 1024  # 64 KB chunks
            last_report_time = time.time()

            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                out_file.write(chunk)
                downloaded += len(chunk)

                now = time.time()
                if now - last_report_time > 0.25 or downloaded == total_bytes:
                    last_report_time = now
                    percent = round((downloaded / total_bytes * 100), 1) if total_bytes > 0 else 0
                    downloaded_mb = round(downloaded / (1024 * 1024), 1)
                    _set_progress(
                        progress_percent=percent,
                        downloaded_bytes=downloaded,
                        total_bytes=total_bytes,
                        downloaded_mb=downloaded_mb,
                        total_mb=total_mb,
                        message=f"Downloading update: {downloaded_mb} MB / {total_mb or '?'} MB ({percent}%)",
                    )

        # Extraction phase
        _set_progress(
            status="extracting",
            progress_percent=95,
            message="Extracting and verifying software update...",
        )

        if not zipfile.is_zipfile(zip_path):
            raise ValueError("Downloaded file is not a valid zip archive.")

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(staging_dir)

        # Normalize staging folder if files are nested in a subfolder
        extracted_items = os.listdir(staging_dir)
        actual_source_dir = staging_dir
        if len(extracted_items) == 1 and os.path.isdir(os.path.join(staging_dir, extracted_items[0])):
            actual_source_dir = os.path.join(staging_dir, extracted_items[0])

        _set_progress(
            status="ready",
            progress_percent=100,
            message=f"Version {target_version} is ready to install.",
            staging_dir=actual_source_dir,
        )
        logger.info(f"Update package {target_version} staged at {actual_source_dir}")

    except Exception as e:
        logger.error(f"In-place update failed: {e}", exc_info=True)
        _set_progress(
            status="failed",
            message=f"Update failed: {str(e)}",
            error=str(e),
        )
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass


def start_in_place_update() -> Dict[str, Any]:
    """Initiates the download and staging of the latest release."""
    with _UPDATE_LOCK:
        if _PROGRESS["status"] in ("downloading", "extracting"):
            return {
                "started": False,
                "message": "An update is already in progress.",
                "progress": _PROGRESS.copy(),
            }

    release_info = check_github_releases(force_refresh=True)
    if not release_info.get("update_available") and not release_info.get("download_url"):
        return {
            "started": False,
            "message": "No new update package found.",
            "progress": get_current_progress(),
        }

    download_url = release_info.get("download_url")
    target_version = release_info.get("latest_version") or "Latest"

    if not download_url:
        return {
            "started": False,
            "message": "No downloadable release asset (.zip) found on GitHub.",
            "progress": get_current_progress(),
        }

    worker = threading.Thread(
        target=_download_and_stage_worker,
        args=(download_url, target_version),
        daemon=True,
        name="update_download_worker",
    )
    worker.start()

    return {
        "started": True,
        "message": f"Downloading update {target_version} in background.",
        "progress": get_current_progress(),
    }


def restart_and_apply_update() -> Dict[str, Any]:
    """
    Creates a detached updater script, launches it, and terminates the current process.
    """
    with _UPDATE_LOCK:
        if _PROGRESS["status"] != "ready":
            return {
                "success": False,
                "message": f"Cannot apply update: current status is '{_PROGRESS['status']}'.",
            }
        staging_dir = _PROGRESS.get("staging_dir")

    if not staging_dir or not os.path.exists(staging_dir):
        return {
            "success": False,
            "message": "Staged update files could not be found.",
        }

    app_dir = _get_app_directory()
    logger.info(f"Applying update from {staging_dir} into {app_dir}")

    # Backup active SQLite databases if they exist
    try:
        backup_dir = os.path.join(app_dir, "backups", f"pre_update_{int(time.time())}")
        os.makedirs(backup_dir, exist_ok=True)
        for db_name in ["cutoff.db", "csab.db", "josaa.db", "medical.db", "iiser.db"]:
            for folder in [app_dir, os.path.join(app_dir, "backend")]:
                src = os.path.join(folder, db_name)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(backup_dir, db_name))
        logger.info(f"Database pre-update backup saved to {backup_dir}")
    except Exception as e:
        logger.warning(f"Could not complete pre-update backup: {e}")

    # Platform-specific detached script
    is_windows = sys.platform.startswith("win")
    script_dir = tempfile.gettempdir()

    if is_windows:
        updater_script = os.path.join(script_dir, "apply_cap_portal_update.bat")
        with open(updater_script, "w", encoding="utf-8") as f:
            f.write(f"""@echo off
chcp 65001 > nul
echo ======================================================
echo   Applying CAP Allotment Portal In-Place Update...
echo ======================================================
echo Waiting for existing application process to close...
timeout /t 3 /nobreak > nul

echo Overwriting application files...
xcopy /E /Y /I "{staging_dir}\\*" "{app_dir}\\"

echo Cleaning up staging directory...
rmdir /S /Q "{staging_dir}"

echo Restarting application...
cd /d "{app_dir}"
if exist "{app_dir}\\CAP_Portal.exe" (
    start "" "{app_dir}\\CAP_Portal.exe"
) else if exist "{app_dir}\\start.bat" (
    start "" "{app_dir}\\start.bat"
)
exit
""")
        # Launch detached batch script
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        subprocess.Popen(
            ["cmd.exe", "/c", updater_script],
            creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
            close_fds=True,
        )

    else:
        updater_script = os.path.join(script_dir, "apply_cap_portal_update.sh")
        with open(updater_script, "w", encoding="utf-8") as f:
            f.write(f"""#!/bin/bash
sleep 3
echo "Applying update to {app_dir}..."
cp -rf "{staging_dir}"/* "{app_dir}"/
rm -rf "{staging_dir}"
cd "{app_dir}"
if [ -f "{app_dir}/CAP_Portal" ]; then
    nohup "{app_dir}/CAP_Portal" > /dev/null 2>&1 &
elif [ -f "{app_dir}/desktop_app.py" ]; then
    nohup python3 "{app_dir}/desktop_app.py" > /dev/null 2>&1 &
fi
rm -f "$0"
""")
        os.chmod(updater_script, 0o755)
        subprocess.Popen(
            ["/bin/bash", updater_script],
            start_new_session=True,
            close_fds=True,
        )

    # Schedule exit after responding to client
    def _delayed_exit():
        time.sleep(1.0)
        logger.info("Process terminating for in-place self update.")
        os._exit(0)

    threading.Thread(target=_delayed_exit, daemon=True).start()

    return {
        "success": True,
        "message": "Update script launched. Application is restarting...",
    }
