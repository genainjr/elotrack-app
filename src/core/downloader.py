"""High-fidelity audio extraction engine powered by yt-dlp and ffmpeg."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import yt_dlp
    from yt_dlp.utils import DownloadError, ExtractorError, download_range_func
except ImportError:
    yt_dlp = None  # type: ignore
    DownloadError = Exception  # type: ignore
    ExtractorError = Exception  # type: ignore
    download_range_func = None  # type: ignore

from .config import AppConfig, ConfigManager
from .interfaces import (
    AudioDownloader,
    DownloadRequest,
    DownloadResult,
    ProgressEvent,
    ProgressReporter,
    ProgressStatus,
)
from .validator import EnvironmentValidator, FileSystemValidator, URLValidator

logger = logging.getLogger(__name__)


class YtDlpAudioDownloader(AudioDownloader):
    """Concrete AudioDownloader implementation utilizing yt-dlp and external FFmpeg.

    Fully decoupled from presentation logic; reports progress strictly through
    the ProgressReporter interface and structured Python logging.
    """

    def __init__(
        self,
        config: Optional[AppConfig] = None,
        ffmpeg_path: Optional[Path] = None,
    ) -> None:
        self.config = config or ConfigManager.get_instance().config
        self.ffmpeg_path = ffmpeg_path or EnvironmentValidator.get_ffmpeg_path(
            self.config.ffmpeg_binary_path
        )

    def inspect_metadata(self, url: str) -> Dict[str, Any]:
        """Fetches metadata for a YouTube URL without downloading media."""
        if not yt_dlp:
            raise RuntimeError("Biblioteca 'yt-dlp' não está instalada no ambiente.")

        if not URLValidator.is_valid_youtube_url(url):
            raise ValueError(f"URL inválida para extração de áudio: {url}")

        ydl_opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info("Inspecionando metadados de: %s", url)
            info = ydl.extract_info(url, download=False)
            return info or {}

    def download(
        self,
        request: DownloadRequest,
        reporter: Optional[ProgressReporter] = None,
    ) -> DownloadResult:
        """Executes the download and audio extraction pipeline."""
        if not yt_dlp:
            err = "Biblioteca 'yt-dlp' não encontrada. Instale via 'pip install yt-dlp'."
            logger.error(err)
            if reporter:
                reporter.on_error(err, request.url)
            return DownloadResult(success=False, url=request.url, error_message=err)

        # 1. URL Validation
        if not URLValidator.is_valid_youtube_url(request.url):
            err_msg = f"URL do YouTube inválida ou malformada: '{request.url}'"
            logger.error(err_msg)
            if reporter:
                reporter.on_error(err_msg, request.url)
            return DownloadResult(success=False, url=request.url, error_message=err_msg)

        # 2. Output Directory Validation
        dir_ok, dir_err = FileSystemValidator.validate_output_directory(
            request.output_dir, create_if_missing=True
        )
        if not dir_ok:
            err_msg = dir_err or "Falha de validação do diretório de destino."
            logger.error(err_msg)
            if reporter:
                reporter.on_error(err_msg, request.url)
            return DownloadResult(success=False, url=request.url, error_message=err_msg)

        # 3. FFmpeg Validation (required for extraction & conversion)
        active_ffmpeg = self.ffmpeg_path or EnvironmentValidator.get_ffmpeg_path(
            self.config.ffmpeg_binary_path
        )
        if not active_ffmpeg:
            err_guide = EnvironmentValidator.get_ffmpeg_install_guide()
            logger.error("FFmpeg não localizado. %s", err_guide)
            if reporter:
                reporter.on_error(err_guide, request.url)
            return DownloadResult(success=False, url=request.url, error_message=err_guide)

        # Ensure FFmpeg directory is in process PATH for yt-dlp internal range & format cutters
        ffmpeg_dir = str(active_ffmpeg.parent if active_ffmpeg.is_file() else active_ffmpeg)
        current_path = os.environ.get("PATH", "")
        if ffmpeg_dir not in current_path:
            os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{current_path}"

        try:
            from yt_dlp.downloader import FFmpegFD
            FFmpegFD._available = True
        except Exception:
            pass

        # Notify Start
        target_url = (
            request.url
            if request.download_playlist
            else URLValidator.clean_video_url(request.url)
        )

        if reporter:
            reporter.on_stage_changed(
                ProgressStatus.STARTING, f"Iniciando preparação para extração de áudio de: {target_url}"
            )

        # 4. Prepare yt-dlp Configuration
        template = request.custom_filename_template or self.config.filename_template
        out_template_path = str(request.output_dir / template)

        ydl_opts = self._build_ydl_options(
            request=request,
            out_template=out_template_path,
            ffmpeg_path=active_ffmpeg,
            reporter=reporter,
        )

        extracted_file_path: Optional[Path] = None
        info_dict: Dict[str, Any] = {}

        try:
            logger.info("Iniciando processo yt-dlp com stream 'bestaudio/best'...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(target_url, download=True) or {}
                extracted_file_path = self._resolve_output_file(
                    request=request,
                    info_dict=info_dict,
                )

            # 5. Run downstream AudioProcessors if provided (Open/Closed Principle)
            final_audio_path = extracted_file_path
            if final_audio_path and final_audio_path.exists() and request.post_processors:
                for processor in request.post_processors:
                    logger.info("Executando pós-processador '%s'...", processor.name)
                    if reporter:
                        reporter.on_stage_changed(
                            ProgressStatus.PROCESSING,
                            f"Executando pipeline adicional: {processor.name}...",
                        )
                    final_audio_path = processor.process(
                        final_audio_path,
                        metadata=info_dict,
                        time_range=request.time_range,
                    )

            # Cache thumbnail locally if available
            thumbnail_local_path = None
            thumb_url = info_dict.get("thumbnail")

            # Enhanced WAV metadata tagging (ID3v2.3 chunk in addition to RIFF INFO)
            if final_audio_path and final_audio_path.exists() and request.audio_format.lower() == "wav" and request.embed_metadata:
                try:
                    import mutagen
                    from mutagen.wave import WAVE
                    from mutagen.id3 import TIT2, TPE1, TALB, TDRC

                    audio_wav = WAVE(final_audio_path)
                    try:
                        audio_wav.add_tags()
                    except Exception:
                        pass

                    title_val = info_dict.get("title")
                    artist_val = info_dict.get("artist") or info_dict.get("uploader") or info_dict.get("channel")
                    album_val = info_dict.get("album") or title_val

                    if audio_wav.tags is not None:
                        if title_val:
                            audio_wav.tags.add(TIT2(encoding=1, text=[title_val]))
                        if artist_val:
                            audio_wav.tags.add(TPE1(encoding=1, text=[artist_val]))
                        if album_val:
                            audio_wav.tags.add(TALB(encoding=1, text=[album_val]))
                        upload_date = info_dict.get("upload_date")
                        if upload_date and len(upload_date) >= 4:
                            audio_wav.tags.add(TDRC(encoding=1, text=[upload_date[:4]]))
                        audio_wav.save(v2_version=3)
                        logger.info("Tags ID3v2.3 injetadas com sucesso no arquivo WAV: %s", final_audio_path.name)
                except Exception as exc:
                    logger.debug("Tentativa de injeção ID3 no WAV ignorada: %s", exc)

            if thumb_url:
                try:
                    thumb_cache_dir = Path.home() / ".elotrack" / "thumbnails"
                    thumb_cache_dir.mkdir(parents=True, exist_ok=True)
                    video_id = info_dict.get("id") or (final_audio_path.stem if final_audio_path else "thumb")
                    cached_file = thumb_cache_dir / f"{video_id}.jpg"
                    if not cached_file.exists() or cached_file.stat().st_size == 0:
                        import urllib.request
                        req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            data = resp.read()
                            if data:
                                cached_file.write_bytes(data)
                    if cached_file.exists():
                        thumbnail_local_path = str(cached_file.resolve())
                except Exception as exc:
                    logger.debug("Falha ao salvar miniatura em cache: %s", exc)

            result = DownloadResult(
                success=True,
                url=request.url,
                output_path=final_audio_path,
                title=info_dict.get("title"),
                artist=info_dict.get("artist") or info_dict.get("uploader") or info_dict.get("channel"),
                duration_seconds=info_dict.get("duration"),
                final_format=request.audio_format,
                file_size_bytes=final_audio_path.stat().st_size if final_audio_path and final_audio_path.exists() else None,
                metadata={
                    "id": info_dict.get("id"),
                    "view_count": info_dict.get("view_count"),
                    "thumbnail": info_dict.get("thumbnail"),
                    "thumbnail_path": thumbnail_local_path,
                    "extractor": info_dict.get("extractor"),
                    "is_trim": bool(request.time_range),
                    "time_range": f"{request.time_range[0]}-{request.time_range[1]}" if request.time_range else None,
                },
            )

            if reporter:
                reporter.on_complete(result)

            return result

        except DownloadError as de:
            err_msg = f"Erro no download do YouTube (vídeo privado, removido ou indisponível): {de}"
            logger.error(err_msg, exc_info=True)
            if reporter:
                reporter.on_error(err_msg, request.url)
            return DownloadResult(success=False, url=request.url, error_message=err_msg)

        except Exception as exc:
            err_msg = f"Falha inesperada durante a extração de áudio: {exc}"
            logger.exception(err_msg)
            if reporter:
                reporter.on_error(err_msg, request.url)
            return DownloadResult(success=False, url=request.url, error_message=err_msg)

    def _build_ydl_options(
        self,
        request: DownloadRequest,
        out_template: str,
        ffmpeg_path: Path,
        reporter: Optional[ProgressReporter],
    ) -> Dict[str, Any]:
        """Assembles yt-dlp configuration dictionary."""
        postprocessors: list[dict[str, Any]] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": request.audio_format,
                "preferredquality": request.audio_quality,
                "nopostoverwrites": False,
            }
        ]

        if request.embed_metadata:
            postprocessors.append({"key": "FFmpegMetadata", "add_metadata": True})

        has_mutagen = False
        try:
            import mutagen  # noqa: F401
            has_mutagen = True
        except ImportError:
            pass

        embed_thumb_formats = ("mp3", "m4a", "flac") if has_mutagen else ("mp3", "m4a")
        if request.embed_thumbnail and request.audio_format.lower() in embed_thumb_formats:
            postprocessors.append({"key": "FFmpegThumbnailsConvertor", "format": "jpg"})
            postprocessors.append({"key": "EmbedThumbnail", "already_have_thumbnail": False})

        progress_hooks = []
        if reporter:
            progress_hooks.append(self._create_progress_hook(reporter, request.url))

        postprocessor_hooks = []
        if reporter:
            postprocessor_hooks.append(self._create_postprocessor_hook(reporter, request.url))

        opts: Dict[str, Any] = {
            "format": "bestaudio/best",
            "outtmpl": out_template,
            "ffmpeg_location": str(ffmpeg_path.parent if ffmpeg_path.is_file() else ffmpeg_path),
            "noplaylist": not request.download_playlist,
            "writethumbnail": bool(request.embed_thumbnail and request.audio_format.lower() in embed_thumb_formats),
            "postprocessors": postprocessors,
            "progress_hooks": progress_hooks,
            "postprocessor_hooks": postprocessor_hooks,
            "keepvideo": request.keep_original,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "socket_timeout": self.config.socket_timeout,
            "retries": self.config.max_retries,
            "extractor_args": {"youtube": {"player_client": ["android", "ios", "web"]}},
        }

        # Lossless / Target Quality Settings
        if request.audio_format in ("wav", "flac"):
            # Avoid recompressing with lossy bitrate settings
            opts["postprocessor_args"] = {
                "FFmpegExtractAudio": ["-acodec", "pcm_s16le" if request.audio_format == "wav" else "flac"]
            }

        # Optional Time Range (partial track extraction)
        if request.time_range and download_range_func:
            start_s, end_s = request.time_range
            opts["download_ranges"] = download_range_func(None, [(start_s, end_s)])
            opts["force_keyframes_at_cuts"] = True

        # Extra options extension point
        if request.extra_options:
            opts.update(request.extra_options)

        return opts

    @staticmethod
    def _create_progress_hook(reporter: ProgressReporter, url: str):
        """Builds a closure that adapts yt-dlp progress callbacks into ProgressEvents."""
        def hook(data: Dict[str, Any]) -> None:
            status_str = data.get("status")
            downloaded = data.get("downloaded_bytes", 0) or 0
            total = data.get("total_bytes") or data.get("total_bytes_estimate")
            speed = data.get("speed")
            eta = data.get("eta")
            filename = data.get("filename")

            pct = 0.0
            if total and total > 0:
                pct = round((downloaded / total) * 100, 2)

            if status_str == "downloading":
                status = ProgressStatus.DOWNLOADING
            elif status_str == "finished":
                status = ProgressStatus.CONVERTING
            elif status_str == "error":
                status = ProgressStatus.ERROR
            else:
                status = ProgressStatus.DOWNLOADING

            event = ProgressEvent(
                status=status,
                url=url,
                filename=Path(filename).name if filename else None,
                downloaded_bytes=downloaded,
                total_bytes=total,
                percentage=pct,
                speed_bytes_sec=speed,
                eta_seconds=eta,
                step_description="Baixando stream de áudio..." if status == ProgressStatus.DOWNLOADING else "Conversão iniciada",
                raw_data=data,
            )
            reporter.on_progress(event)

        return hook

    @staticmethod
    def _create_postprocessor_hook(reporter: ProgressReporter, url: str):
        """Builds a closure that adapts yt-dlp postprocessor callbacks."""
        def hook(data: Dict[str, Any]) -> None:
            status_str = data.get("status")
            pp_name = data.get("postprocessor", "")

            if status_str == "started":
                reporter.on_stage_changed(
                    ProgressStatus.CONVERTING,
                    f"Processando áudio com FFmpeg ({pp_name})...",
                )
            elif status_str == "finished":
                reporter.on_stage_changed(
                    ProgressStatus.PROCESSING,
                    f"Etapa de áudio ({pp_name}) concluída.",
                )

        return hook

    def _resolve_output_file(
        self,
        request: DownloadRequest,
        info_dict: Dict[str, Any],
    ) -> Optional[Path]:
        """Resolves the resulting file path on disk after conversion."""
        # Check standard yt-dlp requested_downloads or filepath
        req_downloads = info_dict.get("requested_downloads")
        if req_downloads and isinstance(req_downloads, list) and len(req_downloads) > 0:
            first_dl = req_downloads[0]
            fp = first_dl.get("filepath")
            if fp:
                path_obj = Path(fp)
                if path_obj.suffix.lstrip(".") != request.audio_format:
                    converted = path_obj.with_suffix(f".{request.audio_format}")
                    if converted.exists():
                        return converted
                if path_obj.exists():
                    return path_obj

        # Fallback inspection by title/id
        video_id = info_dict.get("id")
        matches = []
        if video_id:
            matches = list(request.output_dir.glob(f"*{video_id}*.{request.audio_format}"))

        title = info_dict.get("title")
        if not matches and title:
            safe_prefix = "".join(c for c in title[:20] if c.isalnum() or c in " _-").strip()
            if safe_prefix:
                matches = list(request.output_dir.glob(f"*{safe_prefix}*.{request.audio_format}"))

        if matches:
            if request.time_range:
                trim_matches = [m for m in matches if "[recorte" in m.name.lower()]
                if trim_matches:
                    return max(trim_matches, key=lambda p: p.stat().st_mtime)
            else:
                full_matches = [m for m in matches if "[recorte" not in m.name.lower()]
                if full_matches:
                    return max(full_matches, key=lambda p: p.stat().st_mtime)
            return max(matches, key=lambda p: p.stat().st_mtime)

        # General format glob match
        candidates = list(request.output_dir.glob(f"*.{request.audio_format}"))
        if candidates:
            if request.time_range:
                trim_cands = [c for c in candidates if "[recorte" in c.name.lower()]
                if trim_cands:
                    return max(trim_cands, key=lambda p: p.stat().st_mtime)
            else:
                full_cands = [c for c in candidates if "[recorte" not in c.name.lower()]
                if full_cands:
                    return max(full_cands, key=lambda p: p.stat().st_mtime)
            return max(candidates, key=lambda p: p.stat().st_mtime)

        return None
