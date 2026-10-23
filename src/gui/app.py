"""Modern Desktop GUI for Elo Track with Gemini-style navigation sidebar and dedicated functional views."""

from __future__ import annotations

import io
import logging
import os
import subprocess
import sys
import threading
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional, Tuple

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageOps

from ..adapters.gui_reporter import GuiProgressReporter
from ..core.config import AudioBitrate, AudioFormat, ConfigManager
from ..core.downloader import YtDlpAudioDownloader
from ..core.history import DownloadHistoryService, HistoryItem
from ..core.interfaces import DownloadRequest, DownloadResult, ProgressEvent, ProgressStatus
from ..core.player import AudioPlayerService
from ..core.preview_fetcher import PreviewFetcher
from ..core.search import SearchResult, YouTubeSearchService
from ..core.validator import EnvironmentValidator, URLValidator
from ..core.version import __version__, VersionService, VersionStatus
from .fonts import setup_application_fonts

logger = logging.getLogger(__name__)

FORMAT_SPECS = [
    {
        "id": "MP3 (320 kbps)",
        "label": "MP3",
        "sublabel": "320 kbps • CBR",
        "tag": "Uso Geral",
        "tag_color": "#a1a1aa",
        "desc": (
            "🎵 MP3 (320 kbps) - Máxima Fidelidade MP3\n\n"
            "• Para que serve: Escuta no dia a dia, celular, som do carro e ampla compatibilidade.\n"
            "• Características: Taxa máxima constante de 320 kbps em arquivo leve (~8 a 12 MB)."
        ),
    },
    {
        "id": "WAV (Lossless)",
        "label": "WAV",
        "sublabel": "Lossless • Linear PCM",
        "tag": "★ Stems / IA",
        "tag_color": "#38bdf8",
        "desc": (
            "⭐ WAV (Lossless) - Padrão Ouro para IA e Produção\n\n"
            "• Para que serve: Moises, Demucs, FL Studio, Ableton, Reaper e DJing.\n"
            "• Características: Áudio não comprimido 16-bit 44.1kHz sem perda acústica (~35 a 50 MB)."
        ),
    },
    {
        "id": "FLAC (Lossless)",
        "label": "FLAC",
        "sublabel": "Lossless • Compactado",
        "tag": "Audiófilo",
        "tag_color": "#c084fc",
        "desc": (
            "💎 FLAC (Lossless) - Compressão Sem Perdas\n\n"
            "• Para que serve: Arquivamento audiófilo e coleções de alta definição.\n"
            "• Características: Mesma qualidade matemática do WAV com ~40% menos espaço em disco."
        ),
    },
    {
        "id": "M4A (AAC)",
        "label": "M4A",
        "sublabel": "AAC • Apple",
        "tag": "Padrão Apple",
        "tag_color": "#4ade80",
        "desc": (
            "🍎 M4A (AAC) - Padrão YouTube e Apple\n\n"
            "• Para que serve: Dispositivos Apple (iPhone, iPad, Mac) e players de áudio modernos.\n"
            "• Características: Stream AAC original do YouTube com excelente equilíbrio tamanho/qualidade."
        ),
    },
]


