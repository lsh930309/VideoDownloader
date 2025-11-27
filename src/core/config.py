import json
import os
from pathlib import Path

class Config:
    DEFAULT_CONFIG = {
        "download_path": str(Path.home() / "Downloads"),
        "ffmpeg_path": "",  # Empty means system path or bundled
        "default_quality": "Best", # Best, 2160p, 1440p, 1080p, 720p, 480p, 360p
        "default_format": "mp4", # mp4, mkv, ts
        "keep_original": False,
    }

    CONFIG_FILE = Path("config.json")

    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    return {**self.DEFAULT_CONFIG, **json.load(f)}
            except Exception:
                return self.DEFAULT_CONFIG
        return self.DEFAULT_CONFIG

    def save_config(self):
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def get(self, key):
        return self.config.get(key, self.DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

config = Config()
