"""Configuration management for Tiny Wi-Fi Analyzer."""
import json
import os
from dataclasses import asdict, dataclass
from typing import Optional


@dataclass
class Config:
    """Application configuration with persistent storage."""

    scan_interval_ms: int = 3000
    update_interval_s: float = 0.3
    debug: bool = False
    log_level: str = "WARNING"
    dark_mode: str = "auto"  # "auto", "light", or "dark"
    show_24ghz: bool = True
    show_5ghz: bool = True
    show_6ghz: bool = True
    layout: str = "stacked"  # "stacked" or "side-by-side"
    window_width: int = 1200
    window_height: int = 800

    @classmethod
    def load(cls, path: Optional[str] = None) -> "Config":
        """Load configuration from a JSON file.

        Args:
            path: Path to configuration file. If None or file doesn't exist,
                  returns default configuration.

        Returns:
            Config instance with loaded or default values
        """
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return cls(**data)
        return cls()

    def save(self, path: str) -> None:
        """Save configuration to a JSON file.

        Args:
            path: Path to save configuration file
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
