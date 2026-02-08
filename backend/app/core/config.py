"""Configuration management for LMU Telemetry Analyzer."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Common LMU telemetry paths to check
COMMON_TELEMETRY_PATHS = [
    Path.home() / "Documents" / "My Games" / "Le Mans Ultimate" / "UserData" / "Telemetry",
    Path.home() / "Documents" / "Le Mans Ultimate" / "UserData" / "Telemetry",
]

# Path to store user config (project root - up one more level from backend/)
CONFIG_FILE = Path(__file__).parent.parent.parent.parent / "config.yaml"


def _get_username() -> str:
    """Get current username for path templates."""
    return os.environ.get("USERNAME") or os.environ.get("USER") or ""


def _expand_common_paths() -> list[Path]:
    """Generate common telemetry paths."""
    return list(COMMON_TELEMETRY_PATHS)


def find_telemetry_directory() -> Path | None:
    """Search for LMU telemetry directory in common locations."""
    for path in _expand_common_paths():
        if path.exists() and path.is_dir():
            logger.info(f"Found telemetry directory: {path}")
            return path
    return None


def load_config() -> dict[str, Any]:
    """Load configuration from config.yaml."""
    if not CONFIG_FILE.exists():
        return {}

    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to config.yaml."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        logger.error(f"Error saving config: {e}")


def get_telemetry_path() -> Path:
    """Get telemetry directory path, searching if not configured."""
    config = load_config()

    # Check if already configured
    if config.get("telemetry_path"):
        path = Path(config["telemetry_path"])
        if path.exists():
            return path
        logger.warning(f"Configured telemetry path does not exist: {path}")

    # Search common locations
    found = find_telemetry_directory()
    if found:
        # Save for future use
        config["telemetry_path"] = str(found)
        save_config(config)
        return found

    # Could not find - raise error with instructions
    searched = "\n  - ".join([str(p) for p in _expand_common_paths()])
    raise FileNotFoundError(
        f"Could not find LMU telemetry directory. Searched:\n  - {searched}\n\n"
        f"Please specify the path in {CONFIG_FILE} or set telemetry_path in config.yaml"
    )


def get_cache_dir() -> Path:
    """Get cache directory for derived data."""
    config = load_config()
    cache_path = Path(config.get("cache_dir", "./cache"))
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path
