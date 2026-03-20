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

    async def process_upload(self, file_bytes: bytes, filename: str) -> str:
        ext = os.path.splitext(filename)[1] or ".mp4"
        path = os.path.join(settings.temp_dir, f"{_temp_id()}{ext}")
        with open(path, "wb") as f:
            f.write(file_bytes)
        return path

    async def process_url(self, url: str) -> tuple[str, dict]:
        """Returns (local_file_path, metadata)."""
        if self._is_streaming_url(url):
            return await self._download_with_ytdlp(url)
        elif self._is_direct_video_url(url):
            return await self._download_direct(url), {}
        else:
            # Try yt-dlp as fallback (supports many sites)
            return await self._download_with_ytdlp(url)

    def _is_streaming_url(self, url: str) -> bool:
        parsed = urlparse(url)
        return any(p in parsed.netloc for p in STREAMING_PLATFORMS)

    def _is_direct_video_url(self, url: str) -> bool:
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in [".mp4", ".mov", ".avi", ".webm", ".mkv"])

    async def _download_with_ytdlp(self, url: str) -> tuple[str, dict]:
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
                    "source_url": url,
                }
        return output_path, meta

    async def _download_direct(self, url: str) -> str:
        output_path = os.path.join(settings.temp_dir, f"{_temp_id()}.mp4")
        async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
        return output_path


def _temp_id() -> str:
    return tempfile.mktemp(dir="", prefix="vid_").replace("/", "")


video_input_router = VideoInputRouter()
