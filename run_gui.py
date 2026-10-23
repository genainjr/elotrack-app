"""Quick launcher for Elo Track Desktop GUI."""

import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import os
from src.core.validator import EnvironmentValidator

ffmpeg_bin = EnvironmentValidator.get_ffmpeg_path()
if ffmpeg_bin:
    ffmpeg_dir = str(ffmpeg_bin.parent if ffmpeg_bin.is_file() else ffmpeg_bin)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{os.environ.get('PATH', '')}"

try:
    from yt_dlp.downloader import FFmpegFD
    FFmpegFD._available = True
except Exception:
    pass

from src.gui.app import launch_gui

if __name__ == "__main__":
    launch_gui()
