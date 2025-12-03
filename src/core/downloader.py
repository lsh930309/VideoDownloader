import yt_dlp
import os
from .config import config
from .ffmpeg_installer import FFmpegInstaller

class VideoDownloader:
    def __init__(self):
        self.cancel_requested = False
        self.ffmpeg_ensured = False

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

    def get_video_info(self, url):
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True, # Fast extraction
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return info
        except Exception as e:
            raise e

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

        # 파일 크기 확인하여 최적 워커 수 계산
        try:
            if status_callback:
                status_callback("영상 정보 확인 중...")

            # 영상 정보 추출 (파일 크기 확인용)
            info_opts = {
                'format': format_str,
                'quiet': True,
                'no_warnings': True,
            }
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # 파일 크기 추출 (bytes → MB)
                filesize = info.get('filesize') or info.get('filesize_approx') or 0
                filesize_mb = filesize / (1024 * 1024) if filesize > 0 else None

                if filesize_mb:
                    print(f"[Downloader] 예상 파일 크기: {filesize_mb:.1f}MB")
                else:
                    print(f"[Downloader] 파일 크기 확인 실패 - 기본값 사용")
        except Exception as e:
            print(f"[Downloader] 파일 크기 확인 중 오류: {e}")
            filesize_mb = None

        # 동적 워커 수 계산 (파일 크기 고려)
        from .auto_config import AutoConfig
        concurrent_fragments = AutoConfig.get_optimal_concurrent_fragments(filesize_mb)

        speed_limit_mbps = config.get("speed_limit_mbps")

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
