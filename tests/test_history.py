"""Tests for DownloadHistoryService."""

from pathlib import Path
from src.core.history import DownloadHistoryService
from src.core.interfaces import DownloadResult


def test_history_service_add_and_load(tmp_path: Path) -> None:
    history_file = tmp_path / "test_history.json"
    service = DownloadHistoryService(history_file=history_file)

    # Create dummy audio file
    fake_audio = tmp_path / "Track One.mp3"
    fake_audio.write_text("dummy-audio-content")

    res = DownloadResult(
        success=True,
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        output_path=fake_audio,
        title="Rick Astley - Never Gonna Give You Up",
        artist="Rick Astley",
        final_format="mp3",
        duration_seconds=213.0,
    )

    item = service.add_from_result(res)
    assert item is not None
    assert item.title == "Rick Astley - Never Gonna Give You Up"
    assert item.format == "mp3"
    assert item.formatted_duration == "03:33"
    assert item.file_exists is True

    # Test persistence by creating another instance pointing to same file
    service2 = DownloadHistoryService(history_file=history_file)
    items = service2.get_items()
    assert len(items) == 1
    assert items[0].id == item.id
    assert items[0].file_path == str(fake_audio.resolve())


def test_history_remove_and_clear(tmp_path: Path) -> None:
    history_file = tmp_path / "test_history.json"
    service = DownloadHistoryService(history_file=history_file)

    fake1 = tmp_path / "1.mp3"
    fake1.write_text("1")
    fake2 = tmp_path / "2.mp3"
    fake2.write_text("2")

    item1 = service.add_from_result(DownloadResult(success=True, url="url1", output_path=fake1, title="Song 1"))
    item2 = service.add_from_result(DownloadResult(success=True, url="url2", output_path=fake2, title="Song 2"))

    assert len(service.get_items()) == 2

    # Remove item 1
    assert item1 is not None
    assert service.remove_item(item1.id) is True
    assert len(service.get_items()) == 1
    assert service.get_items()[0].title == "Song 2"

    # Clear
    service.clear()
    assert len(service.get_items()) == 0


def test_history_thumbnail_metadata_and_path(tmp_path: Path) -> None:
    history_file = tmp_path / "test_history.json"
    service = DownloadHistoryService(history_file=history_file)

    fake_thumb = tmp_path / "thumb.jpg"
    fake_thumb.write_bytes(b"fake-image-bytes")

    fake_audio = tmp_path / "Track.mp3"
    fake_audio.write_text("audio")

    res = DownloadResult(
        success=True,
        url="https://www.youtube.com/watch?v=12345",
        output_path=fake_audio,
        title="Test Song",
        metadata={
            "thumbnail": "https://i.ytimg.com/vi/12345/hqdefault.jpg",
            "thumbnail_path": str(fake_thumb),
        },
    )

    item = service.add_from_result(res)
    assert item is not None
    assert item.url == "https://www.youtube.com/watch?v=12345"
    assert item.thumbnail_url == "https://i.ytimg.com/vi/12345/hqdefault.jpg"
    assert item.thumbnail_path == str(fake_thumb)
    assert item.get_cached_thumbnail_path() == fake_thumb

    # Verify reloading from disk preserves metadata
    service2 = DownloadHistoryService(history_file=history_file)
    loaded = service2.get_items()[0]
    assert loaded.thumbnail_url == "https://i.ytimg.com/vi/12345/hqdefault.jpg"
    assert loaded.thumbnail_path == str(fake_thumb)
    assert loaded.get_cached_thumbnail_path() == fake_thumb


def test_history_grouped_items(tmp_path: Path) -> None:
    history_file = tmp_path / "test_history.json"
    service = DownloadHistoryService(history_file=history_file)

    f1 = tmp_path / "Song [111].mp3"
    f1.write_text("mp3")
    f2 = tmp_path / "Song [111] [recorte 00m10s-00m20s].mp3"
    f2.write_text("trim")
    f3 = tmp_path / "Song [111].flac"
    f3.write_text("flac")
    f4 = tmp_path / "Other Song [222].mp3"
    f4.write_text("other")

    # Add items
    service.add_from_result(DownloadResult(success=True, url="https://youtube.com/watch?v=111", output_path=f1, title="Song"))
    service.add_from_result(DownloadResult(success=True, url="https://youtube.com/watch?v=111", output_path=f2, title="Song", metadata={"is_trim": True}))
    service.add_from_result(DownloadResult(success=True, url="https://youtube.com/watch?v=111", output_path=f3, title="Song", final_format="flac"))
    service.add_from_result(DownloadResult(success=True, url="https://youtube.com/watch?v=222", output_path=f4, title="Other Song"))

    groups = service.get_grouped_items()
    # There should be 2 song groups
    assert len(groups) == 2
    # Group 1 (Other Song, added last)
    assert groups[0]["title"] == "Other Song"
    assert len(groups[0]["items"]) == 1

    # Group 2 (Song, with 3 versions: mp3, flac, trim)
    assert groups[1]["title"] == "Song"
    assert len(groups[1]["items"]) == 3
    # Check that is_trim is preserved
    trim_items = [it for it in groups[1]["items"] if it.is_trim]
    full_items = [it for it in groups[1]["items"] if not it.is_trim]
    assert len(trim_items) == 1
    assert len(full_items) == 2

    # Test filtering
    filtered_song = service.get_grouped_items(filter_text="Other")
    assert len(filtered_song) == 1
    assert filtered_song[0]["title"] == "Other Song"

    filtered_flac = service.get_grouped_items(filter_text="flac")
    assert len(filtered_flac) == 1
    assert filtered_flac[0]["title"] == "Song"

    filtered_none = service.get_grouped_items(filter_text="NonExistentQueryXYZ")
    assert len(filtered_none) == 0


def test_history_sync_prune_missing_files(tmp_path: Path) -> None:
    history_file = tmp_path / "test_history.json"
    service = DownloadHistoryService(history_file=history_file)

    f1 = tmp_path / "PresentSong.mp3"
    f1.write_text("mp3")
    f2 = tmp_path / "DeletedSong.mp3"
    f2.write_text("deleted soon")

    service.add_from_result(DownloadResult(success=True, url="https://youtube.com/watch?v=111", output_path=f1, title="Present"))
    service.add_from_result(DownloadResult(success=True, url="https://youtube.com/watch?v=222", output_path=f2, title="Deleted"))

    assert len(service.get_items()) == 2
    assert service.get_missing_files_count() == 0

    # Delete f2 from disk
    f2.unlink()
    assert service.get_missing_files_count() == 1

    removed = service.prune_missing_files()
    assert removed == 1
    assert len(service.get_items()) == 1
    assert service.get_items()[0].title == "Present"


