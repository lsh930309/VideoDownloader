import os
import sys
import subprocess
import shutil
import zipfile
import tarfile
import platform
import requests
from pathlib import Path
from .config import Config

class FFmpegInstaller:
    """
    FFmpeg 자동 설치 및 관리 클래스
    - ffmpeg가 없을 경우 자동으로 다운로드
    - 앱 데이터 디렉토리에 설치
    - config에 경로 자동 저장
    - Windows, Linux, macOS 지원
    """

    # 플랫폼별 FFmpeg 다운로드 URL
    FFMPEG_WINDOWS_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
    FFMPEG_LINUX_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz"
    FFMPEG_MACOS_URL = "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"

    @staticmethod
    def get_ffmpeg_dir():
        """FFmpeg 설치 디렉토리 반환 (%APPDATA%/VideoDownloader/ffmpeg)"""
        ffmpeg_dir = Config.get_config_dir() / "ffmpeg"
        ffmpeg_dir.mkdir(parents=True, exist_ok=True)
        return ffmpeg_dir

    @staticmethod
    def check_ffmpeg():
        """
        ffmpeg 설치 여부 확인
        Returns:
            str: ffmpeg 실행 파일 경로 (없으면 None)
        """
        # 1. config에 저장된 경로 확인
        from .config import config
        ffmpeg_path = config.get("ffmpeg_path")
        if ffmpeg_path and os.path.isfile(ffmpeg_path):
            try:
                result = subprocess.run([ffmpeg_path, "-version"],
                                      capture_output=True,
                                      timeout=5)
                if result.returncode == 0:
                    print(f"[FFmpeg] config 경로에서 발견: {ffmpeg_path}")
                    return ffmpeg_path
            except Exception:
                pass

        # 2. 시스템 PATH에서 확인
        system_ffmpeg = shutil.which("ffmpeg")
        if system_ffmpeg:
            print(f"[FFmpeg] 시스템 PATH에서 발견: {system_ffmpeg}")
            return system_ffmpeg

        # 3. 앱 데이터 디렉토리의 설치된 ffmpeg 확인
        system = platform.system()
        if system == "Windows":
            local_ffmpeg = FFmpegInstaller.get_ffmpeg_dir() / "bin" / "ffmpeg.exe"
        else:
            local_ffmpeg = FFmpegInstaller.get_ffmpeg_dir() / "bin" / "ffmpeg"

        if local_ffmpeg.exists():
            try:
                result = subprocess.run([str(local_ffmpeg), "-version"],
                                      capture_output=True,
                                      timeout=5)
                if result.returncode == 0:
                    print(f"[FFmpeg] 로컬 설치본 발견: {local_ffmpeg}")
                    return str(local_ffmpeg)
            except Exception:
                pass

        print("[FFmpeg] 설치되지 않음")
        return None

    @staticmethod
    def get_download_url():
        """현재 플랫폼에 맞는 FFmpeg 다운로드 URL 반환"""
        system = platform.system()
        if system == "Windows":
            return FFmpegInstaller.FFMPEG_WINDOWS_URL
        elif system == "Linux":
            return FFmpegInstaller.FFMPEG_LINUX_URL
        elif system == "Darwin":  # macOS
            return FFmpegInstaller.FFMPEG_MACOS_URL
        else:
            raise Exception(f"지원하지 않는 운영체제: {system}")

    @staticmethod
    def download_ffmpeg(progress_callback=None):
        """
        FFmpeg 다운로드 및 설치
        Args:
            progress_callback: 진행률 콜백 함수 (0-100)
        Returns:
            str: 설치된 ffmpeg 실행 파일 경로
        """
        print("[FFmpeg] 다운로드 시작...")

        ffmpeg_dir = FFmpegInstaller.get_ffmpeg_dir()
        download_url = FFmpegInstaller.get_download_url()

        # 파일 확장자 결정
        if download_url.endswith('.zip'):
            archive_path = ffmpeg_dir / "ffmpeg.zip"
        elif download_url.endswith('.tar.xz'):
            archive_path = ffmpeg_dir / "ffmpeg.tar.xz"
        else:
            archive_path = ffmpeg_dir / "ffmpeg_archive"

        try:
            # 다운로드
            response = requests.get(download_url, stream=True)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(archive_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            percent = int((downloaded / total_size) * 70)  # 다운로드는 70%까지
                            progress_callback(percent)

            print(f"[FFmpeg] 다운로드 완료: {archive_path}")

            # 압축 해제
            if progress_callback:
                progress_callback(75)

            print("[FFmpeg] 압축 해제 중...")

            if str(archive_path).endswith('.zip'):
                FFmpegInstaller._extract_zip(archive_path, ffmpeg_dir)
            elif str(archive_path).endswith('.tar.xz'):
                FFmpegInstaller._extract_tar(archive_path, ffmpeg_dir)

            if progress_callback:
                progress_callback(90)

            # 다운로드한 압축 파일 삭제
            archive_path.unlink()

            # 실행 파일 경로 확인
            system = platform.system()
            if system == "Windows":
                ffmpeg_exe = ffmpeg_dir / "bin" / "ffmpeg.exe"
            else:
                ffmpeg_exe = ffmpeg_dir / "bin" / "ffmpeg"
                # Linux/macOS에서 실행 권한 부여
                if ffmpeg_exe.exists():
                    os.chmod(ffmpeg_exe, 0o755)

            if not ffmpeg_exe.exists():
                raise Exception("FFmpeg 실행 파일을 찾을 수 없습니다")

            print(f"[FFmpeg] 설치 완료: {ffmpeg_exe}")

            # config에 경로 저장
            from .config import config
            config.set("ffmpeg_path", str(ffmpeg_exe))

            if progress_callback:
                progress_callback(100)

            return str(ffmpeg_exe)

        except Exception as e:
            print(f"[FFmpeg] 설치 실패: {e}")
            # 실패 시 정리
            if archive_path.exists():
                archive_path.unlink()
            raise e

    @staticmethod
    def _extract_zip(zip_path, target_dir):
        """ZIP 파일 압축 해제"""
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # 압축 파일 내부 구조 확인
            # ffmpeg-master-latest-win64-gpl/bin/ffmpeg.exe 형태
            for member in zip_ref.namelist():
                if 'bin/' in member:
                    # bin 디렉토리 내용만 추출
                    filename = os.path.basename(member)
                    if filename:
                        target_path = target_dir / "bin" / filename
                        target_path.parent.mkdir(parents=True, exist_ok=True)

                        with zip_ref.open(member) as source:
                            with open(target_path, 'wb') as target:
                                shutil.copyfileobj(source, target)

    @staticmethod
    def _extract_tar(tar_path, target_dir):
        """TAR.XZ 파일 압축 해제"""
        with tarfile.open(tar_path, 'r:xz') as tar_ref:
            # ffmpeg-master-latest-linux64-gpl/bin/ffmpeg 형태
            for member in tar_ref.getmembers():
                if 'bin/' in member.name:
                    filename = os.path.basename(member.name)
                    if filename:
                        target_path = target_dir / "bin" / filename
                        target_path.parent.mkdir(parents=True, exist_ok=True)

                        source = tar_ref.extractfile(member)
                        if source:
                            with open(target_path, 'wb') as target:
                                shutil.copyfileobj(source, target)

    @staticmethod
    def ensure_ffmpeg(progress_callback=None):
        """
        FFmpeg 설치 확인 및 자동 설치
        - ffmpeg가 없으면 자동으로 다운로드 및 설치
        - 설치된 경로를 config에 저장

        Args:
            progress_callback: 진행률 콜백 함수 (0-100)
        Returns:
            str: ffmpeg 실행 파일 경로
        """
        ffmpeg_path = FFmpegInstaller.check_ffmpeg()

        if ffmpeg_path:
            return ffmpeg_path

        # ffmpeg가 없으면 자동 설치
        print("[FFmpeg] 설치되지 않음. 자동 설치 시작...")
        return FFmpegInstaller.download_ffmpeg(progress_callback)
