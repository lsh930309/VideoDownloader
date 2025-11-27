import yt_dlp
import os
from .config import config

class VideoDownloader:
    def __init__(self):
        self.cancel_requested = False

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
        
        output_path = config.get("download_path")
        quality = config.get("default_quality")
        video_format = config.get("default_format")
        ffmpeg_path = config.get("ffmpeg_path")

        # Format selection logic
        if quality == "Best":
            format_str = f"bestvideo+bestaudio/best"
        else:
            # Map quality string (e.g., "1080p") to height
            height = quality.replace("p", "")
            format_str = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"

        ydl_opts = {
            'format': format_str,
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'merge_output_format': video_format,
            'progress_hooks': [lambda d: self._progress_hook(d, progress_callback, status_callback)],
            # 'logger': MyLogger(), # TODO: Implement logger if needed
            'quiet': True,
            'no_warnings': True,
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
