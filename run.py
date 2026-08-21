"""Entry point - run from the project root: python paper_signs_backend/run.py"""

import sys
import os

# Ensure project root is in sys.path so paper_signs_backend.* imports resolve
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from paper_signs_backend.app.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "paper_signs_backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
