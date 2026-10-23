"""YouTube search service for Elo Track."""

import logging
from dataclasses import dataclass
from typing import List
import yt_dlp

logger = logging.getLogger("elotrack.search")


@dataclass
class SearchResult:
    """Represents a single YouTube search result."""
    video_id: str
    title: str
    uploader: str
    duration_seconds: int
    duration_formatted: str
    thumbnail_url: str
    url: str


class YouTubeSearchService:
    """Performs fast YouTube searches using yt-dlp flat extraction without external APIs."""

    def __init__(self) -> None:
        self._ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
            "skip_download": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios", "web"],
                }
            },
        }

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Searches YouTube and returns up to max_results items."""
        query = query.strip()
        if not query:
            return []

        search_query = f"ytsearch{max_results}:{query}"
        results: List[SearchResult] = []

        try:
            with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                if not info or "entries" not in info:
                    return []

                for entry in info.get("entries", []):
                    if not entry:
                        continue
                    v_id = entry.get("id") or ""
                    title = entry.get("title") or "Sem título"
                    uploader = entry.get("uploader") or entry.get("channel") or "Artista Desconhecido"
                    duration_s = int(entry.get("duration") or 0)

                    m = duration_s // 60
                    s = duration_s % 60
                    dur_fmt = f"{m:02d}:{s:02d}"

                    thumb_url = f"https://i.ytimg.com/vi/{v_id}/mqdefault.jpg" if v_id else ""
                    if entry.get("thumbnails") and isinstance(entry["thumbnails"], list) and len(entry["thumbnails"]) > 0:
                        thumb_url = entry["thumbnails"][0].get("url") or thumb_url

                    url = entry.get("url") or ""
                    if not url.startswith("http") and v_id:
                        url = f"https://www.youtube.com/watch?v={v_id}"

                    results.append(
                        SearchResult(
                            video_id=v_id,
                            title=title,
                            uploader=uploader,
                            duration_seconds=duration_s,
                            duration_formatted=dur_fmt,
                            thumbnail_url=thumb_url,
                            url=url,
                        )
                    )
        except Exception as exc:
            logger.exception("Erro ao realizar busca no YouTube: %s", exc)

        return results
