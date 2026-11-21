"""
Desktop Application Entrypoint for CAP Cutoff & Allotment Portal
Runs FastAPI backend, serves embedded frontend, and opens the default browser.
"""

import os
import sys
import time
import socket
import webbrowser
import threading
import logging

# Ensure root directory and backend directory are in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False):
    # PyInstaller bundle directory
    BASE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)

backend_dir = os.path.join(BASE_DIR, "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Set production environment defaults if not set
os.environ.setdefault("APP_ENV", "production")
os.environ.setdefault("PORT", "8000")
os.environ["IS_DESKTOP_STANDALONE"] = "1"
os.environ["APP_RUNTIME"] = "desktop"

# Ensure desktop uses local SQLite cutoff.db by default
if "DATABASE_URL" not in os.environ or "postgresql" in os.environ.get("DATABASE_URL", ""):
    cutoff_path = os.path.join(BASE_DIR, "backend", "cutoff.db")
    if not os.path.exists(cutoff_path):
        cutoff_path = os.path.join(BASE_DIR, "cutoff.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{os.path.abspath(cutoff_path)}"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("desktop_app")


def create_server_socket(host: str = "127.0.0.1", port: int = 8000) -> socket.socket:
    """Creates a bound listening socket, falling back to dual-stack IPv6 if IPv4 bind fails."""
    if ":" not in host:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.bind((host, port))
            sock.listen(128)
            sock.set_inheritable(True)
            return sock
        except OSError:
            sock.close()
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if hasattr(socket, "SO_REUSEPORT"):
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    sock.bind(('::', port))
    sock.listen(128)
    sock.set_inheritable(True)
    return sock


def bind_available_socket(default_port: int = 8000, max_attempts: int = 10) -> tuple[socket.socket, int]:
    """Finds and binds an available TCP socket starting from default_port, returning (socket, port)."""
    for p in range(default_port, default_port + max_attempts):
        try:
            sock = create_server_socket("127.0.0.1", p)
            return sock, p
        except Exception:
            continue
    return create_server_socket("127.0.0.1", default_port), default_port


def open_browser(url: str, delay_seconds: float = 1.2):
    """Opens the user's default browser after the server has bound the port."""
    if os.environ.get("NO_BROWSER", "").lower() in ("1", "true", "yes"):
        return
    time.sleep(delay_seconds)
    logger.info(f"Opening browser at: {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        logger.warning(f"Could not open browser automatically: {e}")


def main():
    print("=" * 60)
    print("  MHT-CET CAP Cutoff & Seat Allotment Portal — Desktop Edition")
    print("=" * 60)

    # Database initialization check
    try:
        from app.database import engine, SessionLocal
        from app.models.base import Base
        import app.models  # ensure models registered
        from app.auth.seed import seed_admin_user

        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        seed_admin_user(db)
        db.close()
        logger.info("Local database verified.")
    except Exception as e:
        logger.warning(f"Database initialization note: {e}")

    # Determine port and bind socket
    sock, port = bind_available_socket(8000)
    url = f"http://localhost:{port}"

    print(f"\n-> Server starting at: {url}")
    print("-> Default Admin Login: admin / admin123")
    print("-> Press Ctrl+C in this window to stop the application.\n")

    # Start browser opener in background thread
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    # Start Uvicorn server
    try:
        import uvicorn
        from app.main import app

        cfg = uvicorn.Config(app, log_level="info", access_log=False)
        uvicorn.Server(cfg).run(sockets=[sock])
    except KeyboardInterrupt:
        print("\nShutting down portal. Goodbye!")
    except Exception as e:
        logger.critical(f"Server error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
