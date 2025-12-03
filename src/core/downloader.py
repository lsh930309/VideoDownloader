import yt_dlp
import os
from .config import config
from .ffmpeg_installer import FFmpegInstaller

class VideoDownloader:
    def __init__(self):
        self.cancel_requested = False
        self.ffmpeg_ensured = False

    def _build_format_selector(self, quality, preferred_format, format_priority):
        """
        스마트 포맷 선택 로직

        Args:
            quality: 화질 설정 (Best, 2160p, 1440p, 1080p, 720p, 480p, 360p)
            preferred_format: 선호 포맷 (mp4, mkv, ts)
            format_priority: 우선순위 (quality: 품질 우선, format: 포맷 우선)

        Returns:
            yt-dlp format selector 문자열
        """
        # 포맷별 확장자 매핑
        format_ext_map = {
            'mp4': 'mp4',
            'mkv': 'mkv',
            'ts': 'ts'
        }

        preferred_ext = format_ext_map.get(preferred_format, 'mp4')

        if quality == "Best":
            height_filter = ""
        else:
            height = quality.replace("p", "")
            height_filter = f"[height<={height}]"

        if format_priority == "quality":
            # 품질 우선: 지정 화질을 최우선으로, 그 다음 선호 포맷
            # 예: 1440p webm > 1440p mp4 > 1080p mp4
            if quality == "Best":
                format_str = f"bestvideo[ext={preferred_ext}]+bestaudio/bestvideo+bestaudio/best"
            else:
                # 1. 지정 화질의 최고 품질 (포맷 무관)
                # 2. 더 낮은 화질 + 선호 포맷
                # 3. 최선의 선택
                format_str = f"bestvideo{height_filter}+bestaudio/bestvideo[ext={preferred_ext}]+bestaudio/best"
        else:
            # 포맷 우선: 선호 포맷을 최대한 유지 (품질이 낮아져도)
            # 예: 1080p mp4 > 1440p webm
            if quality == "Best":
                format_str = f"bestvideo[ext={preferred_ext}]+bestaudio/bestvideo+bestaudio/best"
            else:
                # 1. 지정 화질 + 선호 포맷
                # 2. 더 낮은 화질 + 선호 포맷
                # 3. 지정 화질 + 다른 포맷
                # 4. 최선의 선택
                format_str = f"bestvideo{height_filter}[ext={preferred_ext}]+bestaudio/bestvideo[ext={preferred_ext}]+bestaudio/bestvideo{height_filter}+bestaudio/best"

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
        preferred_format = config.get("preferred_format") or config.get("default_format") or "mp4"
        format_priority = config.get("format_priority") or "quality"
        ffmpeg_path = config.get("ffmpeg_path")

        print(f"[Downloader] URL: {url}")
        print(f"[Downloader] 출력 경로: {output_path}")
        print(f"[Downloader] 화질: {quality}, 선호 포맷: {preferred_format}, 우선순위: {format_priority}")

        # 스마트 포맷 선택 로직
        format_str = self._build_format_selector(quality, preferred_format, format_priority)

        # 성능 설정 값 가져오기
        concurrent_fragments = config.get("concurrent_fragments")
        chunk_size_mb = config.get("chunk_size_mb")
        buffer_size_mb = config.get("buffer_size_mb")
        speed_limit_mbps = config.get("speed_limit_mbps")

        print(f"[Downloader] 성능 설정: {concurrent_fragments}개 동시 다운로드, 청크 {chunk_size_mb}MB, 버퍼 {buffer_size_mb}MB")

        # 속도 제한 계산 (Mbps -> bytes/s)
        rate_limit = None if speed_limit_mbps == 0 else int(speed_limit_mbps * 1024 * 1024 / 8)
        if speed_limit_mbps > 0:
            print(f"[Downloader] 속도 제한: {speed_limit_mbps} Mbps")
        else:
            print(f"[Downloader] 속도 제한: 없음 (최대 속도)")

        ydl_opts = {
            'format': format_str,
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'merge_output_format': preferred_format,
            'progress_hooks': [lambda d: self._progress_hook(d, progress_callback, status_callback)],
            'quiet': True,
            'no_warnings': True,

            # 성능 최적화 옵션 (설정 값 사용)
            'concurrent_fragment_downloads': concurrent_fragments,
            'http_chunk_size': chunk_size_mb * 1024 * 1024,
            'retries': 10,
            'fragment_retries': 10,
            # buffersize는 yt-dlp 자동 조절에 맡김 (속도 저하 방지)

            # 네트워크 최적화
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
