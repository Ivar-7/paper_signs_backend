"""Entry point for local execution and production deployment."""

import os
import sys
import types

# Ensure parent and current directory are in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# If deployed with paper_signs_backend as root on Heroku, map paper_signs_backend to current package
if "paper_signs_backend" not in sys.modules:
    try:
        import paper_signs_backend  # noqa
    except ImportError:
        pkg = types.ModuleType("paper_signs_backend")
        pkg.__path__ = [current_dir]
        sys.modules["paper_signs_backend"] = pkg

import uvicorn
from paper_signs_backend.app.config import get_settings
from paper_signs_backend.app.main import app  # Export app for ASGI servers (Gunicorn/Uvicorn)

__all__ = ["app"]

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "run:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )

