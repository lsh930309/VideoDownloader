"""
yt-dlp 플러그인 설치 및 관리 모듈

Chrome 쿠키 잠금 문제 해결을 위한 ChromeCookieUnlock 플러그인 자동 설치
"""
import os
import sys
import subprocess
from pathlib import Path
from .config import Config


class YtDlpPluginInstaller:
    """
    yt-dlp 플러그인 관리 클래스

    Chrome 114+ 버전의 쿠키 잠금 문제를 해결하기 위해
    yt-dlp-ChromeCookieUnlock 플러그인을 자동으로 설치합니다.
    """

    PLUGIN_NAME = "yt-dlp-ChromeCookieUnlock"
    PLUGIN_PACKAGE = "yt-dlp-ChromeCookieUnlock"

    @staticmethod
    def get_plugin_dir():
        """
        yt-dlp 플러그인 디렉토리 반환

        Windows: %APPDATA%/yt-dlp/plugins
        Linux/Mac: ~/.config/yt-dlp/plugins
        """
        if os.name == 'nt':  # Windows
            appdata = os.getenv('APPDATA')
            plugin_dir = Path(appdata) / "yt-dlp" / "plugins"
        else:  # Linux/Mac
            plugin_dir = Path.home() / ".config" / "yt-dlp" / "plugins"

        plugin_dir.mkdir(parents=True, exist_ok=True)
        return plugin_dir

    @staticmethod
    def check_plugin_installed():
        """
        ChromeCookieUnlock 플러그인 설치 여부 확인

        Returns:
            bool: 설치되어 있으면 True
        """
        try:
            # pip list로 확인
            result = subprocess.run(
                [sys.executable, "-m", "pip", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return YtDlpPluginInstaller.PLUGIN_NAME in result.stdout

            return False
        except Exception as e:
            print(f"[Plugin] 플러그인 확인 실패: {e}")
            return False

    @staticmethod
    def install_plugin(progress_callback=None):
        """
        ChromeCookieUnlock 플러그인 설치

        Args:
            progress_callback: 진행률 콜백 함수 (0-100)

        Returns:
            bool: 설치 성공 여부
        """
        print(f"[Plugin] {YtDlpPluginInstaller.PLUGIN_NAME} 설치 시작...")

        if progress_callback:
            progress_callback(10)

        try:
            # pip install 실행
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install",
                 YtDlpPluginInstaller.PLUGIN_PACKAGE],
                capture_output=True,
                text=True,
                timeout=120
            )

            if progress_callback:
                progress_callback(80)

            if result.returncode == 0:
                print(f"[Plugin] {YtDlpPluginInstaller.PLUGIN_NAME} 설치 완료")
                if progress_callback:
                    progress_callback(100)
                return True
            else:
                print(f"[Plugin] 설치 실패: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("[Plugin] 설치 타임아웃")
            return False
        except Exception as e:
            print(f"[Plugin] 설치 오류: {e}")
            return False

    @staticmethod
    def ensure_plugin(progress_callback=None):
        """
        플러그인 확인 및 자동 설치

        Args:
            progress_callback: 진행률 콜백 함수 (0-100)

        Returns:
            bool: 플러그인이 설치되어 있거나 설치 성공 시 True
        """
        if YtDlpPluginInstaller.check_plugin_installed():
            print(f"[Plugin] {YtDlpPluginInstaller.PLUGIN_NAME} 이미 설치됨")
            if progress_callback:
                progress_callback(100)
            return True

        print(f"[Plugin] {YtDlpPluginInstaller.PLUGIN_NAME} 미설치. 자동 설치 시작...")
        return YtDlpPluginInstaller.install_plugin(progress_callback)
