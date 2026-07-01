from pathlib import Path


def parse_demo(path: Path) -> dict:
    """Experimental placeholder for a future CS2 .dem parser integration."""
    return {
        "status": "not_implemented",
        "file": str(path),
        "message": "CSV/JSON import is the supported MVP path. demoparser2/awpy integration is intentionally optional.",
    }
