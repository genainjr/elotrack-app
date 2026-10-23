"""Quick preview stream fetcher for the built-in trimmer player."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yt_dlp

from .validator import EnvironmentValidator, URLValidator

logger = logging.getLogger(__name__)


class PreviewFetcher:
    """Downloads a lightweight audio preview to a cache folder for instant scrubbing."""

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self.cache_dir = cache_dir or Path.home() / ".cache" / "elotrack" / "previews"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_preview(self, url: str) -> Tuple[Path, float, str, str]:
        """Fetches or retrieves cached preview audio file.

        Returns:
            Tuple of (audio_file_path, duration_seconds, title, artist)
        """
        clean_url = URLValidator.clean_video_url(url)
        video_id = URLValidator.extract_video_id(clean_url) or "unknown"

        meta_json_file = self.cache_dir / f"preview_{video_id}.json"

        # Check existing cached file
        for existing in self.cache_dir.glob(f"preview_{video_id}.*"):
            if existing.is_file() and existing.suffix.lower() in (".mp3", ".m4a", ".webm", ".wav") and existing.stat().st_size > 1000:
                logger.info("Prévia encontrada em cache: %s", existing)
                if meta_json_file.exists():
                    try:
                        saved_meta = json.loads(meta_json_file.read_text(encoding="utf-8"))
                        t = saved_meta.get("title")
                        if t and t != "Áudio":
                            return existing, float(saved_meta.get("duration", 0.0)), t, saved_meta.get("artist", "")
                    except Exception:
                        pass
                duration, title, artist = self._extract_metadata(clean_url)
                return existing, duration, title, artist

        ffmpeg_path = EnvironmentValidator.get_ffmpeg_path()
        out_template = str(self.cache_dir / f"preview_{video_id}.%(ext)s")

        ydl_opts: Dict[str, Any] = {
            "format": "ba/bestaudio/best",
            "outtmpl": out_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": ["android", "ios", "web"]}},
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "128",  # 128 kbps is ultra-fast for previewing
                }
            ],
        }

        if ffmpeg_path:
            ydl_opts["ffmpeg_location"] = str(ffmpeg_path.parent if ffmpeg_path.is_file() else ffmpeg_path)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("Baixando prévia ultrarrápida para o player...")
            info = ydl.extract_info(clean_url, download=True) or {}
            title = info.get("title") or "Áudio"
            artist = info.get("artist") or info.get("uploader") or ""
            duration = float(info.get("duration") or 0.0)

            # Cache metadata json
            try:
                meta_json_file.write_text(
                    json.dumps({"title": title, "artist": artist, "duration": duration}, ensure_ascii=False),
                    encoding="utf-8",
                )
            except Exception:
                pass

            # Resolve expected mp3
            expected_mp3 = self.cache_dir / f"preview_{video_id}.mp3"
            if expected_mp3.exists():
                return expected_mp3, duration, title, artist

            # Fallback scan
            for candidate in self.cache_dir.glob(f"preview_{video_id}.*"):
                if candidate.is_file() and candidate.suffix.lower() != ".json":
                    return candidate, duration, title, artist

            raise RuntimeError("Não foi possível gerar a prévia de áudio.")

    def _extract_metadata(self, url: str) -> Tuple[float, str, str]:
        """Fetches basic metadata without redownloading."""
        try:
            ydl_opts = {
                "quiet": True,
                "skip_download": True,
                "extractor_args": {"youtube": {"player_client": ["android", "ios", "web"]}},
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False) or {}
                t = info.get("title") or "Áudio"
                return (
                    float(info.get("duration") or 0.0),
                    t,
                    info.get("artist") or info.get("uploader") or "",
                )
        except Exception:
            return 0.0, "Áudio", ""
