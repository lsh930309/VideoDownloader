import yt_dlp
import os
from .config import config, Config
from .ffmpeg_installer import FFmpegInstaller

class VideoDownloader:
    def __init__(self):
        self.cancel_requested = False
        self.ffmpeg_ensured = False

        # yt-dlp 작업 디렉토리를 %APPDATA%로 제한
        self.yt_dlp_cache_dir = Config.get_config_dir() / "yt-dlp-cache"
        self.yt_dlp_cache_dir.mkdir(parents=True, exist_ok=True)

        self.yt_dlp_temp_dir = Config.get_config_dir() / "temp"
        self.yt_dlp_temp_dir.mkdir(parents=True, exist_ok=True)

    def _build_format_selector(self, quality):
        """
        포맷 선택 로직 - 지정 화질의 최고 품질을 다운로드

        Args:
            quality: 화질 설정 (Best, 2160p, 1440p, 1080p, 720p, 480p, 360p)

        Returns:
            yt-dlp format selector 문자열
        """
        if quality == "Best":
            # 최고 화질 다운로드
            format_str = "bestvideo+bestaudio/best"
        else:
            # 지정 화질 이하의 최고 품질 다운로드
            height = quality.replace("p", "")
            format_str = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"

        print(f"[Downloader] 포맷 선택자: {format_str}")
        return format_str

    def _apply_cookie_settings(self, ydl_opts):
        """
        쿠키 설정을 yt-dlp 옵션에 적용

        YouTube Premium 기능 및 봇 검증 우회를 위해 사용
        """
        cookies_enabled = config.get("cookies_enabled")
        if not cookies_enabled:
            return

        # 방법 1: 브라우저에서 자동으로 쿠키 가져오기 (우선순위)
        cookies_from_browser = config.get("cookies_from_browser")
        if cookies_from_browser:
            ydl_opts['cookiesfrombrowser'] = (cookies_from_browser,)
            print(f"[Downloader] 쿠키 활성화: 브라우저 '{cookies_from_browser}'에서 가져오기")
            return

        # 방법 2: 쿠키 파일 직접 지정
        cookies_file = config.get("cookies_file_path")
        if cookies_file and os.path.exists(cookies_file):
            ydl_opts['cookiefile'] = cookies_file
            print(f"[Downloader] 쿠키 활성화: 파일 '{cookies_file}' 사용")
            return

        print("[Downloader] 쿠키 활성화되어 있으나 유효한 설정이 없습니다")

    def get_video_info(self, url):
        """
        영상 정보 추출
        모든 작업을 %APPDATA%/VideoDownloader 내부로 제한하여 권한 문제 방지
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,  # Full extraction for detailed info

            # 캐시 및 임시 파일 경로를 %APPDATA%로 제한
            'cachedir': str(self.yt_dlp_cache_dir),
            'paths': {'temp': str(self.yt_dlp_temp_dir)},

            # 네트워크 타임아웃 설정
            'socket_timeout': 30,
        }

        # 쿠키 설정 추가
        self._apply_cookie_settings(ydl_opts)

        try:
            print(f"[Downloader] 영상 정보 추출 시작...")
            print(f"[Downloader] 캐시 디렉토리: {self.yt_dlp_cache_dir}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                print(f"[Downloader] 영상 정보 추출 완료")
                return info
        except Exception as e:
            print(f"[ERROR] 영상 정보 추출 실패: {e}")
            raise e

    def _print_video_info(self, info, quality, output_format, status_callback=None):
        """영상 정보를 로그로 출력"""
        print("\n" + "="*60)
        print("영상 정보")
        print("="*60)

        # 제목
        title = info.get('title', 'N/A')
        print(f"제목: {title}")
        if status_callback:
            status_callback(f"영상 제목: {title}")

        # 업로더
        uploader = info.get('uploader', 'N/A')
        print(f"업로더: {uploader}")

        # 영상 길이 (초 → 시:분:초)
        duration = info.get('duration', 0)
        if duration:
            hours = int(duration // 3600)
            minutes = int((duration % 3600) // 60)
            seconds = int(duration % 60)
            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours > 0 else f"{minutes:02d}:{seconds:02d}"
            print(f"영상 길이: {duration_str}")
        else:
            print(f"영상 길이: N/A")

        # 선택된 해상도
        print(f"요청 화질: {quality}")

        # 다운로드될 포맷 찾기 (실제로 다운로드될 형식)
        formats = info.get('formats', [])
        if formats:
            # 최고 화질 비디오 포맷 찾기
            video_formats = [f for f in formats if f.get('vcodec') != 'none']
            if video_formats:
                best_video = max(video_formats, key=lambda x: x.get('height', 0) or 0)
                video_format = best_video.get('ext', 'N/A')
                video_height = best_video.get('height', 'N/A')
                video_fps = best_video.get('fps', 'N/A')
                video_vcodec = best_video.get('vcodec', 'N/A')

                print(f"다운로드 포맷: {video_format} ({video_vcodec})")
                print(f"실제 해상도: {video_height}p @ {video_fps}fps")

        # 최종 출력 포맷
        print(f"최종 출력 포맷: {output_format}")

        # 예상 파일 크기
        filesize = info.get('filesize') or info.get('filesize_approx')
        if filesize:
            filesize_mb = filesize / (1024 * 1024)
            filesize_gb = filesize_mb / 1024
            if filesize_gb >= 1:
                print(f"예상 용량: {filesize_gb:.2f} GB")
            else:
                print(f"예상 용량: {filesize_mb:.1f} MB")
        else:
            print(f"예상 용량: 확인 불가")

        # 조회수, 좋아요 등 추가 정보
        view_count = info.get('view_count')
        if view_count:
            print(f"조회수: {view_count:,}")

        like_count = info.get('like_count')
        if like_count:
            print(f"좋아요: {like_count:,}")

        upload_date = info.get('upload_date')
        if upload_date:
            # YYYYMMDD → YYYY-MM-DD
            formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
            print(f"업로드 날짜: {formatted_date}")

        print("="*60 + "\n")

        if status_callback:
            status_callback("영상 정보 확인 완료")

    def download(self, url, progress_callback=None, status_callback=None):
        self.cancel_requested = False

        # FFmpeg 자동 설치 확인 (최초 1회만)
        if not self.ffmpeg_ensured:
            try:
                if status_callback:
                    status_callback("FFmpeg 확인 중...")

                ffmpeg_path = FFmpegInstaller.ensure_ffmpeg(
                    progress_callback=lambda p: progress_callback(p * 0.1) if progress_callback else None
                )

                if status_callback:
                    status_callback("FFmpeg 확인 완료")

                self.ffmpeg_ensured = True
            except Exception as e:
                print(f"[FFmpeg] 자동 설치 실패: {e}")
                if status_callback:
                    status_callback(f"FFmpeg 설치 실패: {e}")
                # FFmpeg 없이도 일부 다운로드는 가능하므로 계속 진행

        output_path = config.get("download_path")
        quality = config.get("default_quality")
        output_format = config.get("output_format") or config.get("preferred_format") or config.get("default_format") or "mp4"
        # ts는 더 이상 지원하지 않으므로 mp4로 변환
        if output_format == "ts":
            output_format = "mp4"
        ffmpeg_path = config.get("ffmpeg_path")

        print(f"[Downloader] URL: {url}")
        print(f"[Downloader] 출력 경로: {output_path}")
        print(f"[Downloader] 화질: {quality}, 출력 포맷: {output_format}")

        # 포맷 선택 로직 - 지정 화질의 최고 품질 다운로드
        format_str = self._build_format_selector(quality)

        # 영상 정보 추출 및 출력
        if status_callback:
            status_callback("영상 정보 확인 중...")

        try:
            info = self.get_video_info(url)
            self._print_video_info(info, quality, output_format, status_callback)
        except Exception as e:
            print(f"[Downloader] 영상 정보 확인 실패: {e}")
            if status_callback:
                status_callback(f"영상 정보 확인 실패 (다운로드는 계속 진행)")

        # 병렬 다운로드 설정 (벤치마크로 결정된 값 사용)
        concurrent_fragments = config.get("concurrent_fragments")

        speed_limit_mbps = config.get("speed_limit_mbps")

        print(f"[Downloader] 병렬 다운로드: {concurrent_fragments}개 워커")
        print(f"[Downloader] 참고: 청크 크기, 버퍼 등은 yt-dlp가 자동으로 최적화합니다")

        # 속도 제한 계산 (Mbps -> bytes/s)
        rate_limit = None if speed_limit_mbps == 0 else int(speed_limit_mbps * 1024 * 1024 / 8)
        if speed_limit_mbps > 0:
            print(f"[Downloader] 속도 제한: {speed_limit_mbps} Mbps")
        else:
            print(f"[Downloader] 속도 제한: 없음 (최대 속도)")

        ydl_opts = {
            'format': format_str,
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'merge_output_format': output_format,  # FFmpeg로 remux하여 출력 포맷 변환
            'progress_hooks': [lambda d: self._progress_hook(d, progress_callback, status_callback)],
            'quiet': True,
            'no_warnings': True,

            # 캐시 및 임시 파일 경로를 %APPDATA%로 제한 (권한 문제 방지)
            'cachedir': str(self.yt_dlp_cache_dir),
            'paths': {'temp': str(self.yt_dlp_temp_dir)},

            # 병렬 다운로드 설정 (CPU 기반 자동 설정)
            'concurrent_fragment_downloads': concurrent_fragments,

            # 재시도 설정
            'retries': 10,
            'fragment_retries': 10,

            # 네트워크 최적화 (yt-dlp 자동 조절)
            # - buffer_size: 자동 조절 (resize-buffer 기본 활성화)
            # - http_chunk_size: 자동 조절 (기본 disabled, 필요시 자동 활성화)
            'socket_timeout': 30,
            'source_address': None,
            'prefer_insecure': False,

            # 다운로드 속도 제한
            'ratelimit': rate_limit,
            'throttledratelimit': None,
        }

        if ffmpeg_path:
            ydl_opts['ffmpeg_location'] = ffmpeg_path

        # 쿠키 설정 추가
        self._apply_cookie_settings(ydl_opts)

        print(f"[Downloader] yt-dlp 임시 파일 디렉토리: {self.yt_dlp_temp_dir}")

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            if status_callback:
                status_callback(f"Error: {str(e)}")
            raise e

    def _progress_hook(self, d, progress_callback, status_callback):
        if self.cancel_requested:
            raise yt_dlp.utils.DownloadError("사용자에 의해 다운로드가 취소되었습니다.")

        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%').replace('%', '')
            try:
                percent = float(p)
            except:
                percent = 0
            
            if progress_callback:
                progress_callback(percent)
            
            if status_callback:
                speed = d.get('_speed_str', 'N/A')
                eta = d.get('_eta_str', 'N/A')
                status_callback(f"다운로드 중: {percent}% | 속도: {speed} | 남은 시간: {eta}")
        
        elif d['status'] == 'finished':
            if progress_callback:
                progress_callback(100)
            if status_callback:
                status_callback("다운로드 완료. 처리 중...")

    def cancel(self):
        self.cancel_requested = True
