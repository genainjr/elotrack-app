"""Unit tests for YouTubeSearchService."""

from unittest.mock import MagicMock, patch
from src.core.search import YouTubeSearchService, SearchResult


class TestYouTubeSearchService:
    def test_empty_query_returns_empty_list(self) -> None:
        service = YouTubeSearchService()
        assert service.search("") == []
        assert service.search("   ") == []

    @patch("yt_dlp.YoutubeDL")
    def test_search_parses_results_correctly(self, mock_ydl_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_ydl_cls.return_value.__enter__.return_value = mock_instance

        mock_instance.extract_info.return_value = {
            "entries": [
                {
                    "id": "abc12345",
                    "title": "Musica Teste",
                    "uploader": "Banda Teste",
                    "duration": 215,
                    "url": "https://www.youtube.com/watch?v=abc12345",
                    "thumbnails": [{"url": "https://i.ytimg.com/vi/abc12345/mqdefault.jpg"}],
                }
            ]
        }

        service = YouTubeSearchService()
        results = service.search("musica teste", max_results=1)

        assert len(results) == 1
        r = results[0]
        assert isinstance(r, SearchResult)
        assert r.video_id == "abc12345"
        assert r.title == "Musica Teste"
        assert r.uploader == "Banda Teste"
        assert r.duration_seconds == 215
        assert r.duration_formatted == "03:35"
        assert r.url == "https://www.youtube.com/watch?v=abc12345"
        assert "abc12345" in r.thumbnail_url

    @patch("yt_dlp.YoutubeDL")
    def test_search_handles_exception_gracefully(self, mock_ydl_cls: MagicMock) -> None:
        mock_instance = MagicMock()
        mock_ydl_cls.return_value.__enter__.return_value = mock_instance
        mock_instance.extract_info.side_effect = RuntimeError("Network error")

        service = YouTubeSearchService()
        results = service.search("error query")
        assert results == []
