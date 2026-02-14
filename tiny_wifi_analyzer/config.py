import json
import os
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Config:
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
        if path and os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                return cls(**data)
        return cls()

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)
