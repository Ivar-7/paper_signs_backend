"""Compatibility shim                    re-exports from app/config/settings.py."""
from paper_signs_backend.app.config.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]