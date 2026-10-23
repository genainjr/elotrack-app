"""Validation services for environment binaries, URLs, and file system permissions."""

from __future__ import annotations

import logging
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class EnvironmentValidator:
    """Verifies external system dependencies, specifically FFmpeg."""

    COMMON_WINDOWS_PATHS = [
        Path(r"C:\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe"),
        Path(r"C:\ProgramData\chocolatey\bin\ffmpeg.exe"),
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe")),
    ]

    @classmethod
    def get_ffmpeg_path(cls, custom_path: Optional[Path] = None) -> Optional[Path]:
        """Locates the ffmpeg executable in app bundle, PATH, or known locations."""
        if custom_path:
            resolved = Path(custom_path).resolve()
            if resolved.is_file() and os.access(resolved, os.X_OK):
                return resolved

        # Check bundled / portable locations (PyInstaller frozen or local bin folder)
        candidate_dirs = []
        if getattr(sys, "frozen", False):
            if hasattr(sys, "_MEIPASS"):
                candidate_dirs.append(Path(sys._MEIPASS))
                candidate_dirs.append(Path(sys._MEIPASS) / "bin")
            exe_parent = Path(sys.executable).resolve().parent
            candidate_dirs.append(exe_parent)
            candidate_dirs.append(exe_parent / "bin")

        if os.name == "nt":
            try:
                candidate_dirs.append(Path.cwd())
                candidate_dirs.append(Path.cwd() / "bin")
            except (OSError, ValueError):
                pass

        for bdir in candidate_dirs:
            exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
            candidate = bdir / exe_name
            try:
                if candidate.is_file() and os.access(candidate, os.X_OK):
                    return candidate.resolve()
            except OSError:
                continue

        # Check system PATH
        which_path = shutil.which("ffmpeg")
        if which_path:
            return Path(which_path).resolve()

        # Check common Windows fallback locations
        if os.name == "nt":
            # 1. Check known fixed locations
            for candidate in cls.COMMON_WINDOWS_PATHS:
                try:
                    if candidate.exists() and candidate.is_file():
                        return candidate.resolve()
                except OSError:
                    continue

            # 2. Check WinGet Packages directory
            winget_packages = Path(os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"))
            if winget_packages.exists():
                try:
                    for found in winget_packages.glob("**/bin/ffmpeg.exe"):
                        if found.is_file():
                            return found.resolve()
                    for found in winget_packages.glob("**/ffmpeg.exe"):
                        if found.is_file():
                            return found.resolve()
                except OSError:
                    pass

            # 3. Check Windows Registry User and Machine PATH
            try:
                import winreg

                for root_key in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                    subkey = r"Environment" if root_key == winreg.HKEY_CURRENT_USER else r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"
                    try:
                        with winreg.OpenKey(root_key, subkey) as key:
                            reg_path, _ = winreg.QueryValueEx(key, "Path")
                            for entry in reg_path.split(";"):
                                entry_clean = os.path.expandvars(entry.strip())
                                if entry_clean:
                                    candidate = Path(entry_clean) / "ffmpeg.exe"
                                    if candidate.is_file():
                                        return candidate.resolve()
                    except OSError:
                        continue
            except ImportError:
                pass

        return None

    @classmethod
    def is_ffmpeg_available(cls, custom_path: Optional[Path] = None) -> bool:
        """Returns True if a usable FFmpeg binary is detected."""
        return cls.get_ffmpeg_path(custom_path) is not None

    @classmethod
    def get_ffmpeg_install_guide(cls) -> str:
        """Returns a user-friendly installation guide according to the OS."""
        if os.name == "nt":
            return (
                "FFmpeg não foi encontrado no sistema (PATH).\n"
                "Para instalar no Windows, escolha uma das opções abaixo:\n"
                "  1. Via Winget (Recomendado): winget install Gyan.FFmpeg\n"
                "  2. Via Chocolatey:           choco install ffmpeg\n"
                "  3. Via Scoop:                scoop install ffmpeg\n"
                "  4. Manual: Baixe em https://www.gyan.dev/ffmpeg/builds/ e adicione a pasta 'bin' ao PATH do sistema."
            )
        return (
            "FFmpeg não foi encontrado no sistema (PATH).\n"
            "Para instalar no Linux/macOS:\n"
            "  - Ubuntu/Debian: sudo apt update && sudo apt install ffmpeg\n"
            "  - Fedora/RHEL:   sudo dnf install ffmpeg\n"
            "  - Arch Linux:    sudo pacman -S ffmpeg\n"
            "  - macOS (Brew):  brew install ffmpeg"
        )


class URLValidator:
    """Validates and inspects YouTube URL patterns."""

    # Matches youtube.com/watch?v=..., youtu.be/..., youtube.com/shorts/..., music.youtube.com/...
    YOUTUBE_REGEX = re.compile(
        r"^(https?://)?(www\.|music\.)?"
        r"(youtube\.com/(watch\?.*v=|embed/|v/|shorts/)|youtu\.be/)"
        r"([a-zA-Z0-9_-]{11})"
    )

    @classmethod
    def is_valid_youtube_url(cls, url: Optional[str]) -> bool:
        """Checks whether the given string is a valid YouTube video/track URL."""
        if not url or not isinstance(url, str):
            return False
        clean_url = url.strip()
        return bool(cls.YOUTUBE_REGEX.search(clean_url))

    @classmethod
    def extract_video_id(cls, url: str) -> Optional[str]:
        """Extracts the 11-character video ID from a YouTube URL if present."""
        if not url:
            return None
        match = cls.YOUTUBE_REGEX.search(url.strip())
        return match.group(5) if match else None

    @classmethod
    def clean_video_url(cls, url: str) -> str:
        """Strips playlist parameters (e.g. &list=RD..., &start_radio=1) if video ID is present."""
        vid = cls.extract_video_id(url)
        if vid:
            return f"https://www.youtube.com/watch?v={vid}"
        return url.strip()


class FileSystemValidator:
    """Validates local destination paths and write permissions."""

    @classmethod
    def validate_output_directory(
        cls, directory: Path, create_if_missing: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """Verifies if the output directory exists or can be created and has write access."""
        try:
            target_dir = Path(directory).resolve()
            if not target_dir.exists():
                if create_if_missing:
                    target_dir.mkdir(parents=True, exist_ok=True)
                else:
                    return False, f"Diretório inexistente: {target_dir}"

            if not target_dir.is_dir():
                return False, f"O caminho especificado não é uma pasta: {target_dir}"

            # Test write permissions by creating and deleting a temporary probe file
            test_file = target_dir / ".write_probe.tmp"
            try:
                test_file.touch()
                test_file.unlink()
            except (OSError, PermissionError) as pe:
                return False, f"Sem permissão de escrita em '{target_dir}': {pe}"

            return True, None
        except Exception as e:
            return False, f"Falha ao validar diretório '{directory}': {e}"
