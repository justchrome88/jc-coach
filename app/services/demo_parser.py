"""Compatibility facade for the canonical parsing boundary."""

from app.services.ingestion.demo_import import import_demo_file, import_inbox_demo, list_inbox_demos  # noqa: F401
from app.services.parsing.demo_parser import *  # noqa: F403
