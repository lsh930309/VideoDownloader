import json
import os
from pathlib import Path

class Config:
    DEFAULT_CONFIG = {
        "download_path": str(Path.home() / "Downloads"),
        "ffmpeg_path": "",  # Empty means system path or bundled
        "default_quality": "Best", # Best, 2160p, 1440p, 1080p, 720p, 480p, 360p
        "output_format": "mp4", # mp4, mkv (최종 출력 포맷)
        "keep_original": False,

        # 성능 옵션
        "concurrent_fragments": 8,  # 동시 다운로드 프래그먼트 수 (자동 설정됨)
        "speed_limit_mbps": 0,  # 속도 제한 (0 = 무제한, Mbps)

        # 네트워크 벤치마크 결과
        "benchmark_completed": False,  # 벤치마크 완료 여부
        "benchmark_optimal_workers": None,  # 벤치마크로 찾은 최적 워커 수
        "benchmark_min_size_per_worker": 100,  # 벤치마크로 찾은 워커당 최소 크기 (MB)

        # 쿠키 인증 설정 (YouTube Premium, 봇 검증 우회 등)
        "cookies_enabled": False,  # 쿠키 사용 여부
        "cookies_from_browser": "",  # 브라우저 이름 (chrome, firefox, edge, brave 등) - 비어있으면 비활성화
        "cookies_file_path": "",  # 쿠키 파일 경로 (Netscape 형식) - 비어있으면 비활성화

        # 아래 옵션들은 하위 호환성을 위해 유지하지만 yt-dlp 자동 최적화에 맡김
        "chunk_size_mb": 10,  # (사용 안 함 - yt-dlp 자동 조절)
        "buffer_size_mb": 16,  # (사용 안 함 - yt-dlp 자동 조절)
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
        self._apply_auto_settings_if_first_run()

    def load_config(self):
        if self.CONFIG_FILE.exists():
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    return {**self.DEFAULT_CONFIG, **json.load(f)}
            except Exception:
                return self.DEFAULT_CONFIG
        return self.DEFAULT_CONFIG

    def _apply_auto_settings_if_first_run(self):
        """최초 실행 시 CPU 기반 자동 설정 적용"""
        is_first_run = not self.CONFIG_FILE.exists()

        if is_first_run:
            try:
                from .auto_config import AutoConfig
                concurrent_fragments = AutoConfig.get_optimal_concurrent_fragments()

                self.config["concurrent_fragments"] = concurrent_fragments
                self.save_config()
                print(f"[Config] 자동 설정 적용됨: concurrent_fragments={concurrent_fragments}")
            except Exception as e:
                print(f"[Config] 자동 설정 실패 (기본값 사용): {e}")

    def save_config(self):
        with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=4)

    def get(self, key):
        return self.config.get(key, self.DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

config = Config()
