"""Audio player service powered by pygame.mixer."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    pygame = None  # type: ignore
    PYGAME_AVAILABLE = False

logger = logging.getLogger(__name__)


class AudioPlayerService:
    """Manages playback, seeking, pausing and track timing."""

    def __init__(self) -> None:
        self._initialized = False
        self._current_file: Optional[Path] = None
        self._duration: float = 0.0
        self._start_offset: float = 0.0
        self._is_paused = False
        self._is_loaded = False

    def _ensure_mixer(self) -> bool:
        if not PYGAME_AVAILABLE:
            return False
        if not self._initialized:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                self._initialized = True
            except Exception as e:
                logger.error("Falha ao inicializar pygame.mixer: %s", e)
                return False
        return True

    def load(self, file_path: Path, duration: float = 0.0) -> bool:
        """Loads an audio file into the player."""
        if not self._ensure_mixer():
            return False

        resolved = Path(file_path).resolve()
        if not resolved.is_file():
            logger.error("Arquivo de áudio não encontrado: %s", resolved)
            return False

        try:
            self.stop()
            try:
                pygame.mixer.music.load(str(resolved))
            except Exception as load_err:
                logger.info("Formato não suportado nativamente pelo mixer (%s). Transcodificando via FFmpeg...", resolved.suffix)
                transcoded = self._transcode_to_wav(resolved)
                if transcoded:
                    pygame.mixer.music.load(str(transcoded))
                else:
                    raise load_err

            self._current_file = resolved
            self._duration = duration
            self._start_offset = 0.0
            self._is_paused = False
            self._is_loaded = True
            return True
        except Exception as e:
            logger.exception("Erro ao carregar áudio no player: %s", e)
            return False

    def _transcode_to_wav(self, input_path: Path) -> Optional[Path]:
        """Transcodes unsupported audio formats (e.g. M4A/AAC) to a temporary WAV for playback."""
        try:
            import subprocess
            from .validator import EnvironmentValidator

            ffmpeg_path = EnvironmentValidator.get_ffmpeg_path()
            if not ffmpeg_path:
                return None

            cache_dir = Path.home() / ".cache" / "elotrack" / "playback"
            cache_dir.mkdir(parents=True, exist_ok=True)
            out_wav = cache_dir / f"{input_path.stem}.wav"
            if out_wav.exists() and out_wav.stat().st_size > 1000:
                return out_wav

            cmd = [
                str(ffmpeg_path),
                "-y",
                "-i", str(input_path),
                "-vn",
                "-ac", "2",
                "-ar", "44100",
                str(out_wav)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            if out_wav.exists() and out_wav.stat().st_size > 0:
                return out_wav
        except Exception as exc:
            logger.warning("Falha na transcodificação para reprodução via FFmpeg: %s", exc)
        return None

    def play(self, start_seconds: float = 0.0) -> bool:
        """Plays or seeks to start_seconds."""
        if not self._is_loaded or not self._ensure_mixer():
            return False

        try:
            self._start_offset = max(0.0, start_seconds)
            pygame.mixer.music.play(start=self._start_offset)
            self._is_paused = False
            return True
        except Exception as e:
            logger.exception("Erro ao iniciar reprodução: %s", e)
            return False

    def pause(self) -> None:
        """Pauses active playback."""
        if self._initialized and pygame.mixer.music.get_busy() and not self._is_paused:
            pygame.mixer.music.pause()
            self._is_paused = True

    def unpause(self) -> None:
        """Resumes paused playback."""
        if self._initialized and self._is_paused:
            pygame.mixer.music.unpause()
            self._is_paused = False

    def stop(self) -> None:
        """Stops playback and resets offset."""
        if self._initialized:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self._start_offset = 0.0
        self._is_paused = False

    def get_current_time(self) -> float:
        """Calculates current playback position in seconds."""
        if not self._initialized or not self._is_loaded:
            return 0.0
        if not pygame.mixer.music.get_busy() and not self._is_paused:
            return self._start_offset

        pos_ms = pygame.mixer.music.get_pos()
        if pos_ms < 0:
            return self._start_offset
        return self._start_offset + (pos_ms / 1000.0)

    @property
    def is_playing(self) -> bool:
        return self._initialized and pygame.mixer.music.get_busy() and not self._is_paused

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def duration(self) -> float:
        return self._duration

    @property
    def is_loaded(self) -> bool:
        return self._is_loaded
