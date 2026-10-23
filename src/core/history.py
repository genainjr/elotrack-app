"""History management and persistence for downloaded audio tracks."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .interfaces import DownloadResult

logger = logging.getLogger(__name__)


@dataclass
class HistoryItem:
    """Record representing a successfully completed download."""

    id: str
    title: str
    artist: str
    format: str
    file_path: str
    file_size_bytes: int
    duration_seconds: Optional[float] = None
    downloaded_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    url: str = ""
    thumbnail_url: Optional[str] = None
    thumbnail_path: Optional[str] = None
    is_trim: bool = False
    time_range: Optional[str] = None

    @property
    def path_obj(self) -> Path:
        return Path(self.file_path)

    def get_cached_thumbnail_path(self) -> Optional[Path]:
        """Returns the local path of the cached thumbnail if available on disk."""
        if self.thumbnail_path:
            p = Path(self.thumbnail_path)
            if p.is_file():
                return p

        # Check default thumbnails directory
        thumb_dir = Path.home() / ".elotrack" / "thumbnails"
        for ext in (".jpg", ".png", ".webp", ".jpeg"):
            cand = thumb_dir / f"{self.id}{ext}"
            if cand.is_file():
                return cand
            # Also check stem of file_path
            if self.file_path:
                cand_stem = thumb_dir / f"{Path(self.file_path).stem}{ext}"
                if cand_stem.is_file():
                    return cand_stem
        return None

    @property
    def file_exists(self) -> bool:
        try:
            return self.path_obj.is_file()
        except OSError:
            return False

    @property
    def formatted_size(self) -> str:
        mb = self.file_size_bytes / (1024 * 1024)
        return f"{mb:.1f} MB"

    @property
    def formatted_duration(self) -> str:
        if not self.duration_seconds or self.duration_seconds <= 0:
            return "--:--"
        mins = int(self.duration_seconds // 60)
        secs = int(self.duration_seconds % 60)
        return f"{mins:02d}:{secs:02d}"


class DownloadHistoryService:
    """Manages reading, persisting, and mutating local download history."""

    def __init__(self, history_file: Optional[Path] = None) -> None:
        if history_file:
            self.history_file = Path(history_file).resolve()
        else:
            # Default to user home music/elotrack or local app data
            storage_dir = Path.home() / ".elotrack"
            try:
                storage_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                storage_dir = Path("./downloads").resolve()
                storage_dir.mkdir(parents=True, exist_ok=True)
            self.history_file = storage_dir / "history.json"

        self._items: List[HistoryItem] = []
        self._load()

    def _load(self) -> None:
        """Loads records from JSON storage file."""
        if not self.history_file.exists():
            self._items = []
            return

        try:
            content = self.history_file.read_text(encoding="utf-8")
            raw_list = json.loads(content)
            self._items = [
                HistoryItem(
                    id=item["id"],
                    title=item.get("title", "Desconhecido"),
                    artist=item.get("artist", "YouTube"),
                    format=item.get("format", "mp3"),
                    file_path=item.get("file_path", ""),
                    file_size_bytes=item.get("file_size_bytes", 0),
                    duration_seconds=item.get("duration_seconds"),
                    downloaded_at=item.get("downloaded_at", ""),
                    url=item.get("url", ""),
                    thumbnail_url=item.get("thumbnail_url"),
                    thumbnail_path=item.get("thumbnail_path"),
                    is_trim=bool(item.get("is_trim", False) or "[recorte" in str(item.get("file_path", "")).lower()),
                    time_range=item.get("time_range"),
                )
                for item in raw_list
                if isinstance(item, dict) and "id" in item and "file_path" in item
            ]
        except Exception as exc:
            logger.warning("Falha ao carregar histórico de downloads (%s): %s", self.history_file, exc)
            self._items = []

    def _save(self) -> None:
        """Flushes in-memory items to JSON storage."""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            raw = [asdict(item) for item in self._items]
            self.history_file.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            logger.error("Falha ao salvar histórico de downloads (%s): %s", self.history_file, exc)

    def add_from_result(self, result: DownloadResult) -> Optional[HistoryItem]:
        """Creates and stores a history item from a successful DownloadResult."""
        if not result.success or not result.output_path or not result.output_path.exists():
            return None

        size = 0
        try:
            size = result.output_path.stat().st_size
        except OSError:
            pass

        meta = result.metadata or {}
        is_trim = bool(meta.get("is_trim", False) or "[recorte" in result.output_path.stem.lower())
        time_range = meta.get("time_range")

        # Generate unique id based on file path and timestamp
        item_id = f"{result.output_path.stem}_{int(datetime.now(timezone.utc).timestamp())}"
        item = HistoryItem(
            id=item_id,
            title=result.title or result.output_path.stem,
            artist=result.artist or meta.get("uploader") or "YouTube",
            format=(result.final_format or result.output_path.suffix.lstrip(".")).lower(),
            file_path=str(result.output_path.resolve()),
            file_size_bytes=size,
            duration_seconds=result.duration_seconds,
            url=result.url,
            thumbnail_url=meta.get("thumbnail"),
            thumbnail_path=meta.get("thumbnail_path"),
            is_trim=is_trim,
            time_range=time_range,
        )

        # Prepend to display newest first; avoid duplicate entries of same file
        self._items = [i for i in self._items if i.file_path != item.file_path]
        self._items.insert(0, item)
        # Cap at 50 records
        if len(self._items) > 50:
            self._items = self._items[:50]
        self._save()
        return item

    def get_items(self, limit: int = 50) -> List[HistoryItem]:
        """Returns the most recent history items."""
        return self._items[:limit]

    def get_grouped_items(self, limit: int = 100, filter_text: str = "") -> List[dict]:
        """Returns history records grouped by song/track, optionally filtered by search text."""
        import re

        groups: dict[str, dict] = {}
        ordered_keys: list[str] = []
        q = filter_text.strip().lower()

        for item in self._items:
            # Check filter match
            if q:
                file_name = Path(item.file_path).name.lower()
                matches = (
                    q in item.title.lower()
                    or q in item.artist.lower()
                    or q in item.format.lower()
                    or q in file_name
                )
                if not matches:
                    continue

            key = self._extract_group_key(item)
            if key not in groups:
                if len(ordered_keys) >= limit:
                    continue
                ordered_keys.append(key)
                # Clean up title for canonical group header
                clean_title = re.sub(r"\s*\[recorte.*?\]", "", item.title, flags=re.IGNORECASE).strip()
                groups[key] = {
                    "key": key,
                    "title": clean_title or item.title,
                    "artist": item.artist,
                    "url": item.url,
                    "thumbnail_url": item.thumbnail_url,
                    "thumbnail_path": item.thumbnail_path,
                    "latest_downloaded_at": item.downloaded_at,
                    "items": [],
                }

            g = groups[key]
            # If group has missing or placeholder thumbnail/url, backfill from item
            if (not g["thumbnail_path"] or not Path(g["thumbnail_path"]).is_file()) and item.thumbnail_path:
                g["thumbnail_path"] = item.thumbnail_path
            if not g["thumbnail_url"] and item.thumbnail_url:
                g["thumbnail_url"] = item.thumbnail_url
            if not g["url"] and item.url:
                g["url"] = item.url
            if g["artist"] in ("YouTube", "Desconhecido") and item.artist not in ("YouTube", "Desconhecido"):
                g["artist"] = item.artist

            g["items"].append(item)

        result_groups = []
        for key in ordered_keys:
            g = groups[key]
            # Order versions: full tracks first, then recortes; within same type, newer first
            g["items"].sort(key=lambda it: (it.is_trim, it.downloaded_at), reverse=False)
            result_groups.append(g)

        return result_groups

    def prune_missing_files(self) -> int:
        """Removes all history records whose files no longer exist on disk."""
        initial_len = len(self._items)
        self._items = [i for i in self._items if i.file_exists]
        removed = initial_len - len(self._items)
        if removed > 0:
            self._save()
        return removed

    def get_missing_files_count(self) -> int:
        """Returns the number of history records whose files are missing from disk."""
        return sum(1 for i in self._items if not i.file_exists)

    @staticmethod
    def _extract_group_key(item: HistoryItem) -> str:
        """Derives a grouping key so different formats and trims of the same song group together."""
        import re

        if item.url:
            m = re.search(r"([a-zA-Z0-9_-]{11})", item.url)
            if m:
                return f"yt_{m.group(1)}"
            return f"url_{item.url.strip().lower()}"

        # Fallback to normalized title without recorte annotations
        norm = re.sub(r"\[recorte.*?\]", "", item.title, flags=re.IGNORECASE)
        norm = re.sub(r"\[[a-zA-Z0-9_-]{11}\]", "", norm)
        norm = re.sub(r"[\s_-]+", " ", norm).strip().lower()
        if norm:
            return f"title_{norm}"
        return f"file_{Path(item.file_path).stem.lower()}"

    def remove_item(self, item_id: str) -> bool:
        """Removes a record by its unique ID."""
        initial_len = len(self._items)
        self._items = [i for i in self._items if i.id != item_id]
        if len(self._items) != initial_len:
            self._save()
            return True
        return False

    def clear(self) -> None:
        """Wipes all records from history."""
        self._items = []
        self._save()
