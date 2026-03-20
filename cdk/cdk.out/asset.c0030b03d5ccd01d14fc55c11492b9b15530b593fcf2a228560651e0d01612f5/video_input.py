import os
import tempfile
from urllib.parse import urlparse

import httpx
import yt_dlp

from config import settings

STREAMING_PLATFORMS = ["youtube.com", "youtu.be", "vimeo.com", "tiktok.com", "instagram.com"]


class VideoInputRouter:
    def __init__(self):
        os.makedirs(settings.temp_dir, exist_ok=True)

    def save_upload(self, file_bytes: bytes, filename: str) -> str:
        ext = os.path.splitext(filename)[1] or ".mp4"
        path = os.path.join(settings.temp_dir, f"{_temp_id()}{ext}")
        with open(path, "wb") as f:
            f.write(file_bytes)
        return path

    def download_url(self, url: str) -> tuple[str, dict]:
        if self._is_direct_video_url(url):
            return self._download_direct(url), {}
        return self._download_with_ytdlp(url)

    def _is_direct_video_url(self, url: str) -> bool:
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in [".mp4", ".mov", ".avi", ".webm", ".mkv"])

    def _download_with_ytdlp(self, url: str) -> tuple[str, dict]:
        output_path = os.path.join(settings.temp_dir, f"{_temp_id()}.mp4")
        ydl_opts = {
            "format": f"best[height<={settings.max_video_resolution}][ext=mp4]/best[height<={settings.max_video_resolution}]/best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
            "match_filter": yt_dlp.utils.match_filter_func(
                f"duration < {settings.max_video_duration_sec}"
            ),
        }
        meta = {}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                meta = {
                    "title": info.get("title", ""),
                    "duration": info.get("duration", 0),
                    "thumbnail": info.get("thumbnail", ""),
                }
        return output_path, meta

    def _download_direct(self, url: str) -> str:
        output_path = os.path.join(settings.temp_dir, f"{_temp_id()}.mp4")
        with httpx.Client(follow_redirects=True, timeout=120) as client:
            resp = client.get(url)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
        return output_path


def _temp_id() -> str:
    return next(tempfile.NamedTemporaryFile(dir="", prefix="vid_", delete=True)).name.split("/")[-1]


# simpler approach
def _temp_id() -> str:
    import uuid
    return f"vid_{uuid.uuid4().hex[:12]}"


video_input = VideoInputRouter()
