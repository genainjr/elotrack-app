"""Font management and dynamic loading for Elo Track GUI with One Elo typography parity."""

from __future__ import annotations

import ctypes
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import customtkinter as ctk

logger = logging.getLogger(__name__)

_LOADED_FONT_FAMILY: Optional[str] = None


def setup_application_fonts() -> str:
    """Loads bundled Inter fonts and registers them for CustomTkinter."""
    global _LOADED_FONT_FAMILY
    if _LOADED_FONT_FAMILY:
        return _LOADED_FONT_FAMILY

    # Locate assets/fonts directory
    candidates = []
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            candidates.append(Path(sys._MEIPASS) / "assets" / "fonts")
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / "assets" / "fonts")

    candidates.append(Path(__file__).resolve().parent.parent.parent / "assets" / "fonts")
    candidates.append(Path.cwd() / "assets" / "fonts")

    fonts_dir = None
    for cand in candidates:
        if cand.is_dir():
            fonts_dir = cand
            break

    # Register TTF files on Windows
    if fonts_dir and os.name == "nt":
        for ttf_path in fonts_dir.glob("*.ttf"):
            try:
                # FR_PRIVATE = 0x10 (available only to this process)
                ret = ctypes.windll.gdi32.AddFontResourceExW(str(ttf_path), 0x10, 0)
                if ret > 0:
                    logger.debug("Loaded font resource: %s", ttf_path.name)
            except Exception as exc:
                logger.debug("Could not register font %s: %s", ttf_path, exc)

    # Detect active Inter family name in Tkinter
    chosen_family = "Segoe UI"
    try:
        import tkinter as tk
        import tkinter.font as tkfont

        temp_root = tk.Tk()
        temp_root.withdraw()
        available = tkfont.families()
        temp_root.destroy()

        for cand in ("Inter 18pt", "Inter", "Segoe UI", "SF Pro Display", "Roboto"):
            if cand in available:
                chosen_family = cand
                break
    except Exception as exc:
        logger.debug("Failed font detection: %s", exc)

    # Apply globally to CustomTkinter ThemeManager
    try:
        ctk.ThemeManager.theme["CTkFont"]["family"] = chosen_family
    except Exception:
        pass

    _LOADED_FONT_FAMILY = chosen_family
    logger.info("Application typography configured with family: %s", chosen_family)
    return chosen_family


def get_font_family() -> str:
    """Returns the active font family name."""
    global _LOADED_FONT_FAMILY
    if not _LOADED_FONT_FAMILY:
        return setup_application_fonts()
    return _LOADED_FONT_FAMILY
