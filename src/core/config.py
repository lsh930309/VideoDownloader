import json
import os
from pathlib import Path

class Config:
    DEFAULT_CONFIG = {
        "download_path": str(Path.home() / "Downloads"),
        "ffmpeg_path": "",  # Empty means system path or bundled
        "default_quality": "Best", # Best, 2160p, 1440p, 1080p, 720p, 480p, 360p
        "preferred_format": "mp4", # mp4, mkv, ts (선호 포맷)
        "format_priority": "quality", # quality: 품질 우선, format: 포맷 우선
        "keep_original": False,

        # 성능 옵션
        "concurrent_fragments": 16,  # 동시 다운로드 프래그먼트 수 (1-32, 기본 16)
        "chunk_size_mb": 10,  # 청크 크기 (MB)
        "buffer_size_mb": 16,  # 버퍼 크기 (MB) - 사용 안 함
        "speed_limit_mbps": 0,  # 속도 제한 (0 = 무제한, Mbps)
    }

    # %APPDATA%에 설정 파일 저장
    @staticmethod
    def get_config_dir():
        """설정 디렉토리 경로 반환 (%APPDATA%/VideoDownloader)"""
        if os.name == 'nt':  # Windows
            appdata = os.getenv('APPDATA')
            config_dir = Path(appdata) / "VideoDownloader"
        else:  # Linux/Mac
            config_dir = Path.home() / ".config" / "VideoDownloader"

        # 디렉토리가 없으면 생성
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    CONFIG_FILE = get_config_dir.__func__() / "config.json"

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