class EloTrackApp(ctk.CTk):
    """Main application window for Elo Track Desktop with Gemini-inspired sidebar architecture."""

    def __init__(self) -> None:
        super().__init__()

        # Appearance & Dimensions (ODS / Gemini-inspired dark aesthetic)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color="#09090b")

        # Setup typography (Inter font from One Elo design system)
        self.app_font_family = setup_application_fonts()
        self._lookup_logo_imgs: list[ctk.CTkImage] = []

        self.title("Elo Track - Extrator de Áudio em Alta Fidelidade")
        self.geometry("1020x740")
        self.minsize(940, 680)

        # Set window icon
        icon_path = self._find_icon()
        if icon_path:
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

        # Core State & Services
        self.config_mgr = ConfigManager.get_instance()
        self.downloader = YtDlpAudioDownloader(config=self.config_mgr.config)
        self.player_service = AudioPlayerService()
        self.preview_fetcher = PreviewFetcher()
        self.history_service = DownloadHistoryService()
        self.version_service = VersionService()
        self.output_dir: Path = self.config_mgr.config.default_output_dir

        self.is_downloading: bool = False
        self.is_fetching_preview: bool = False
        self._is_dragging_slider: bool = False
        self._test_cutoff_time: Optional[float] = None
        self.last_downloaded_file: Optional[Path] = None
        self._playing_history_id: Optional[str] = None
        self._history_play_btns: dict[str, ctk.CTkButton] = {}
        self._thumbnail_cache: dict[str, ctk.CTkImage] = {}
        self._fetching_thumbnails: set[str] = set()
        self.search_service = YouTubeSearchService()
        self.is_searching: bool = False
        self._search_thumb_images: list[ctk.CTkImage] = []
        self.is_version_blocked: bool = False

        self.selected_format: str = "MP3 (320 kbps)"
        self.format_cards: dict[str, list[ctk.CTkFrame]] = {spec["id"]: [] for spec in FORMAT_SPECS}
        self.format_labels: dict[str, list[ctk.CTkLabel]] = {spec["id"]: [] for spec in FORMAT_SPECS}

        # Active Navigation View
        self.active_view_name: str = "full_download"
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        self.views: dict[str, ctk.CTkFrame] = {}

        self._build_ui()
        self._check_dependencies()
        self._check_version_lifecycle()

    def _find_icon(self) -> Optional[Path]:
        """Finds the elotrack.ico icon path across frozen and development environments."""
        candidates = []
        if getattr(sys, "frozen", False):
            if hasattr(sys, "_MEIPASS"):
                candidates.append(Path(sys._MEIPASS) / "assets" / "elotrack.ico")
                candidates.append(Path(sys._MEIPASS) / "elotrack.ico")
            exe_dir = Path(sys.executable).resolve().parent
            candidates.append(exe_dir / "assets" / "elotrack.ico")
            candidates.append(exe_dir / "elotrack.ico")

        # Dev paths
        candidates.append(Path(__file__).resolve().parent.parent.parent / "assets" / "elotrack.ico")
        candidates.append(Path.cwd() / "assets" / "elotrack.ico")

        for c in candidates:
            if c.is_file():
                return c
        return None

    def _find_lookup_logo(self, variant: str = "sm") -> Optional[Path]:
        """Finds the official Lookup Labs logo badge path across frozen and development environments."""
        filename = f"lookup_labs_badge_{variant}.png"
        candidates = []
        if getattr(sys, "frozen", False):
            if hasattr(sys, "_MEIPASS"):
                candidates.append(Path(sys._MEIPASS) / "assets" / filename)
                candidates.append(Path(sys._MEIPASS) / filename)
            exe_dir = Path(sys.executable).resolve().parent
            candidates.append(exe_dir / "assets" / filename)

        candidates.append(Path(__file__).resolve().parent.parent.parent / "assets" / filename)
        candidates.append(Path.cwd() / "assets" / filename)

        for c in candidates:
            if c.is_file():
                return c
        return None

    def _create_lookup_pill(self, parent_frame: ctk.CTkFrame) -> ctk.CTkFrame:
        """Renders the official Lookup Labs branding pill in the top-right corner."""
        pill = ctk.CTkFrame(
            parent_frame,
            fg_color="#18181b",
            border_color="#27272a",
            border_width=1,
            corner_radius=20,
            height=34,
        )
        pill.pack(side="right")

        inner = ctk.CTkFrame(pill, fg_color="transparent")
        inner.pack(padx=12, pady=4)

        logo_path = self._find_lookup_logo("sm")
        if logo_path and logo_path.is_file():
            try:
                pil_img = Image.open(str(logo_path)).convert("RGBA")
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(20, 20))
                self._lookup_logo_imgs.append(ctk_img)
                ctk.CTkLabel(inner, text="", image=ctk_img).pack(side="left", padx=(0, 8))
            except Exception:
                pass

        lbl_col = ctk.CTkFrame(inner, fg_color="transparent")
        lbl_col.pack(side="left")

        ctk.CTkLabel(
            lbl_col,
            text="Lookup Labs",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#f4f4f5",
        ).pack(anchor="w")

        return pill

    @property
    def format_segmented(self):
        """Adapter providing get() compatibility for selected audio format."""
        class _Adapter:
            def __init__(adapter_self, app):
                adapter_self.app = app
            def get(adapter_self) -> str:
                return adapter_self.app.selected_format
            def set(adapter_self, val: str) -> None:
                adapter_self.app._select_format(val)
        return _Adapter(self)

    def _select_format(self, format_id: str) -> None:
        """Selects active audio format and synchronizes card styles across all views."""
        self.selected_format = format_id
        for spec in FORMAT_SPECS:
            f_id = spec["id"]
            cards = self.format_cards.get(f_id, [])
            labels = self.format_labels.get(f_id, [])
            is_active = (f_id == format_id)

            for card in cards:
                if is_active:
                    card.configure(fg_color="#172554", border_color="#2563eb", border_width=2)
                else:
                    card.configure(fg_color="#09090b", border_color="#27272a", border_width=1)

            for lbl in labels:
                if is_active:
                    lbl.configure(text_color="#60a5fa")
                else:
                    lbl.configure(text_color="#e4e4e7")

    def _build_ui(self) -> None:
        """Constructs modern two-column desktop interface: Sidebar + Main Content Views."""
        # Top Container Split
        self.main_layout = ctk.CTkFrame(self, fg_color="#09090b")
        self.main_layout.pack(fill="both", expand=True)

        # 1. Left Sidebar Frame (Gemini style)
        self.sidebar_frame = ctk.CTkFrame(
            self.main_layout,
            width=240,
            fg_color="#121215",
            border_color="#27272a",
            border_width=1,
            corner_radius=0,
        )
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)

        self._build_sidebar()

        # 2. Right Container (Content Views)
        self.right_container = ctk.CTkFrame(self.main_layout, fg_color="#09090b", corner_radius=0)
        self.right_container.pack(side="right", fill="both", expand=True)

        # 3. Right Content Area Frame
        self.content_area = ctk.CTkFrame(self.right_container, fg_color="#09090b", corner_radius=0)
        self.content_area.pack(fill="both", expand=True)

        # 4. Create Views
        self._build_view_full_download()
        self._build_view_trimmer()
        self._build_view_history()
        self._build_view_settings()

        # Initial View Display
        self._switch_view("full_download")

    # =========================================================================
    # SIDEBAR COMPONENT (GEMINI-INSPIRED)
    # =========================================================================
    def _build_sidebar(self) -> None:
        """Assembles the left navigation sidebar with brand header, actions and status footer."""
        # Brand Header (System Brand Identity in Superior Esquerdo)
        brand_row = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        brand_row.pack(fill="x", padx=16, pady=(18, 14))

        # Logo on top left: Official Elo Track application icon
        icon_path = self._find_icon()
        app_icon_loaded = False
        if icon_path and icon_path.is_file():
            try:
                pil_img = Image.open(str(icon_path)).convert("RGBA")
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(32, 32))
                self._app_icon_img = ctk_img
                ctk.CTkLabel(brand_row, text="", image=ctk_img).pack(side="left", padx=(0, 10))
                app_icon_loaded = True
            except Exception:
                pass
        if not app_icon_loaded:
            ctk.CTkLabel(brand_row, text="⚡", font=ctk.CTkFont(size=20), text_color="#38bdf8").pack(side="left", padx=(0, 8))

        # Text Column: System Information only
        brand_text_col = ctk.CTkFrame(brand_row, fg_color="transparent")
        brand_text_col.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(
            brand_text_col,
            text="Elo Track",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#f4f4f5",
            anchor="w",
        ).pack(anchor="w")

        ctk.CTkLabel(
            brand_text_col,
            text=f"v{__version__} • Audio Studio",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#71717a",
            anchor="w",
        ).pack(anchor="w", pady=(1, 0))

        # Quick Action Button (+ Novo Download)
        quick_new_btn = ctk.CTkButton(
            self.sidebar_frame,
            text="+ Novo Download",
            height=38,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            text_color="#ffffff",
            command=self._on_quick_new_click,
        )
        quick_new_btn.pack(fill="x", padx=14, pady=(0, 16))

        # Navigation Section: MÓDULOS DE EXTRAÇÃO
        ctk.CTkLabel(
            self.sidebar_frame,
            text="MÓDULOS",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#71717a",
            anchor="w",
        ).pack(fill="x", padx=16, pady=(0, 6))

        self._create_nav_button("full_download", "⚡ Download Completo", "full_download")
        self._create_nav_button("trimmer", "✂️ Recorte & Player", "trimmer")
        self._create_nav_button("history", "🕒 Biblioteca & Histórico", "history")

        # Navigation Section: SISTEMA
        ctk.CTkLabel(
            self.sidebar_frame,
            text="SISTEMA",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#71717a",
            anchor="w",
        ).pack(fill="x", padx=16, pady=(18, 6))

        self._create_nav_button("settings", "⚙️ Configurações & Sobre", "settings")

        # Bottom Pinned Footer in Sidebar (Inferior Esquerdo: Lookup Labs Branding)
        sidebar_footer = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        sidebar_footer.pack(side="bottom", fill="x", padx=14, pady=16)

        lookup_box = ctk.CTkFrame(
            sidebar_footer,
            fg_color="#141417",
            border_color="#27272a",
            border_width=1,
            corner_radius=8,
        )
        lookup_box.pack(fill="x")

        lookup_inner = ctk.CTkFrame(lookup_box, fg_color="transparent")
        lookup_inner.pack(padx=10, pady=8, fill="x")

        logo_sm = self._find_lookup_logo("sm")
        if logo_sm and logo_sm.is_file():
            try:
                pil_img = Image.open(str(logo_sm)).convert("RGBA")
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(16, 16))
                self._lookup_logo_imgs.append(ctk_img)
                ctk.CTkLabel(lookup_inner, text="", image=ctk_img).pack(side="left", padx=(0, 8))
            except Exception:
                pass

        ctk.CTkLabel(
            lookup_inner,
            text="Lookup Labs",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            text_color="#a1a1aa",
        ).pack(side="left")

    def _create_nav_button(self, view_id: str, label: str, target_view: str) -> None:
        """Creates a modern rounded navigation button for the sidebar."""
        btn = ctk.CTkButton(
            self.sidebar_frame,
            text=label,
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="transparent",
            hover_color="#1e1e24",
            text_color="#a1a1aa",
            anchor="w",
            command=lambda: self._switch_view(target_view),
        )
        btn.pack(fill="x", padx=12, pady=(0, 4))
        self.nav_buttons[view_id] = btn

    def _switch_view(self, view_name: str) -> None:
        """Switches the active content view and updates sidebar highlight state."""
        self.active_view_name = view_name

        # Hide all views
        for v in self.views.values():
            v.pack_forget()

        # Show target view
        target_view = self.views.get(view_name)
        if target_view:
            target_view.pack(fill="both", expand=True)

        # Update sidebar styling
        for vid, btn in self.nav_buttons.items():
            if vid == view_name:
                btn.configure(fg_color="#1e293b", text_color="#f4f4f5")
            else:
                btn.configure(fg_color="transparent", text_color="#a1a1aa")

        # If switching to history, refresh its list
        if view_name == "history":
            self._refresh_history_ui()



    def _on_quick_new_click(self) -> None:
        """Action when clicking '+ Novo Download': switches to Full Download view and focuses URL."""
        self._switch_view("full_download")
        try:
            self.full_url_entry.focus_set()
        except Exception:
            pass

    # =========================================================================
    # REUSABLE FORMAT SELECTOR CARDS
    # =========================================================================
    def _create_format_cards_grid(self, parent_frame: ctk.CTkFrame) -> None:
        """Creates the 4-column format cards grid with ODS tags and interactive selection."""
        grid_row = ctk.CTkFrame(parent_frame, fg_color="transparent")
        grid_row.pack(fill="x", padx=16, pady=(0, 14))

        for idx, spec in enumerate(FORMAT_SPECS):
            f_id = spec["id"]
            is_selected = (f_id == self.selected_format)

            card = ctk.CTkFrame(
                grid_row,
                fg_color="#172554" if is_selected else "#09090b",
                border_color="#2563eb" if is_selected else "#27272a",
                border_width=2 if is_selected else 1,
                corner_radius=8,
            )
            card.pack(side="left", fill="both", expand=True, padx=(0 if idx == 0 else 6, 0))
            self.format_cards[f_id].append(card)

            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=8, pady=8)

            header_row = ctk.CTkFrame(inner, fg_color="transparent")
            header_row.pack(fill="x")

            lbl = ctk.CTkLabel(
                header_row,
                text=spec["label"],
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#60a5fa" if is_selected else "#e4e4e7",
            )
            lbl.pack(side="left")
            self.format_labels[f_id].append(lbl)

            tag_lbl = ctk.CTkLabel(
                header_row,
                text=spec["tag"],
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color=spec["tag_color"],
            )
            tag_lbl.pack(side="right")

            sub_lbl = ctk.CTkLabel(
                inner,
                text=spec["sublabel"],
                font=ctk.CTkFont(size=10),
                text_color="#a1a1aa",
                anchor="w",
            )
            sub_lbl.pack(fill="x", pady=(3, 0))

            # Bind selection click to all elements in this card
            for w in (card, inner, header_row, lbl, tag_lbl, sub_lbl):
                w.bind("<Button-1>", lambda e, val=f_id: self._select_format(val))

    # =========================================================================
    # VIEW 1: DOWNLOAD COMPLETO (FAST AUDIO EXTRACTION)
    # =========================================================================
    def _build_view_full_download(self) -> None:
        """Constructs dedicated view for downloading full audio tracks."""
        view = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent", corner_radius=0)
        self.views["full_download"] = view

        # Page Header
        hdr = ctk.CTkFrame(view, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 14))

        hdr_left = ctk.CTkFrame(hdr, fg_color="transparent")
        hdr_left.pack(side="left")

        ctk.CTkLabel(
            hdr_left,
            text="⚡ Download Completo de Áudio",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#f4f4f5",
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            hdr_left,
            text="Extraia faixas completas do YouTube na máxima fidelidade acústica disponível.",
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa",
            anchor="w",
        ).pack(fill="x", pady=(3, 0))

        # Sunset warning placeholder (only packed dynamically if sunset policy is triggered)
        self.sunset_banner_container = ctk.CTkFrame(view, fg_color="transparent", height=0)

        # Card 1: URL / Pesquisa Input
        self.full_url_card = ctk.CTkFrame(view, fg_color="#18181b", border_color="#27272a", border_width=1, corner_radius=12)
        self.full_url_card.pack(fill="x", padx=24, pady=(0, 12))
        url_card = self.full_url_card

        url_hdr = ctk.CTkFrame(url_card, fg_color="transparent")
        url_hdr.pack(fill="x", padx=16, pady=(14, 6))

        ctk.CTkLabel(url_hdr, text="LINK OU PESQUISA DE MÚSICA", font=ctk.CTkFont(size=11, weight="bold"), text_color="#a1a1aa").pack(side="left")
        ctk.CTkLabel(url_hdr, text="Cole o link ou digite o nome da música", font=ctk.CTkFont(size=11), text_color="#71717a").pack(side="right")

        input_row = ctk.CTkFrame(url_card, fg_color="transparent")
        input_row.pack(fill="x", padx=16, pady=(0, 14))

        self.full_url_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Cole o link do YouTube ou pesquise o nome da música...",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="#09090b",
            border_color="#27272a",
            corner_radius=8,
        )
        self.full_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.full_url_entry.bind("<Return>", lambda e: self._on_full_url_enter())

        self.full_search_btn = ctk.CTkButton(
            input_row,
            text="🔍 Pesquisar",
            width=96,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            text_color="#ffffff",
            corner_radius=8,
            command=self._on_full_search_click,
        )
        self.full_search_btn.pack(side="right")

        paste_btn = ctk.CTkButton(
            input_row,
            text="📋 Colar",
            width=78,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#27272a",
            hover_color="#3f3f46",
            text_color="#e4e4e7",
            corner_radius=8,
            command=lambda: self._paste_to_entry(self.full_url_entry),
        )
        paste_btn.pack(side="right", padx=(0, 8))

        # Dynamic Search Results Card
        self.search_results_container = ctk.CTkFrame(
            view,
            fg_color="#18181b",
            border_color="#2563eb",
            border_width=1,
            corner_radius=12,
        )

        # Card 2: Formatos de Áudio
        self.fmt_card = ctk.CTkFrame(view, fg_color="#18181b", border_color="#27272a", border_width=1, corner_radius=12)
        self.fmt_card.pack(fill="x", padx=24, pady=(0, 12))
        fmt_card = self.fmt_card

        fmt_hdr = ctk.CTkFrame(fmt_card, fg_color="transparent")
        fmt_hdr.pack(fill="x", padx=16, pady=(14, 8))
        ctk.CTkLabel(fmt_hdr, text="FORMATO DE EXPORTAÇÃO", font=ctk.CTkFont(size=11, weight="bold"), text_color="#a1a1aa").pack(side="left")
        ctk.CTkLabel(fmt_hdr, text="Selecione a fidelidade desejada", font=ctk.CTkFont(size=11), text_color="#71717a").pack(side="right")

        self._create_format_cards_grid(fmt_card)

        # Card 3: Pasta de Destino
        dest_card = ctk.CTkFrame(view, fg_color="#18181b", border_color="#27272a", border_width=1, corner_radius=12)
        dest_card.pack(fill="x", padx=24, pady=(0, 14))

        dest_hdr = ctk.CTkFrame(dest_card, fg_color="transparent")
        dest_hdr.pack(fill="x", padx=16, pady=(14, 8))
        ctk.CTkLabel(dest_hdr, text="PASTA DE SALVAMENTO", font=ctk.CTkFont(size=11, weight="bold"), text_color="#a1a1aa").pack(side="left")

        dest_row = ctk.CTkFrame(dest_card, fg_color="transparent")
        dest_row.pack(fill="x", padx=16, pady=(0, 14))

        self.full_dest_lbl = ctk.CTkLabel(
            dest_row,
            text=str(self.output_dir),
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color="#93c5fd",
            fg_color="#09090b",
            corner_radius=8,
            padx=12,
            height=38,
        )
        self.full_dest_lbl.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            dest_row,
            text="📁 Alterar...",
            width=90,
            height=38,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#27272a",
            hover_color="#3f3f46",
            text_color="#e4e4e7",
            corner_radius=8,
            command=self._browse_output_dir,
        ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            dest_row,
            text="📂 Abrir",
            width=76,
            height=38,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#27272a",
            hover_color="#3f3f46",
            text_color="#e4e4e7",
            corner_radius=8,
            command=self._open_output_dir,
        ).pack(side="right")

        # Action & Progress Card (Docked in view)
        action_card = ctk.CTkFrame(view, fg_color="#18181b", border_color="#27272a", border_width=1, corner_radius=12)
        action_card.pack(fill="x", padx=24, pady=(0, 20))

        self.download_btn = ctk.CTkButton(
            action_card,
            text="⚡ BAIXAR ÁUDIO COMPLETO",
            height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            text_color="#ffffff",
            command=lambda: self._start_download_from_view("full"),
        )
        self.download_btn.pack(fill="x", padx=16, pady=(16, 8))

        prog_hdr = ctk.CTkFrame(action_card, fg_color="transparent")
        prog_hdr.pack(fill="x", padx=16, pady=(0, 4))

        self.status_label = ctk.CTkLabel(prog_hdr, text="Pronto para iniciar.", font=ctk.CTkFont(size=12, weight="bold"), text_color="#f4f4f5", anchor="w")
        self.status_label.pack(side="left")

        self.progress_badge = ctk.CTkLabel(prog_hdr, text="Aguardando link", font=ctk.CTkFont(size=11), text_color="#a1a1aa")
        self.progress_badge.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(action_card, height=8, corner_radius=4, progress_color="#2563eb", fg_color="#27272a")
        self.progress_bar.pack(fill="x", padx=16, pady=(0, 6))
        self.progress_bar.set(0.0)

        self.details_label = ctk.CTkLabel(action_card, text="Cole uma URL acima e clique em Baixar.", font=ctk.CTkFont(size=11), text_color="#a1a1aa", anchor="w")
        self.details_label.pack(fill="x", padx=16, pady=(0, 14))

        # Result Card inside Action Card
        self.result_card = ctk.CTkFrame(action_card, fg_color="#052e16", border_color="#166534", border_width=1, corner_radius=8)
        res_inner = ctk.CTkFrame(self.result_card, fg_color="transparent")
        res_inner.pack(fill="x", padx=12, pady=8)

        self.result_text = ctk.CTkLabel(res_inner, text="", font=ctk.CTkFont(size=11, weight="bold"), text_color="#4ade80", anchor="w")
        self.result_text.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            res_inner,
            text="▶ Ouvir Faixa",
            width=90,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#15803d",
            hover_color="#16a34a",
            text_color="#ffffff",
            corner_radius=6,
            command=self._open_completed_file,
        ).pack(side="right")
        self.result_card.pack_forget()

    # =========================================================================
    # VIEW 2: RECORTE & PLAYER (AUDIO CUTTING STUDIO)
    # =========================================================================
    def _build_view_trimmer(self) -> None:
        """Constructs dedicated view for precision audio trimming and interactive playback."""
        view = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent", corner_radius=0)
        self.views["trimmer"] = view

        # Page Header
        hdr = ctk.CTkFrame(view, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 14))

        hdr_left = ctk.CTkFrame(hdr, fg_color="transparent")
        hdr_left.pack(side="left")

        ctk.CTkLabel(
            hdr_left,
            text="✂️ Estúdio de Recorte & Player",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#f4f4f5",
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            hdr_left,
            text="Ouça a música antecipadamente e marque com precisão cirúrgica os pontos de início e fim para download.",
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa",
            anchor="w",
        ).pack(fill="x", pady=(3, 0))

        # Card 1: URL & Preview Stream Fetcher
        url_card = ctk.CTkFrame(view, fg_color="#18181b", border_color="#27272a", border_width=1, corner_radius=12)
        url_card.pack(fill="x", padx=24, pady=(0, 12))

        ctk.CTkLabel(url_card, text="LINK OU PESQUISA DE MÚSICA", font=ctk.CTkFont(size=11, weight="bold"), text_color="#a1a1aa").pack(anchor="w", padx=16, pady=(14, 6))

        input_row = ctk.CTkFrame(url_card, fg_color="transparent")
        input_row.pack(fill="x", padx=16, pady=(0, 14))

        self.trim_url_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Cole o link do YouTube ou pesquise o nome da música...",
            height=40,
            font=ctk.CTkFont(size=13),
            fg_color="#09090b",
            border_color="#27272a",
            corner_radius=8,
        )
        self.trim_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.trim_url_entry.bind("<Return>", lambda e: self._on_trim_url_enter())

        self.fetch_preview_btn = ctk.CTkButton(
            input_row,
            text="🎧 Carregar",
            width=100,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            text_color="#ffffff",
            corner_radius=8,
            command=self._start_fetch_preview,
        )
        self.fetch_preview_btn.pack(side="right")

        self.trim_search_btn = ctk.CTkButton(
            input_row,
            text="🔍 Pesquisar",
            width=96,
            height=40,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#93c5fd",
            corner_radius=8,
            command=self._on_trim_search_click,
        )
        self.trim_search_btn.pack(side="right", padx=(0, 8))

        ctk.CTkButton(
            input_row,
            text="📋 Colar",
            width=70,
            height=40,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#27272a",
            hover_color="#3f3f46",
            text_color="#e4e4e7",
            corner_radius=8,
            command=lambda: self._paste_to_entry(self.trim_url_entry),
        ).pack(side="right", padx=(0, 8))

        # Dynamic Search Results Card for Trimmer
        self.trim_search_results_container = ctk.CTkFrame(
            view,
            fg_color="#18181b",
            border_color="#2563eb",
            border_width=1,
            corner_radius=12,
        )

        # Card 2: Interactive Player & Scrubber
        self.player_card = ctk.CTkFrame(view, fg_color="#18181b", border_color="#27272a", border_width=1, corner_radius=12)
        self.player_card.pack(fill="x", padx=24, pady=(0, 12))

        p_hdr = ctk.CTkFrame(self.player_card, fg_color="transparent")
        p_hdr.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(p_hdr, text="PLAYER DE AUDIÇÃO & NAVEGAÇÃO", font=ctk.CTkFont(size=11, weight="bold"), text_color="#a1a1aa").pack(side="left")
        self.track_title_label = ctk.CTkLabel(p_hdr, text="Nenhum áudio carregado", font=ctk.CTkFont(size=11), text_color="#71717a")
        self.track_title_label.pack(side="right")

        # Player Slider / Scrubber Row
        slider_box = ctk.CTkFrame(self.player_card, fg_color="#09090b", border_color="#27272a", border_width=1, corner_radius=8)
        slider_box.pack(fill="x", padx=16, pady=(0, 10))

        slider_inner = ctk.CTkFrame(slider_box, fg_color="transparent")
        slider_inner.pack(fill="x", padx=12, pady=10)

        self.time_label = ctk.CTkLabel(slider_inner, text="00:00 / 00:00", font=ctk.CTkFont(size=12, weight="bold"), text_color="#60a5fa", width=95)
        self.time_label.pack(side="left", padx=(0, 10))

        self.audio_slider = ctk.CTkSlider(
            slider_inner,
            from_=0,
            to=100,
            number_of_steps=1000,
            progress_color="#2563eb",
            button_color="#60a5fa",
            button_hover_color="#93c5fd",
            fg_color="#27272a",
        )
        self.audio_slider.pack(side="left", fill="x", expand=True)
        self.audio_slider.set(0)
        self.audio_slider.bind("<Button-1>", self._on_slider_start)
        self.audio_slider.bind("<B1-Motion>", self._on_slider_move)
        self.audio_slider.bind("<ButtonRelease-1>", self._on_slider_release)

        # Playback Controls Row
        ctrl_row = ctk.CTkFrame(self.player_card, fg_color="transparent")
        ctrl_row.pack(fill="x", padx=16, pady=(0, 14))

        self.play_btn = ctk.CTkButton(
            ctrl_row,
            text="▶ Tocar",
            width=90,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            corner_radius=6,
            command=self._toggle_player,
        )
        self.play_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = ctk.CTkButton(
            ctrl_row,
            text="⏹ Parar",
            width=80,
            height=34,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#27272a",
            hover_color="#3f3f46",
            text_color="#e4e4e7",
            corner_radius=6,
            command=self._stop_player,
        )
        self.stop_btn.pack(side="left")

        # Card 3: Marcadores de Início e Fim (A/B)
        marker_card = ctk.CTkFrame(view, fg_color="#18181b", border_color="#27272a", border_width=1, corner_radius=12)
        marker_card.pack(fill="x", padx=24, pady=(0, 12))

        m_hdr = ctk.CTkFrame(marker_card, fg_color="transparent")
        m_hdr.pack(fill="x", padx=16, pady=(14, 8))
        ctk.CTkLabel(m_hdr, text="PONTOS DE CORTE (INÍCIO & FIM)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#a1a1aa").pack(side="left")

        # Inputs and Marker Buttons
        m_row = ctk.CTkFrame(marker_card, fg_color="transparent")
        m_row.pack(fill="x", padx=16, pady=(0, 14))

        # Start Time Box
        start_col = ctk.CTkFrame(m_row, fg_color="transparent")
        start_col.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(start_col, text="Início do Trecho:", font=ctk.CTkFont(size=11), text_color="#a1a1aa", anchor="w").pack(fill="x", pady=(0, 2))
        self.start_entry = ctk.CTkEntry(start_col, placeholder_text="00:00 ou segs", height=36, fg_color="#09090b", border_color="#27272a", corner_radius=6)
        self.start_entry.pack(fill="x")
        ctk.CTkButton(
            start_col,
            text="⏱ Marcar Aqui [ Início ]",
            height=28,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#27272a",
            hover_color="#3f3f46",
            text_color="#38bdf8",
            corner_radius=6,
            command=self._mark_start_current,
        ).pack(fill="x", pady=(4, 0))

        # End Time Box
        end_col = ctk.CTkFrame(m_row, fg_color="transparent")
        end_col.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkLabel(end_col, text="Fim do Trecho:", font=ctk.CTkFont(size=11), text_color="#a1a1aa", anchor="w").pack(fill="x", pady=(0, 2))
        self.end_entry = ctk.CTkEntry(end_col, placeholder_text="02:30 ou segs", height=36, fg_color="#09090b", border_color="#27272a", corner_radius=6)
        self.end_entry.pack(fill="x")
        ctk.CTkButton(
            end_col,
            text="⏱ Marcar Aqui [ Fim ]",
            height=28,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color="#27272a",
            hover_color="#3f3f46",
            text_color="#38bdf8",
            corner_radius=6,
            command=self._mark_end_current,
        ).pack(fill="x", pady=(4, 0))

        # Test Actions Box
        test_col = ctk.CTkFrame(m_row, fg_color="transparent")
        test_col.pack(side="right", padx=(8, 0))
        ctk.CTkLabel(test_col, text="Ações de Teste:", font=ctk.CTkFont(size=11), text_color="#a1a1aa", anchor="w").pack(fill="x", pady=(0, 2))
        ctk.CTkButton(
            test_col,
            text="🎯 Testar Trecho",
            height=36,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#93c5fd",
            corner_radius=6,
            command=self._test_trimmed_audio,
        ).pack(fill="x")
        ctk.CTkButton(
            test_col,
            text="Limpar",
            height=28,
            font=ctk.CTkFont(size=10),
            fg_color="transparent",
            hover_color="#27272a",
            text_color="#71717a",
            command=self._clear_trim_inputs,
        ).pack(fill="x", pady=(4, 0))

        # Card 4: Formato & Botão de Baixar Trecho
        trim_act_card = ctk.CTkFrame(view, fg_color="#18181b", border_color="#27272a", border_width=1, corner_radius=12)
        trim_act_card.pack(fill="x", padx=24, pady=(0, 20))

        ctk.CTkLabel(trim_act_card, text="FORMATO DO RECORTE", font=ctk.CTkFont(size=11, weight="bold"), text_color="#a1a1aa").pack(anchor="w", padx=16, pady=(14, 8))
        self._create_format_cards_grid(trim_act_card)

        self.trim_download_btn = ctk.CTkButton(
            trim_act_card,
            text="✂️ BAIXAR E RECORTAR TRECHO",
            height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            text_color="#ffffff",
            command=lambda: self._start_download_from_view("trim"),
        )
        self.trim_download_btn.pack(fill="x", padx=16, pady=(4, 10))

        # Status & Progress Row (Inherited from Download Completo)
        trim_prog_hdr = ctk.CTkFrame(trim_act_card, fg_color="transparent")
        trim_prog_hdr.pack(fill="x", padx=16, pady=(0, 4))

        self.trim_status_label = ctk.CTkLabel(
            trim_prog_hdr,
            text="Pronto para iniciar.",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f4f4f5",
            anchor="w",
        )
        self.trim_status_label.pack(side="left")

        self.trim_progress_badge = ctk.CTkLabel(
            trim_prog_hdr,
            text="Aguardando recorte",
            font=ctk.CTkFont(size=11),
            text_color="#a1a1aa",
        )
        self.trim_progress_badge.pack(side="right")

        self.trim_progress_bar = ctk.CTkProgressBar(
            trim_act_card,
            height=8,
            corner_radius=4,
            progress_color="#2563eb",
            fg_color="#27272a",
        )
        self.trim_progress_bar.pack(fill="x", padx=16, pady=(0, 6))
        self.trim_progress_bar.set(0.0)

        self.trim_details_label = ctk.CTkLabel(
            trim_act_card,
            text="Defina os pontos de início e fim e clique em Baixar e Recortar.",
            font=ctk.CTkFont(size=11),
            text_color="#a1a1aa",
            anchor="w",
        )
        self.trim_details_label.pack(fill="x", padx=16, pady=(0, 14))

        # Result Card inside Trim Action Card
        self.trim_result_card = ctk.CTkFrame(
            trim_act_card,
            fg_color="#052e16",
            border_color="#166534",
            border_width=1,
            corner_radius=8,
        )
        trim_res_inner = ctk.CTkFrame(self.trim_result_card, fg_color="transparent")
        trim_res_inner.pack(fill="x", padx=12, pady=8)

        self.trim_result_text = ctk.CTkLabel(
            trim_res_inner,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#4ade80",
            anchor="w",
        )
        self.trim_result_text.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkButton(
            trim_res_inner,
            text="▶ Ouvir Recorte",
            width=110,
            height=26,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#15803d",
            hover_color="#16a34a",
            text_color="#ffffff",
            corner_radius=6,
            command=self._open_completed_file,
        ).pack(side="right")
        self.trim_result_card.pack_forget()

    # =========================================================================
    # VIEW 3: BIBLIOTECA & HISTÓRICO
    # =========================================================================
    def _build_view_history(self) -> None:
        """Constructs dedicated library view displaying downloaded audio history with playback."""
        view = ctk.CTkFrame(self.content_area, fg_color="transparent", corner_radius=0)
        self.views["history"] = view

        # Page Header & Controls Row
        hdr = ctk.CTkFrame(view, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 14))

        hdr_left = ctk.CTkFrame(hdr, fg_color="transparent")
        hdr_left.pack(side="left")

        ctk.CTkLabel(
            hdr_left,
            text="🕒 Biblioteca de Downloads",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#f4f4f5",
            anchor="w",
        ).pack(fill="x")

        self.history_count_badge = ctk.CTkLabel(
            hdr_left,
            text="0 faixas baixadas",
            font=ctk.CTkFont(size=12),
            text_color="#a1a1aa",
            anchor="w",
        )
        self.history_count_badge.pack(fill="x", pady=(2, 0))

        hdr_right = ctk.CTkFrame(hdr, fg_color="transparent")
        hdr_right.pack(side="right")

        self.sync_disk_btn = ctk.CTkButton(
            hdr_right,
            text="🔄 Sincronizar Disco",
            height=34,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#93c5fd",
            corner_radius=8,
            command=self._sync_history_with_disk,
        )
        self.sync_disk_btn.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            hdr_right,
            text="📂 Abrir Pasta",
            height=34,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#27272a",
            hover_color="#3f3f46",
            text_color="#e4e4e7",
            corner_radius=8,
            command=self._open_output_dir,
        ).pack(side="left", padx=(0, 8))

        self.clear_history_btn = ctk.CTkButton(
            hdr_right,
            text="🗑️ Limpar Histórico",
            height=34,
            font=ctk.CTkFont(size=11),
            fg_color="#450a0a",
            hover_color="#7f1d1d",
            text_color="#fca5a5",
            corner_radius=8,
            command=self._clear_history,
        )
        self.clear_history_btn.pack(side="left")

        # Search & Filter Bar
        filter_card = ctk.CTkFrame(view, fg_color="#18181b", border_color="#27272a", border_width=1, corner_radius=10)
        filter_card.pack(fill="x", padx=24, pady=(0, 10))

        f_inner = ctk.CTkFrame(filter_card, fg_color="transparent")
        f_inner.pack(fill="x", padx=12, pady=7)

        ctk.CTkLabel(f_inner, text="🔍", font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 8))

        self.history_filter_entry = ctk.CTkEntry(
            f_inner,
            placeholder_text="Filtrar biblioteca por música, artista ou formato...",
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="#09090b",
            border_color="#27272a",
            corner_radius=6,
        )
        self.history_filter_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.history_filter_entry.bind("<KeyRelease>", lambda e: self._on_history_filter_change())

        self.history_clear_filter_btn = ctk.CTkButton(
            f_inner,
            text="✕ Limpar",
            width=68,
            height=32,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color="#27272a",
            text_color="#a1a1aa",
            command=self._clear_history_filter,
        )
        self.history_clear_filter_btn.pack(side="right")

        # Scrollable List Frame
        self.history_scroll = ctk.CTkScrollableFrame(view, fg_color="transparent", corner_radius=0)
        self.history_scroll.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        self._refresh_history_ui()

    def _on_history_filter_change(self) -> None:
        """Triggered on text input in history filter bar."""
        self._refresh_history_ui()

    def _clear_history_filter(self) -> None:
        """Clears the history filter entry and re-renders full library."""
        if hasattr(self, "history_filter_entry"):
            self.history_filter_entry.delete(0, "end")
        self._refresh_history_ui()

    def _sync_history_with_disk(self) -> None:
        """Scans library records against physical disk and purges moved/deleted files."""
        removed = self.history_service.prune_missing_files()
        self._refresh_history_ui()
        if removed > 0:
            msg = f"✓ Sincronizado: {removed} registro(s) ausente(s) removido(s) da biblioteca."
            color = "#4ade80"
        else:
            msg = "✓ Sincronizado: Todos os arquivos da biblioteca continuam no disco!"
            color = "#60a5fa"
        if hasattr(self, "history_count_badge"):
            self.history_count_badge.configure(text=msg, text_color=color)

    def _refresh_history_ui(self) -> None:
        """Renders list items inside the history library view grouped by song/music."""
        if not hasattr(self, "history_scroll"):
            return

        for w in self.history_scroll.winfo_children():
            w.destroy()

        self._history_play_btns.clear()

        filter_q = self.history_filter_entry.get().strip() if hasattr(self, "history_filter_entry") else ""
        groups = self.history_service.get_grouped_items(limit=100, filter_text=filter_q)
        total_files = sum(len(g["items"]) for g in groups)
        missing_count = self.history_service.get_missing_files_count()

        if hasattr(self, "history_count_badge"):
            if not groups and not filter_q:
                count_text = "0 faixas baixadas"
                color = "#a1a1aa"
            elif filter_q:
                m_word = "música encontrada" if len(groups) == 1 else "músicas encontradas"
                count_text = f"Filtrando: {len(groups)} {m_word} para \"{filter_q}\""
                color = "#93c5fd"
            else:
                m_word = "música" if len(groups) == 1 else "músicas"
                f_word = "arquivo" if total_files == 1 else "arquivos"
                count_text = f"{len(groups)} {m_word} ({total_files} {f_word} salvos)"
                if missing_count > 0:
                    count_text += f"   •   ⚠️ {missing_count} ausente(s) no disco"
                color = "#a1a1aa" if missing_count == 0 else "#fbbf24"
            self.history_count_badge.configure(text=count_text, text_color=color)

        if not groups:
            empty_card = ctk.CTkFrame(self.history_scroll, fg_color="#18181b", border_color="#27272a", border_width=1, corner_radius=12)
            empty_card.pack(fill="x", pady=20)
            if filter_q:
                ctk.CTkLabel(
                    empty_card,
                    text=f"Nenhuma música encontrada para \"{filter_q}\".\nTente buscar por outro termo ou limpe o filtro.",
                    font=ctk.CTkFont(size=13),
                    text_color="#71717a",
                    justify="center",
                ).pack(padx=20, pady=40)
            else:
                ctk.CTkLabel(
                    empty_card,
                    text="Sua biblioteca de downloads está vazia.\nAs músicas baixadas aparecerão agrupadas aqui com seus diferentes formatos e recortes.",
                    font=ctk.CTkFont(size=13),
                    text_color="#71717a",
                    justify="center",
                ).pack(padx=20, pady=40)
            if hasattr(self, "clear_history_btn"):
                self.clear_history_btn.configure(state="disabled")
            return

        if hasattr(self, "clear_history_btn"):
            self.clear_history_btn.configure(state="normal")

        badge_colors = {
            "mp3": ("#2563eb", "#172554"),
            "wav": ("#38bdf8", "#082f49"),
            "flac": ("#c084fc", "#3b0764"),
            "m4a": ("#4ade80", "#052e16"),
        }

        for group in groups:
            group_card = ctk.CTkFrame(
                self.history_scroll,
                fg_color="#18181b",
                border_color="#27272a",
                border_width=1,
                corner_radius=12,
            )
            group_card.pack(fill="x", pady=(0, 12))

            # Group Header Row: Thumbnail, Title, Artist, Version Count, Quick Actions
            ghdr = ctk.CTkFrame(group_card, fg_color="transparent")
            ghdr.pack(fill="x", padx=14, pady=(12, 10))

            # 1. Group Thumbnail
            thumb_container = ctk.CTkFrame(ghdr, width=54, height=54, fg_color="#27272a", corner_radius=8)
            thumb_container.pack_propagate(False)
            thumb_container.pack(side="left", padx=(0, 12))

            thumb_label = ctk.CTkLabel(thumb_container, text="🎵", font=ctk.CTkFont(size=20), text_color="#71717a")
            thumb_label.place(relx=0.5, rely=0.5, anchor="center")

            representative_item = group["items"][0]
            self._load_item_thumbnail(representative_item, thumb_label)

            # 2. Group Title & Meta
            ginfo = ctk.CTkFrame(ghdr, fg_color="transparent")
            ginfo.pack(side="left", fill="x", expand=True)

            title_txt = group["title"] if len(group["title"]) <= 50 else group["title"][:47] + "..."
            ctk.CTkLabel(
                ginfo,
                text=title_txt,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color="#f4f4f5",
                anchor="w",
            ).pack(anchor="w")

            gmeta_row = ctk.CTkFrame(ginfo, fg_color="transparent")
            gmeta_row.pack(anchor="w", pady=(3, 0))

            artist_txt = group["artist"] if group["artist"] != "YouTube" else "YouTube"
            ctk.CTkLabel(
                gmeta_row,
                text=artist_txt,
                font=ctk.CTkFont(size=11),
                text_color="#a1a1aa",
                anchor="w",
            ).pack(side="left", padx=(0, 8))

            num_vers = len(group["items"])
            v_badge_text = f"{num_vers} {'versão salva' if num_vers == 1 else 'versões salvas'}"
            ctk.CTkLabel(
                gmeta_row,
                text=v_badge_text,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#38bdf8",
                fg_color="#082f49",
                corner_radius=4,
                padx=6,
                pady=1,
            ).pack(side="left")

            # 3. Quick Actions in Group Header
            group_url = group["url"]
            if group_url:
                g_acts = ctk.CTkFrame(ghdr, fg_color="transparent")
                g_acts.pack(side="right")

                existing_formats = {it.format.lower() for it in group["items"] if not it.is_trim}
                for spec in FORMAT_SPECS:
                    spec_fmt = spec["label"].lower()
                    if spec_fmt not in existing_formats:
                        ctk.CTkButton(
                            g_acts,
                            text=f"+ {spec['label']}",
                            height=24,
                            width=56,
                            font=ctk.CTkFont(size=10, weight="bold"),
                            fg_color="#27272a",
                            hover_color="#3f3f46",
                            text_color="#e4e4e7",
                            corner_radius=6,
                            command=lambda u=group_url, fid=spec["id"]: self._redownload_from_history(u, fid),
                        ).pack(side="left", padx=(0, 4))

                ctk.CTkButton(
                    g_acts,
                    text="✂️ Recortar",
                    height=24,
                    font=ctk.CTkFont(size=10, weight="bold"),
                    fg_color="#1e293b",
                    hover_color="#334155",
                    text_color="#93c5fd",
                    corner_radius=6,
                    command=lambda u=group_url: self._open_in_trimmer(u),
                ).pack(side="left", padx=(2, 0))

            # Sub-items Container (Individual File Rows for this Song)
            sub_container = ctk.CTkFrame(group_card, fg_color="transparent")
            sub_container.pack(fill="x", padx=14, pady=(0, 10))

            for it in group["items"]:
                self._render_history_sub_item(sub_container, it, badge_colors)

    def _render_history_sub_item(self, parent: ctk.CTkFrame, item: HistoryItem, badge_colors: dict) -> None:
        """Renders an individual audio file row within a song group with disk sync detection."""
        file_on_disk = item.file_exists

        row = ctk.CTkFrame(
            parent,
            fg_color="#181113" if not file_on_disk else "#121215",
            border_color="#7f1d1d" if not file_on_disk else "#27272a",
            border_width=1,
            corner_radius=8,
        )
        row.pack(fill="x", pady=(0, 5))

        inner = ctk.CTkFrame(row, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=7)

        # Left Info: Badges & Metadata
        left_col = ctk.CTkFrame(inner, fg_color="transparent")
        left_col.pack(side="left", fill="x", expand=True)

        meta_line = ctk.CTkFrame(left_col, fg_color="transparent")
        meta_line.pack(fill="x")

        # Format Badge
        fg_col, bg_col = badge_colors.get(item.format.lower(), ("#94a3b8", "#1e293b"))
        ctk.CTkLabel(
            meta_line,
            text=item.format.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=fg_col if file_on_disk else "#71717a",
            fg_color=bg_col if file_on_disk else "#27272a",
            corner_radius=4,
            width=42,
            height=20,
        ).pack(side="left", padx=(0, 6))

        # Trim vs Full Audio Badge
        if item.is_trim:
            type_txt = "✂️ Recorte"
            type_fg = "#38bdf8"
            type_bg = "#082f49"
        else:
            type_txt = "⚡ Áudio Completo"
            type_fg = "#4ade80"
            type_bg = "#052e16"

        ctk.CTkLabel(
            meta_line,
            text=type_txt,
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=type_fg if file_on_disk else "#71717a",
            fg_color=type_bg if file_on_disk else "#18181b",
            corner_radius=4,
            padx=6,
            height=20,
        ).pack(side="left", padx=(0, 8))

        # File stats or Missing Alert
        stat_parts = []
        if item.duration_seconds:
            stat_parts.append(item.formatted_duration)
        if item.file_size_bytes > 0:
            stat_parts.append(item.formatted_size)
        file_name = Path(item.file_path).name
        stat_parts.append(file_name)

        stat_str = " • ".join(stat_parts)

        if not file_on_disk:
            ctk.CTkLabel(
                meta_line,
                text="⚠️ Arquivo movido ou excluído do disco",
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color="#fca5a5",
                fg_color="#450a0a",
                corner_radius=4,
                padx=6,
                height=20,
            ).pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            meta_line,
            text=stat_str,
            font=ctk.CTkFont(size=11),
            text_color="#71717a" if not file_on_disk else "#a1a1aa",
            anchor="w",
        ).pack(side="left")

        # Right Action Buttons
        btn_col = ctk.CTkFrame(inner, fg_color="transparent")
        btn_col.pack(side="right")

        if file_on_disk:
            is_this_playing = (self._playing_history_id == item.id and self.player_service.is_playing)
            play_btn = ctk.CTkButton(
                btn_col,
                text="⏹ Parar" if is_this_playing else "▶ Tocar",
                width=68,
                height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#dc2626" if is_this_playing else "#2563eb",
                hover_color="#b91c1c" if is_this_playing else "#1d4ed8",
                text_color="#ffffff",
                corner_radius=6,
                command=lambda i=item: self._toggle_play_history(i),
            )
            play_btn.pack(side="left", padx=(0, 6))
            self._history_play_btns[item.id] = play_btn

            ctk.CTkButton(
                btn_col,
                text="📁 Abrir",
                width=62,
                height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="#27272a",
                hover_color="#3f3f46",
                text_color="#e4e4e7",
                corner_radius=6,
                command=lambda p=item.file_path: self._open_in_explorer(p),
            ).pack(side="left", padx=(0, 6))

            ctk.CTkButton(
                btn_col,
                text="✕",
                width=26,
                height=26,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color="transparent",
                hover_color="#27272a",
                text_color="#71717a",
                corner_radius=6,
                command=lambda i_id=item.id: self._remove_history_item(i_id),
            ).pack(side="left")
        else:
            ctk.CTkButton(
                btn_col,
                text="🗑️ Limpar Registro",
                width=115,
                height=26,
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color="#450a0a",
                hover_color="#7f1d1d",
                text_color="#fca5a5",
                corner_radius=6,
                command=lambda i_id=item.id: self._remove_history_item(i_id),
            ).pack(side="left")

    # =========================================================================
    # VIEW 4: CONFIGURAÇÕES & SOBRE (SETTINGS)
    # =========================================================================
    def _build_view_settings(self) -> None:
        """Constructs settings view for output directories, diagnostics, and version lifecycle."""
        view = ctk.CTkScrollableFrame(self.content_area, fg_color="transparent", corner_radius=0)
        self.views["settings"] = view

        # Page Header
        hdr = ctk.CTkFrame(view, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 14))

        hdr_left = ctk.CTkFrame(hdr, fg_color="transparent")
        hdr_left.pack(side="left")

        ctk.CTkLabel(hdr_left, text="⚙️ Configurações & Sistema", font=ctk.CTkFont(size=22, weight="bold"), text_color="#f4f4f5", anchor="w").pack(fill="x")
        ctk.CTkLabel(hdr_left, text="Gerencie caminhos padrão, diagnóstico do ambiente e ciclo de vida do Elo Track.", font=ctk.CTkFont(size=12), text_color="#a1a1aa", anchor="w").pack(fill="x", pady=(3, 0))

        # Card 1: Diretório de Destino Padrão
        dir_card = ctk.CTkFrame(view, fg_color="#18181b", border_color="#27272a", border_width=1, corner_radius=12)
        dir_card.pack(fill="x", padx=24, pady=(0, 14))

        ctk.CTkLabel(dir_card, text="PASTA PADRÃO DE DOWNLOAD", font=ctk.CTkFont(size=11, weight="bold"), text_color="#a1a1aa").pack(anchor="w", padx=16, pady=(14, 6))

        d_row = ctk.CTkFrame(dir_card, fg_color="transparent")
        d_row.pack(fill="x", padx=16, pady=(0, 14))

        self.settings_dest_lbl = ctk.CTkLabel(
            d_row,
            text=str(self.output_dir),
            anchor="w",
            font=ctk.CTkFont(size=12),
            text_color="#93c5fd",
            fg_color="#09090b",
            corner_radius=8,
            padx=12,
            height=38,
        )
        self.settings_dest_lbl.pack(side="left", fill="x", expand=True, padx=(0, 10))

        ctk.CTkButton(
            d_row,
            text="📁 Alterar...",
            width=90,
            height=38,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#27272a",
            hover_color="#3f3f46",
            text_color="#e4e4e7",
            corner_radius=8,
            command=self._browse_output_dir,
        ).pack(side="right")

        # Card 2: Diagnóstico FFmpeg
        ff_card = ctk.CTkFrame(view, fg_color="#18181b", border_color="#27272a", border_width=1, corner_radius=12)
        ff_card.pack(fill="x", padx=24, pady=(0, 14))

        ctk.CTkLabel(ff_card, text="MOTOR DE PROCESSAMENTO DE ÁUDIO (FFMPEG)", font=ctk.CTkFont(size=11, weight="bold"), text_color="#a1a1aa").pack(anchor="w", padx=16, pady=(14, 6))

        ffmpeg_detected = EnvironmentValidator.get_ffmpeg_path()
        ff_row = ctk.CTkFrame(ff_card, fg_color="#09090b", border_color="#27272a", border_width=1, corner_radius=8)
        ff_row.pack(fill="x", padx=16, pady=(0, 14))

        ff_inner = ctk.CTkFrame(ff_row, fg_color="transparent")
        ff_inner.pack(fill="x", padx=12, pady=10)

        status_text = "● FFmpeg Integrado e Operacional" if ffmpeg_detected else "✖ FFmpeg Ausente"
        status_color = "#4ade80" if ffmpeg_detected else "#f87171"
        ctk.CTkLabel(ff_inner, text=status_text, font=ctk.CTkFont(size=12, weight="bold"), text_color=status_color).pack(anchor="w")

        loc_text = str(ffmpeg_detected) if ffmpeg_detected else "Nenhum binário do FFmpeg foi localizado."
        ctk.CTkLabel(ff_inner, text=f"Localização: {loc_text}", font=ctk.CTkFont(size=11), text_color="#a1a1aa").pack(anchor="w", pady=(2, 0))

        # Card 3: Versão e Informações do Produto
        ver_card = ctk.CTkFrame(view, fg_color="#18181b", border_color="#27272a", border_width=1, corner_radius=12)
        ver_card.pack(fill="x", padx=24, pady=(0, 20))

        ctk.CTkLabel(ver_card, text="INFORMAÇÕES DO PRODUTO & LICENCIAMENTO", font=ctk.CTkFont(size=11, weight="bold"), text_color="#a1a1aa").pack(anchor="w", padx=16, pady=(14, 6))

        v_inner = ctk.CTkFrame(ver_card, fg_color="transparent")
        v_inner.pack(fill="x", padx=16, pady=(0, 16))

        # Brand row with large Lookup Labs badge
        b_row = ctk.CTkFrame(v_inner, fg_color="transparent")
        b_row.pack(fill="x", pady=(0, 10))

        logo_lg = self._find_lookup_logo("lg")
        if logo_lg and logo_lg.is_file():
            try:
                pil_img = Image.open(str(logo_lg)).convert("RGBA")
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(52, 52))
                self._lookup_logo_imgs.append(ctk_img)
                ctk.CTkLabel(b_row, text="", image=ctk_img).pack(side="left", padx=(0, 14))
            except Exception:
                pass

        v_text_col = ctk.CTkFrame(b_row, fg_color="transparent")
        v_text_col.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(v_text_col, text="Elo Track Desktop", font=ctk.CTkFont(size=16, weight="bold"), text_color="#f4f4f5").pack(anchor="w")
        ctk.CTkLabel(v_text_col, text=f"Versão Instalada: v{__version__} • Publicado por Lookup Labs", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38bdf8").pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(v_text_col, text="Lookup Labs • Engenharia de Software e Produtos Digitais", font=ctk.CTkFont(size=11), text_color="#a1a1aa").pack(anchor="w", pady=(2, 0))

        ctk.CTkLabel(
            v_inner,
            text="Projetado para extração e separação acústica profissional de faixas com inteligência artificial (Moises / Demucs / DAWs).",
            font=ctk.CTkFont(size=11),
            text_color="#71717a",
            wraplength=640,
            justify="left",
        ).pack(anchor="w")

    # =========================================================================
    # LOGIC, VALIDATION & WORKERS
    # =========================================================================
    def _check_dependencies(self) -> None:
        """Verifies FFmpeg presence silently."""
        ffmpeg_path = EnvironmentValidator.get_ffmpeg_path()
        self.is_ffmpeg_ready = bool(ffmpeg_path)

    def _check_version_lifecycle(self) -> None:
        """Verifies whether this installed version has been sunset/deprecated by policy."""
        try:
            res = self.version_service.check_status()
            if res.is_blocked:
                self.is_version_blocked = True
                self.download_btn.configure(
                    state="disabled",
                    text="🚫 VERSÃO DESCONTINUADA - ATUALIZAÇÃO OBRIGATÓRIA",
                    fg_color="#7f1d1d",
                    hover_color="#7f1d1d",
                )
                self.trim_download_btn.configure(
                    state="disabled",
                    text="🚫 VERSÃO DESCONTINUADA",
                    fg_color="#7f1d1d",
                )
                self.status_label.configure(text="✖ Versão descontinuada pela Lookup Labs.", text_color="#f87171")
                self.progress_badge.configure(text="Obsoleta", text_color="#f87171")
                self.details_label.configure(text="Esta versão antiga não possui mais permissão para realizar downloads.")

                # Show Sunset Card in full download view
                if hasattr(self, "full_url_card"):
                    self.sunset_banner_container.pack(fill="x", padx=24, pady=(0, 12), before=self.full_url_card)
                else:
                    self.sunset_banner_container.pack(fill="x", padx=24, pady=(0, 12))
                sunset_card = ctk.CTkFrame(self.sunset_banner_container, fg_color="#450a0a", border_color="#ef4444", border_width=2, corner_radius=12)
                sunset_card.pack(fill="x")

                c_in = ctk.CTkFrame(sunset_card, fg_color="transparent")
                c_in.pack(fill="x", padx=16, pady=14)

                ctk.CTkLabel(c_in, text=f"🚫 ATUALIZAÇÃO OBRIGATÓRIA (v{__version__})", font=ctk.CTkFont(size=14, weight="bold"), text_color="#fca5a5", anchor="w").pack(fill="x")
                ctk.CTkLabel(c_in, text=res.message, font=ctk.CTkFont(size=11), text_color="#fecaca", justify="left", wraplength=640, anchor="w").pack(fill="x", pady=(6, 12))

                ctk.CTkButton(
                    c_in,
                    text="📥 BAIXAR NOVO INSTALADOR OFICIAL",
                    height=36,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    fg_color="#dc2626",
                    hover_color="#b91c1c",
                    text_color="#ffffff",
                    corner_radius=8,
                    command=lambda u=res.download_url: webbrowser.open(u),
                ).pack(anchor="w")

        except Exception:
            pass

    def _paste_to_entry(self, entry_widget: ctk.CTkEntry) -> None:
        """Pastes clipboard text into the specified entry widget."""
        try:
            clipboard = self.clipboard_get().strip()
            entry_widget.delete(0, "end")
            entry_widget.insert(0, clipboard)
        except Exception:
            pass

    def _browse_output_dir(self) -> None:
        """Opens folder dialog to pick destination."""
        chosen = ctk.filedialog.askdirectory(initialdir=str(self.output_dir))
        if chosen:
            self.output_dir = Path(chosen).resolve()
            if hasattr(self, "full_dest_lbl"):
                self.full_dest_lbl.configure(text=str(self.output_dir))
            if hasattr(self, "settings_dest_lbl"):
                self.settings_dest_lbl.configure(text=str(self.output_dir))

    def _open_output_dir(self) -> None:
        """Opens output folder in system file explorer."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(self.output_dir))
        else:
            subprocess.run(["xdg-open", str(self.output_dir)])

    def _open_completed_file(self) -> None:
        """Opens the last extracted audio track with the default system player."""
        if self.last_downloaded_file and self.last_downloaded_file.exists():
            if os.name == "nt":
                os.startfile(str(self.last_downloaded_file))
            else:
                subprocess.run(["xdg-open", str(self.last_downloaded_file)])

    def _clear_history(self) -> None:
        """Clears all records from download history."""
        self.history_service.clear()
        if self._playing_history_id:
            self.player_service.stop()
            self._playing_history_id = None
        self._refresh_history_ui()



    def _remove_history_item(self, item_id: str) -> None:
        """Removes a specific record from download history."""
        if self._playing_history_id == item_id:
            self.player_service.stop()
            self._playing_history_id = None
        self.history_service.remove_item(item_id)
        self._refresh_history_ui()



    def _open_in_explorer(self, file_path_str: str) -> None:
        """Opens Windows Explorer and highlights the file."""
        path = Path(file_path_str)
        if not path.exists():
            return
        if os.name == "nt":
            subprocess.Popen(f'explorer /select,"{path.resolve()}"')
        else:
            subprocess.Popen(["xdg-open", str(path.parent)])

    def _toggle_play_history(self, item: HistoryItem) -> None:
        """Plays or stops playback of a specific history item with instant in-place button toggle."""
        path = item.path_obj
        if not path.exists():
            return

        old_playing_id = self._playing_history_id

        if self._playing_history_id == item.id and self.player_service.is_playing:
            self.player_service.stop()
            self._playing_history_id = None
        else:
            self.player_service.stop()
            if self.player_service.load(path, duration=item.duration_seconds or 0.0):
                self.player_service.play(0.0)
                self._playing_history_id = item.id

        # Update button visual states directly without destroying list widgets
        if old_playing_id and old_playing_id in self._history_play_btns:
            btn = self._history_play_btns[old_playing_id]
            try:
                if btn.winfo_exists():
                    btn.configure(text="▶ Tocar", fg_color="#2563eb", hover_color="#1d4ed8")
            except Exception:
                pass

        if self._playing_history_id and self._playing_history_id in self._history_play_btns:
            btn = self._history_play_btns[self._playing_history_id]
            try:
                if btn.winfo_exists():
                    btn.configure(text="⏹ Parar", fg_color="#dc2626", hover_color="#b91c1c")
            except Exception:
                pass

    def _create_thumbnail_ctk_image(self, file_path_or_bytes, size: Tuple[int, int] = (54, 54)) -> ctk.CTkImage:
        """Generates a rounded CTkImage from image bytes or file path."""
        if isinstance(file_path_or_bytes, (str, Path)):
            img = Image.open(str(file_path_or_bytes)).convert("RGBA")
        else:
            img = Image.open(io.BytesIO(file_path_or_bytes)).convert("RGBA")

        fitted = ImageOps.fit(img, size, Image.Resampling.LANCZOS)
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), size], radius=6, fill=255)
        fitted.putalpha(mask)
        return ctk.CTkImage(light_image=fitted, dark_image=fitted, size=size)

    def _get_thumbnail_image(self, item: HistoryItem) -> Optional[ctk.CTkImage]:
        """Returns cached CTkImage for history item if already in RAM or on disk."""
        if item.id in self._thumbnail_cache:
            return self._thumbnail_cache[item.id]

        local_path = item.get_cached_thumbnail_path()
        if local_path and local_path.is_file():
            try:
                ctk_img = self._create_thumbnail_ctk_image(local_path)
                self._thumbnail_cache[item.id] = ctk_img
                return ctk_img
            except Exception as exc:
                logger.debug("Falha ao carregar thumbnail local (%s): %s", local_path, exc)

        return None

    def _load_item_thumbnail(self, item: HistoryItem, label: ctk.CTkLabel) -> None:
        """Sets thumbnail image on label, fetching asynchronously in background if needed."""
        cached_img = self._get_thumbnail_image(item)
        if cached_img:
            label.configure(image=cached_img, text="")
            return

        label.configure(image=None, text="🎵", text_color="#71717a")

        thumb_url = item.thumbnail_url
        if not thumb_url or item.id in self._fetching_thumbnails:
            return

        self._fetching_thumbnails.add(item.id)

        def _worker() -> None:
            try:
                req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    raw_bytes = resp.read()

                if raw_bytes:
                    thumb_dir = Path.home() / ".elotrack" / "thumbnails"
                    thumb_dir.mkdir(parents=True, exist_ok=True)
                    cache_file = thumb_dir / f"{item.id}.jpg"
                    cache_file.write_bytes(raw_bytes)

                    ctk_img = self._create_thumbnail_ctk_image(raw_bytes)
                    self._thumbnail_cache[item.id] = ctk_img

                    def _ui_update() -> None:
                        try:
                            if label.winfo_exists():
                                label.configure(image=ctk_img, text="")
                        except Exception:
                            pass

                    self.after(0, _ui_update)
            except Exception as exc:
                logger.debug("Falha no download assíncrono da miniatura (%s): %s", item.id, exc)
            finally:
                self._fetching_thumbnails.discard(item.id)

        threading.Thread(target=_worker, daemon=True).start()

    def _redownload_from_history(self, url: str, format_id: str) -> None:
        """Switches to Full Download, pre-fills URL and format, and starts download immediately."""
        if not url:
            return
        self._switch_view("full_download")
        if hasattr(self, "full_url_entry"):
            self.full_url_entry.delete(0, "end")
            self.full_url_entry.insert(0, url)
        self._select_format(format_id)
        self._start_download_from_view("full")

    def _open_in_trimmer(self, url: str) -> None:
        """Switches to Trimmer view, pre-fills URL, and starts fetching preview audio."""
        if not url:
            return
        self._switch_view("trimmer")
        if hasattr(self, "trim_url_entry"):
            self.trim_url_entry.delete(0, "end")
            self.trim_url_entry.insert(0, url)
        self._start_fetch_preview()



    # =========================================================================
    # YOUTUBE SEARCH INTEGRATION
    # =========================================================================
    def _on_full_url_enter(self) -> None:
        """Called when user presses Enter inside full_url_entry."""
        text = self.full_url_entry.get().strip()
        if not text:
            return
        if text.startswith(("http://", "https://")):
            self._start_download_from_view("full")
        else:
            self._on_full_search_click()

    def _on_trim_url_enter(self) -> None:
        """Called when user presses Enter inside trim_url_entry."""
        text = self.trim_url_entry.get().strip()
        if not text:
            return
        if text.startswith(("http://", "https://")):
            self._start_fetch_preview()
        else:
            self._on_trim_search_click()

    def _on_full_search_click(self) -> None:
        query = self.full_url_entry.get().strip()
        if not query:
            return
        if query.startswith(("http://", "https://")):
            self._start_download_from_view("full")
            return
        self._start_search(query, target_view="full")

    def _on_trim_search_click(self) -> None:
        query = self.trim_url_entry.get().strip()
        if not query:
            return
        if query.startswith(("http://", "https://")):
            self._start_fetch_preview()
            return
        self._start_search(query, target_view="trim")

    def _start_search(self, query: str, target_view: str = "full") -> None:
        if self.is_searching:
            return
        self.is_searching = True

        container = self.search_results_container if target_view == "full" else self.trim_search_results_container
        btn = self.full_search_btn if target_view == "full" else self.trim_search_btn
        btn.configure(state="disabled", text="⏳ Buscando...")

        # Clear and pack container
        for widget in container.winfo_children():
            widget.destroy()

        if target_view == "full":
            container.pack(fill="x", padx=24, pady=(0, 12), before=self.fmt_card)
        else:
            container.pack(fill="x", padx=24, pady=(0, 12), before=self.player_card)

        # Loading header
        load_frame = ctk.CTkFrame(container, fg_color="transparent")
        load_frame.pack(fill="x", padx=16, pady=16)
        ctk.CTkLabel(
            load_frame,
            text=f"🔍 Pesquisando no YouTube: \"{query}\"...",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#60a5fa",
        ).pack(side="left")

        threading.Thread(
            target=self._search_worker,
            args=(query, target_view),
            daemon=True,
        ).start()

    def _search_worker(self, query: str, target_view: str) -> None:
        results = self.search_service.search(query, max_results=5)
        self.after(0, self._render_search_results, results, query, target_view)

    def _render_search_results(self, results: list[SearchResult], query: str, target_view: str) -> None:
        self.is_searching = False
        container = self.search_results_container if target_view == "full" else self.trim_search_results_container
        btn = self.full_search_btn if target_view == "full" else self.trim_search_btn
        btn.configure(state="normal", text="🔍 Pesquisar")

        for widget in container.winfo_children():
            widget.destroy()

        # Header Row
        hdr_row = ctk.CTkFrame(container, fg_color="transparent")
        hdr_row.pack(fill="x", padx=16, pady=(12, 8))

        if not results:
            ctk.CTkLabel(
                hdr_row,
                text=f"✖ Nenhum resultado encontrado para \"{query}\".",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#f87171",
            ).pack(side="left")
            close_btn = ctk.CTkButton(
                hdr_row,
                text="✕ Fechar",
                width=65,
                height=26,
                font=ctk.CTkFont(size=11),
                fg_color="transparent",
                hover_color="#27272a",
                text_color="#a1a1aa",
                command=lambda: container.pack_forget(),
            )
            close_btn.pack(side="right")
            return

        ctk.CTkLabel(
            hdr_row,
            text=f"🔍 {len(results)} resultados encontrados para \"{query}\":",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#93c5fd",
        ).pack(side="left")

        close_btn = ctk.CTkButton(
            hdr_row,
            text="✕ Fechar",
            width=65,
            height=26,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color="#27272a",
            text_color="#a1a1aa",
            command=lambda: container.pack_forget(),
        )
        close_btn.pack(side="right")

        # Results List
        for res in results:
            card = ctk.CTkFrame(
                container,
                fg_color="#141417",
                border_color="#27272a",
                border_width=1,
                corner_radius=8,
            )
            card.pack(fill="x", padx=16, pady=(0, 8))

            c_inner = ctk.CTkFrame(card, fg_color="transparent")
            c_inner.pack(fill="x", padx=10, pady=8)

            # Thumbnail placeholder
            thumb_label = ctk.CTkLabel(
                c_inner,
                text="🎵",
                width=76,
                height=42,
                fg_color="#27272a",
                corner_radius=6,
                font=ctk.CTkFont(size=16),
            )
            thumb_label.pack(side="left", padx=(0, 10))

            if res.thumbnail_url:
                threading.Thread(
                    target=self._fetch_result_thumb_async,
                    args=(res.thumbnail_url, thumb_label),
                    daemon=True,
                ).start()

            # Metadata column
            info_col = ctk.CTkFrame(c_inner, fg_color="transparent")
            info_col.pack(side="left", fill="both", expand=True)

            disp_title = res.title if len(res.title) <= 52 else res.title[:49] + "..."
            ctk.CTkLabel(
                info_col,
                text=disp_title,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#f4f4f5",
                anchor="w",
            ).pack(fill="x")

            sub_text = f"👤 {res.uploader}   •   ⏱️ {res.duration_formatted}"
            ctk.CTkLabel(
                info_col,
                text=sub_text,
                font=ctk.CTkFont(size=11),
                text_color="#a1a1aa",
                anchor="w",
            ).pack(fill="x", pady=(2, 0))

            # Actions column
            act_col = ctk.CTkFrame(c_inner, fg_color="transparent")
            act_col.pack(side="right", padx=(8, 0))

            if target_view == "full":
                dl_btn = ctk.CTkButton(
                    act_col,
                    text="⚡ Baixar",
                    width=75,
                    height=30,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color="#2563eb",
                    hover_color="#1d4ed8",
                    text_color="#ffffff",
                    corner_radius=6,
                    command=lambda u=res.url: self._quick_download_search_result(u),
                )
                dl_btn.pack(side="left", padx=(0, 4))

                trim_btn = ctk.CTkButton(
                    act_col,
                    text="✂️ Recortar",
                    width=78,
                    height=30,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color="#1e293b",
                    hover_color="#334155",
                    text_color="#93c5fd",
                    corner_radius=6,
                    command=lambda u=res.url: self._open_search_result_in_trimmer(u),
                )
                trim_btn.pack(side="left")
            else:
                load_btn = ctk.CTkButton(
                    act_col,
                    text="🎧 Carregar no Player",
                    width=140,
                    height=30,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    fg_color="#2563eb",
                    hover_color="#1d4ed8",
                    text_color="#ffffff",
                    corner_radius=6,
                    command=lambda u=res.url: self._load_search_result_into_trimmer(u),
                )
                load_btn.pack(side="left")

    def _fetch_result_thumb_async(self, thumb_url: str, label_widget: ctk.CTkLabel) -> None:
        try:
            req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as response:
                img_data = response.read()
            pil_img = Image.open(io.BytesIO(img_data)).convert("RGB")
            pil_img = ImageOps.fit(pil_img, (76, 42), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(76, 42))
            self._search_thumb_images.append(ctk_img)
            self.after(0, lambda: self._apply_thumb_image(label_widget, ctk_img))
        except Exception:
            pass

    def _apply_thumb_image(self, label_widget: ctk.CTkLabel, ctk_img: ctk.CTkImage) -> None:
        try:
            if label_widget.winfo_exists():
                label_widget.configure(image=ctk_img, text="")
        except Exception:
            pass

    def _quick_download_search_result(self, url: str) -> None:
        self.full_url_entry.delete(0, "end")
        self.full_url_entry.insert(0, url)
        self.search_results_container.pack_forget()
        self._start_download_from_view("full")

    def _open_search_result_in_trimmer(self, url: str) -> None:
        self.search_results_container.pack_forget()
        self._switch_view("trimmer")
        self.trim_url_entry.delete(0, "end")
        self.trim_url_entry.insert(0, url)
        self._start_fetch_preview()

    def _load_search_result_into_trimmer(self, url: str) -> None:
        self.trim_search_results_container.pack_forget()
        self.trim_url_entry.delete(0, "end")
        self.trim_url_entry.insert(0, url)
        self._start_fetch_preview()

    # =========================================================================
    # AUDIO PLAYER & SCRUBBING METHODS
    # =========================================================================
    def _start_fetch_preview(self) -> None:
        """Fetches lightweight preview stream for player scrubbing."""
        if self.is_fetching_preview:
            return

        url = self.trim_url_entry.get().strip()
        if not url:
            self.track_title_label.configure(text="Por favor, informe a URL primeiro", text_color="#f87171")
            return

        if not URLValidator.is_valid_youtube_url(url):
            if not url.startswith("http"):
                self._on_trim_search_click()
                return
            self.track_title_label.configure(text="URL do YouTube inválida", text_color="#f87171")
            return

        # Check if title is already known from history
        known_title = None
        if hasattr(self, "history_service"):
            target_vid = URLValidator.extract_video_id(url)
            for it in self.history_service.get_items():
                if it.url == url or (target_vid and URLValidator.extract_video_id(it.url) == target_vid):
                    known_title = it.title
                    break

        self.is_fetching_preview = True
        self.fetch_preview_btn.configure(state="disabled", text="⏳ Carregando...")
        if known_title:
            disp_k = known_title if len(known_title) <= 40 else known_title[:37] + "..."
            self.track_title_label.configure(text=f"Carregando: {disp_k}...", text_color="#60a5fa")
        else:
            self.track_title_label.configure(text="Obtendo stream do YouTube...", text_color="#60a5fa")

        t = threading.Thread(target=self._fetch_preview_worker, args=(url,), daemon=True)
        t.start()

    def _fetch_preview_worker(self, url: str) -> None:
        try:
            preview_file, duration, title, artist = self.preview_fetcher.fetch_preview(url)
            self.after(0, self._on_preview_ready, preview_file, title, duration, url)
        except Exception as e:
            logger.exception("Erro ao carregar prévia para o player: %s", e)
            self.after(0, self._on_preview_error, str(e))

    def _on_preview_ready(self, file_path: Path, title: str, duration: float, url: str = "") -> None:
        self.is_fetching_preview = False
        self.fetch_preview_btn.configure(state="normal", text="🎧 Carregar Player")

        # Resolve title if generic
        if (not title or title == "Áudio") and hasattr(self, "history_service") and url:
            target_vid = URLValidator.extract_video_id(url)
            for it in self.history_service.get_items():
                if it.url == url or (target_vid and URLValidator.extract_video_id(it.url) == target_vid):
                    if it.title and it.title != "Áudio":
                        title = it.title
                        break

        disp_title = title if len(title) <= 45 else title[:42] + "..."
        self.track_title_label.configure(text=f"Pronto: {disp_title}", text_color="#4ade80")

        self.player_service.load(file_path, duration=duration)
        self.audio_slider.configure(to=max(1.0, duration))
        self.audio_slider.set(0)
        self.time_label.configure(text=f"00:00 / {self._format_time(duration)}")
        self._update_playback_tick()

    def _on_preview_error(self, err_msg: str) -> None:
        self.is_fetching_preview = False
        self.fetch_preview_btn.configure(state="normal", text="🎧 Carregar Player")
        self.track_title_label.configure(text=f"Falha ao carregar: {err_msg[:35]}", text_color="#f87171")

    def _toggle_player(self) -> None:
        if not self.player_service.is_loaded:
            return
        self._test_cutoff_time = None
        if self.player_service.is_playing:
            self.player_service.pause()
            self.play_btn.configure(text="▶ Tocar")
        elif self.player_service.is_paused:
            self.player_service.unpause()
            self.play_btn.configure(text="⏸ Pausar")
        else:
            curr = self.audio_slider.get()
            self.player_service.play(curr)
            self.play_btn.configure(text="⏸ Pausar")

    def _stop_player(self) -> None:
        self.player_service.stop()
        self.play_btn.configure(text="▶ Tocar")
        self.audio_slider.set(0)
        dur = self.player_service.duration
        self.time_label.configure(text=f"00:00 / {self._format_time(dur)}")
        self._test_cutoff_time = None

    def _on_slider_start(self, event=None) -> None:
        self._is_dragging_slider = True

    def _on_slider_move(self, event=None) -> None:
        if self.player_service.duration > 0:
            val = self.audio_slider.get()
            dur = self.player_service.duration
            self.time_label.configure(text=f"{self._format_time(val)} / {self._format_time(dur)}")

    def _on_slider_release(self, event=None) -> None:
        self._is_dragging_slider = False
        self._test_cutoff_time = None
        if self.player_service.is_loaded:
            val = self.audio_slider.get()
            was_playing = self.player_service.is_playing
            self.player_service.play(val)
            if not was_playing:
                self.player_service.pause()
                self.play_btn.configure(text="▶ Tocar")
            else:
                self.play_btn.configure(text="⏸ Pausar")

    def _update_playback_tick(self) -> None:
        if not self.winfo_exists():
            return
        if self.player_service.is_loaded and not self._is_dragging_slider:
            curr = self.player_service.get_current_time()
            dur = self.player_service.duration

            if self._test_cutoff_time is not None and curr >= self._test_cutoff_time:
                self.player_service.stop()
                self.play_btn.configure(text="▶ Tocar")
                self.audio_slider.set(self._test_cutoff_time)
                self.time_label.configure(
                    text=f"{self._format_time(self._test_cutoff_time)} / {self._format_time(dur)}"
                )
                self._test_cutoff_time = None
                curr = self.audio_slider.get()

            if self.player_service.is_playing:
                self.audio_slider.set(curr)
                self.time_label.configure(text=f"{self._format_time(curr)} / {self._format_time(dur)}")
                if self.play_btn.cget("text") != "⏸ Pausar":
                    self.play_btn.configure(text="⏸ Pausar")
            elif not self.player_service.is_paused:
                if self.play_btn.cget("text") != "▶ Tocar":
                    self.play_btn.configure(text="▶ Tocar")

        self.after(200, self._update_playback_tick)

    def _mark_start_current(self) -> None:
        val = int(self.audio_slider.get())
        self.start_entry.delete(0, "end")
        self.start_entry.insert(0, self._format_time(val))

    def _mark_end_current(self) -> None:
        val = int(self.audio_slider.get())
        self.end_entry.delete(0, "end")
        self.end_entry.insert(0, self._format_time(val))

    def _test_trimmed_audio(self) -> None:
        if not self.player_service.is_loaded:
            return

        start_s = self._parse_time(self.start_entry.get())
        if start_s is None:
            start_s = int(self.audio_slider.get())

        end_s = self._parse_time(self.end_entry.get())
        if end_s is not None and end_s > start_s:
            self._test_cutoff_time = float(end_s)
        else:
            self._test_cutoff_time = float(self.preview_duration or self.player_service.duration or (start_s + 30.0))

        self.audio_slider.set(start_s)
        self.player_service.play(start_s)
        self.play_btn.configure(text="⏸ Pausar")

    def _clear_trim_inputs(self) -> None:
        self.start_entry.delete(0, "end")
        self.end_entry.delete(0, "end")
        self._test_cutoff_time = None

    def _format_time(self, seconds: float) -> str:
        s = max(0, int(seconds))
        m = s // 60
        sec = s % 60
        return f"{m:02d}:{sec:02d}"

    def _parse_time(self, val: str) -> Optional[int]:
        if not val or not val.strip():
            return None
        clean = val.strip()
        if clean.isdigit():
            return int(clean)
        parts = clean.split(":")
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
            pass
        return None

    # =========================================================================
    # DOWNLOAD EXECUTION DISPATCHER
    # =========================================================================
    def _start_download_from_view(self, source_view: str) -> None:
        """Validates parameters from the respective view and spawns extraction worker."""
        if self.is_version_blocked or self.is_downloading:
            return

        time_range = None
        if source_view == "trim":
            url = self.trim_url_entry.get().strip()
            start_s = self._parse_time(self.start_entry.get()) or 0
            end_s = self._parse_time(self.end_entry.get())
            if end_s is not None and end_s <= start_s:
                err_msg = "O tempo final deve ser estritamente maior que o tempo inicial."
                self.track_title_label.configure(text=f"Erro: {err_msg}", text_color="#f87171")
                if hasattr(self, "trim_status_label"):
                    self.trim_status_label.configure(text="✖ Erro no intervalo de recorte", text_color="#f87171")
                    self.trim_progress_badge.configure(text="Tempo Inválido", text_color="#f87171")
                    self.trim_details_label.configure(text=err_msg)
                return
            time_range = (start_s, end_s or 86400)
        else:
            url = self.full_url_entry.get().strip()

        if not url:
            err_msg = "Por favor, informe uma URL do YouTube."
            self.status_label.configure(text=err_msg, text_color="#f87171")
            self.progress_badge.configure(text="URL Ausente", text_color="#f87171")
            self.details_label.configure(text="Insira uma URL válida para continuar.")
            if hasattr(self, "trim_status_label"):
                self.trim_status_label.configure(text=err_msg, text_color="#f87171")
                self.trim_progress_badge.configure(text="URL Ausente", text_color="#f87171")
                self.trim_details_label.configure(text="Insira uma URL válida para continuar.")
            return

        if not URLValidator.is_valid_youtube_url(url):
            if not url.startswith("http"):
                if source_view == "trim":
                    self._on_trim_search_click()
                else:
                    self._on_full_search_click()
                return
            err_msg = "URL inválida ou não reconhecida."
            self.status_label.configure(text=err_msg, text_color="#f87171")
            self.progress_badge.configure(text="URL Inválida", text_color="#f87171")
            self.details_label.configure(text="Verifique o link do YouTube informado.")
            if hasattr(self, "trim_status_label"):
                self.trim_status_label.configure(text=err_msg, text_color="#f87171")
                self.trim_progress_badge.configure(text="URL Inválida", text_color="#f87171")
                self.trim_details_label.configure(text="Verifique o link do YouTube informado.")
            return

        choice = self.selected_format
        if "WAV" in choice:
            fmt, quality = "wav", "0"
        elif "FLAC" in choice:
            fmt, quality = "flac", "0"
        elif "M4A" in choice:
            fmt, quality = "m4a", "best"
        else:
            fmt, quality = "mp3", "320"

        # Update UI state on BOTH views
        self.is_downloading = True
        self.download_btn.configure(state="disabled", text="⏳ BAIXANDO...")
        self.trim_download_btn.configure(state="disabled", text="⏳ RECORTANDO...")

        self.status_label.configure(text="Iniciando extração...", text_color="#FFFFFF")
        self.progress_badge.configure(text="Conectando...", text_color="#60a5fa")
        self.details_label.configure(text="Conectando aos servidores do YouTube...")
        self.progress_bar.set(0.0)
        self.result_card.pack_forget()

        if hasattr(self, "trim_status_label"):
            self.trim_status_label.configure(text="Iniciando recorte...", text_color="#FFFFFF")
            self.trim_progress_badge.configure(text="Conectando...", text_color="#60a5fa")
            self.trim_details_label.configure(text="Conectando aos servidores do YouTube...")
            self.trim_progress_bar.set(0.0)
            self.trim_result_card.pack_forget()

        custom_template = None
        if source_view == "trim" and time_range:
            start_s, end_s = time_range
            s_str = self._format_time(start_s).replace(":", "m")
            e_str = self._format_time(end_s).replace(":", "m") if end_s < 86400 else "fim"
            custom_template = f"%(title)s [recorte {s_str}s-{e_str}s].%(ext)s"

        req = DownloadRequest(
            url=url,
            output_dir=self.output_dir,
            audio_format=fmt,
            audio_quality=quality,
            time_range=time_range,
            custom_filename_template=custom_template,
        )

        reporter = GuiProgressReporter(
            progress_callback=lambda ev: self.after(0, self._on_gui_progress, ev),
            stage_callback=lambda st, msg: self.after(0, self._on_gui_stage, st, msg),
            complete_callback=lambda res: self.after(0, self._on_gui_complete, res),
            error_callback=lambda err, u: self.after(0, self._on_gui_error, err, u),
        )

        worker = threading.Thread(target=self._run_download, args=(req, reporter), daemon=True)
        worker.start()

    def _run_download(self, req: DownloadRequest, reporter: GuiProgressReporter) -> None:
        try:
            self.downloader.download(req, reporter=reporter)
        except Exception as e:
            self.after(0, self._on_gui_error, str(e), req.url)

    def _on_gui_progress(self, event: ProgressEvent) -> None:
        if event.status == ProgressStatus.DOWNLOADING:
            if self.progress_bar.cget("mode") != "determinate":
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
            if hasattr(self, "trim_progress_bar") and self.trim_progress_bar.cget("mode") != "determinate":
                self.trim_progress_bar.stop()
                self.trim_progress_bar.configure(mode="determinate")

            pct = event.percentage / 100.0
            val = max(0.01, min(1.0, pct))
            self.progress_bar.set(val)
            if hasattr(self, "trim_progress_bar"):
                self.trim_progress_bar.set(val)

            speed_str = f"{event.speed_mb_sec:.1f} MB/s" if event.speed_mb_sec else "--"
            total_str = f"{event.total_mb:.1f} MB" if event.total_mb else "--"
            downloaded_str = f"{event.downloaded_mb:.1f} MB"
            eta_str = f"{event.eta_seconds}s" if event.eta_seconds else "--"

            stat_txt = f"Baixando áudio... {event.percentage:.1f}%"
            badge_txt = f"{event.percentage:.0f}%"
            det_txt = f"Progresso: {downloaded_str} / {total_str} | Velocidade: {speed_str} | Restante: {eta_str}"

            self.status_label.configure(text=stat_txt, text_color="#60a5fa")
            self.progress_badge.configure(text=badge_txt, text_color="#60a5fa")
            self.details_label.configure(text=det_txt)

            if hasattr(self, "trim_status_label"):
                self.trim_status_label.configure(text=stat_txt, text_color="#60a5fa")
                self.trim_progress_badge.configure(text=badge_txt, text_color="#60a5fa")
                self.trim_details_label.configure(text=det_txt)

    def _on_gui_stage(self, stage: ProgressStatus, message: str) -> None:
        if stage in (ProgressStatus.CONVERTING, ProgressStatus.PROCESSING):
            if self.progress_bar.cget("mode") != "indeterminate":
                self.progress_bar.configure(mode="indeterminate")
                self.progress_bar.start()
            if hasattr(self, "trim_progress_bar") and self.trim_progress_bar.cget("mode") != "indeterminate":
                self.trim_progress_bar.configure(mode="indeterminate")
                self.trim_progress_bar.start()

            if stage == ProgressStatus.CONVERTING:
                lbl_txt = "Convertendo com FFmpeg..."
                bdg_txt = "FFmpeg"
                col = "#fbbf24"
            else:
                lbl_txt = "Processando áudio..."
                bdg_txt = "Processando"
                col = "#c084fc"

            self.status_label.configure(text=lbl_txt, text_color=col)
            self.progress_badge.configure(text=bdg_txt, text_color=col)
            self.details_label.configure(text=message)

            if hasattr(self, "trim_status_label"):
                self.trim_status_label.configure(text=lbl_txt, text_color=col)
                self.trim_progress_badge.configure(text=bdg_txt, text_color=col)
                self.trim_details_label.configure(text=message)

    def _on_gui_complete(self, result: DownloadResult) -> None:
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="⚡ BAIXAR ÁUDIO COMPLETO")
        self.trim_download_btn.configure(state="normal", text="✂️ BAIXAR E RECORTAR TRECHO")

        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(1.0)

        if hasattr(self, "trim_progress_bar"):
            self.trim_progress_bar.stop()
            self.trim_progress_bar.configure(mode="determinate")
            self.trim_progress_bar.set(1.0)

        title = result.title or "Faixa de áudio"
        fmt = result.final_format.upper() if result.final_format else "AUDIO"
        compl_txt = "✔ Extração Concluída com Sucesso!"
        det_txt = f"{title} ({fmt})"

        self.status_label.configure(text=compl_txt, text_color="#4ade80")
        self.progress_badge.configure(text="Concluído", text_color="#4ade80")
        self.details_label.configure(text=det_txt)

        if hasattr(self, "trim_status_label"):
            self.trim_status_label.configure(text=compl_txt, text_color="#4ade80")
            self.trim_progress_badge.configure(text="Concluído", text_color="#4ade80")
            self.trim_details_label.configure(text=det_txt)

        self.last_downloaded_file = result.output_path
        if self.last_downloaded_file and self.last_downloaded_file.exists():
            size_mb = self.last_downloaded_file.stat().st_size / (1024 * 1024)
            save_msg = f"Salvo: {self.last_downloaded_file.name} ({size_mb:.1f} MB)"

            self.result_text.configure(text=save_msg)
            self.result_card.pack(fill="x", padx=16, pady=(0, 10))

            if hasattr(self, "trim_result_text") and hasattr(self, "trim_result_card"):
                self.trim_result_text.configure(text=save_msg)
                self.trim_result_card.pack(fill="x", padx=16, pady=(0, 10))

        # Register in persistent history
        self.history_service.add_from_result(result)
        self._refresh_history_ui()

    def _on_gui_error(self, error_message: str, url: str) -> None:
        self.is_downloading = False
        self.download_btn.configure(state="normal", text="⚡ BAIXAR ÁUDIO COMPLETO")
        self.trim_download_btn.configure(state="normal", text="✂️ BAIXAR E RECORTAR TRECHO")

        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0.0)

        if hasattr(self, "trim_progress_bar"):
            self.trim_progress_bar.stop()
            self.trim_progress_bar.configure(mode="determinate")
            self.trim_progress_bar.set(0.0)

        err_title = "✖ Erro durante a extração"
        self.status_label.configure(text=err_title, text_color="#f87171")
        self.progress_badge.configure(text="Falha", text_color="#f87171")
        self.details_label.configure(text=error_message)

        if hasattr(self, "trim_status_label"):
            self.trim_status_label.configure(text=err_title, text_color="#f87171")
            self.trim_progress_badge.configure(text="Falha", text_color="#f87171")
            self.trim_details_label.configure(text=error_message)


def launch_gui() -> None:
    """Launches the Elo Track GUI application."""
    app = EloTrackApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
