"""
yt-dlp 플러그인 설치 및 관리 모듈

Chrome 쿠키 잠금 문제 해결을 위한 ChromeCookieUnlock 플러그인 설치
"""
import os
import sys
import subprocess
import zipfile
import requests
from pathlib import Path
from .config import Config


class YtDlpPluginInstaller:
    """
    yt-dlp 플러그인 관리 클래스

    Chrome 114+ 버전의 쿠키 잠금 문제를 해결하기 위해
    ChromeCookieUnlock 플러그인을 설치합니다.
    """

    PLUGIN_NAME = "ChromeCookieUnlock"
    GITHUB_REPO = "seproDev/yt-dlp-ChromeCookieUnlock"
    GITHUB_ZIP_URL = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip"

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
            plugin_dir = YtDlpPluginInstaller.get_plugin_dir()
            # yt_dlp_plugins 폴더 확인
            plugin_path = plugin_dir / "yt_dlp_plugins"
            if not plugin_path.exists():
                return False

            # postprocessor 폴더 및 chromecookieunlock.py 확인
            postprocessor_path = plugin_path / "postprocessor"
            if not postprocessor_path.exists():
                return False

            cookie_unlock_file = postprocessor_path / "chromecookieunlock.py"
            return cookie_unlock_file.exists()

        except Exception as e:
            print(f"[Plugin] 플러그인 확인 실패: {e}")
            return False

    @staticmethod
    def install_plugin(progress_callback=None):
        """
        ChromeCookieUnlock 플러그인 설치
        GitHub에서 직접 다운로드하여 plugins 폴더에 설치

        Args:
            progress_callback: 진행률 콜백 함수 (0-100)

        Returns:
            bool: 설치 성공 여부
        """
        print(f"[Plugin] {YtDlpPluginInstaller.PLUGIN_NAME} 설치 시작...")
        print(f"[Plugin] GitHub에서 다운로드: {YtDlpPluginInstaller.GITHUB_ZIP_URL}")

        plugin_dir = YtDlpPluginInstaller.get_plugin_dir()
        temp_zip = plugin_dir / "temp_plugin.zip"

        try:
            # 1. GitHub에서 ZIP 다운로드
            if progress_callback:
                progress_callback(10)

            print("[Plugin] 다운로드 중...")
            response = requests.get(YtDlpPluginInstaller.GITHUB_ZIP_URL, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(temp_zip, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            percent = 10 + int((downloaded / total_size) * 50)
                            progress_callback(percent)

            print(f"[Plugin] 다운로드 완료: {temp_zip}")

            # 2. ZIP 압축 해제
            if progress_callback:
                progress_callback(70)

            print("[Plugin] 압축 해제 중...")
            with zipfile.ZipFile(temp_zip, 'r') as zip_ref:
                # ZIP 내용 확인
                file_list = zip_ref.namelist()
                print(f"[Plugin] ZIP 파일 수: {len(file_list)}")

                # yt_dlp_plugins 폴더 찾기
                plugin_folder = None
                for file in file_list:
                    if 'yt_dlp_plugins/' in file:
                        plugin_folder = file.split('yt_dlp_plugins/')[0] + 'yt_dlp_plugins'
                        break

                if not plugin_folder:
                    raise Exception("ZIP 파일에서 yt_dlp_plugins 폴더를 찾을 수 없습니다")

                # yt_dlp_plugins 폴더 내용만 추출
                target_plugin_path = plugin_dir / "yt_dlp_plugins"
                target_plugin_path.mkdir(parents=True, exist_ok=True)

                for file in file_list:
                    if file.startswith(plugin_folder + '/'):
                        # 파일 경로에서 상위 폴더명 제거
                        relative_path = file[len(plugin_folder) + 1:]
                        if relative_path:  # 빈 경로 제외
                            target_file = target_plugin_path / relative_path
                            target_file.parent.mkdir(parents=True, exist_ok=True)

                            if not file.endswith('/'):  # 디렉토리가 아닌 파일만
                                with zip_ref.open(file) as source:
                                    with open(target_file, 'wb') as target:
                                        target.write(source.read())

            if progress_callback:
                progress_callback(90)

            # 3. 임시 파일 삭제
            temp_zip.unlink()

            # 4. 설치 확인
            if YtDlpPluginInstaller.check_plugin_installed():
                print(f"[Plugin] {YtDlpPluginInstaller.PLUGIN_NAME} 설치 완료")
                print(f"[Plugin] 설치 경로: {plugin_dir / 'yt_dlp_plugins'}")
                if progress_callback:
                    progress_callback(100)
                return True
            else:
                raise Exception("플러그인 파일이 제대로 설치되지 않았습니다")

        except requests.exceptions.RequestException as e:
            print(f"[Plugin] 다운로드 실패: {e}")
            if temp_zip.exists():
                temp_zip.unlink()
            return False
        except Exception as e:
            print(f"[Plugin] 설치 오류: {e}")
            if temp_zip.exists():
                temp_zip.unlink()
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
