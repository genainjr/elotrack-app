"""CLI entry point for Elo Track."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .adapters.console_reporter import ConsoleProgressReporter
from .core.config import AudioBitrate, AudioFormat, ConfigManager
from .core.downloader import YtDlpAudioDownloader
from .core.history import DownloadHistoryService
from .core.interfaces import DownloadRequest
from .core.validator import EnvironmentValidator


def parse_time_argument(time_str: Optional[str]) -> Optional[int]:
    """Parses seconds or HH:MM:SS / MM:SS string into integer seconds."""
    if not time_str:
        return None
    time_str = time_str.strip()
    if time_str.isdigit():
        return int(time_str)

    parts = time_str.split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        pass
    raise argparse.ArgumentTypeError(
        f"Formato de tempo inválido: '{time_str}'. Use segundos (ex: 90) ou MM:SS (ex: 01:30)."
    )


def check_environment() -> int:
    """Diagnoses system requirements and prints status."""
    print("=== Diagnóstico de Ambiente - Elo Track ===")
    ffmpeg_path = EnvironmentValidator.get_ffmpeg_path()
    if ffmpeg_path:
        print(f"[OK] FFmpeg detectado em: {ffmpeg_path}")
    else:
        print("[AVISO] FFmpeg não foi encontrado no PATH do sistema!")
        print()
        print(EnvironmentValidator.get_ffmpeg_install_guide())

    try:
        import yt_dlp
        print(f"[OK] yt-dlp instalado (versão: {yt_dlp.version.__version__})")
    except ImportError:
        print("[ERRO] yt-dlp não está instalado. Execute: pip install yt-dlp")

    return 0 if ffmpeg_path else 1


def build_parser() -> argparse.ArgumentParser:
    """Configures command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="elo-track",
        description="Elo Track - Extrator de áudio em alta fidelidade a partir do YouTube para stems e análise musical.",
    )

    parser.add_argument(
        "urls",
        nargs="*",
        help="Uma ou mais URLs do YouTube para download.",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=list(AudioFormat.values()),
        default=AudioFormat.MP3.value,
        help="Formato de áudio de saída (padrão: mp3). Para máxima fidelidade em stems use 'wav' ou 'flac'.",
    )
    parser.add_argument(
        "-q",
        "--quality",
        choices=list(AudioBitrate.values()),
        default=AudioBitrate.B320.value,
        help="Qualidade/taxa de bits para MP3/M4A (padrão: 320 kbps). Use '0' para best.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=None,
        help="Diretório onde os arquivos de áudio serão salvos.",
    )
    parser.add_argument(
        "--start",
        type=parse_time_argument,
        default=None,
        help="Ponto de corte inicial (em segundos ou MM:SS). Ex: 00:30 ou 30.",
    )
    parser.add_argument(
        "--end",
        type=parse_time_argument,
        default=None,
        help="Ponto de corte final (em segundos ou MM:SS). Ex: 02:45 ou 165.",
    )
    parser.add_argument(
        "-b",
        "--batch",
        type=Path,
        help="Arquivo de texto contendo URLs (uma por linha).",
    )
    parser.add_argument(
        "--keep-original",
        action="store_true",
        help="Mantém o contêiner original de vídeo/áudio baixado além do áudio convertido.",
    )
    parser.add_argument(
        "--check-env",
        action="store_true",
        help="Verifica se FFmpeg e dependências estão corretamente instalados.",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Inicia a interface gráfica desktop (CustomTkinter).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Habilita mensagens de log detalhadas (DEBUG).",
    )

    return parser


def main(args_list: Optional[List[str]] = None) -> int:
    """Execution entry point."""
    # If no arguments provided in CLI invocation, default to launching GUI
    if args_list is None and len(sys.argv) == 1:
        try:
            from .gui.app import launch_gui
            launch_gui()
            return 0
        except Exception as e:
            print(f"[AVISO] Não foi possível iniciar a interface gráfica ({e}). Exibindo ajuda do terminal.\n")

    parser = build_parser()
    args = parser.parse_args(args_list)

    if args.gui:
        from .gui.app import launch_gui
        launch_gui()
        return 0

    log_level = logging.DEBUG if args.verbose else logging.WARNING
    ConfigManager.configure_logging(level=log_level, structured=args.verbose)

    if args.check_env:
        return check_environment()

    # Collect target URLs
    urls: List[str] = list(args.urls)
    if args.batch:
        batch_path = Path(args.batch)
        if not batch_path.is_file():
            print(f"[ERRO] Arquivo de lote não encontrado: {batch_path}", file=sys.stderr)
            return 1
        with open(batch_path, "r", encoding="utf-8") as f:
            for line in f:
                clean = line.strip()
                if clean and not clean.startswith("#"):
                    urls.append(clean)

    if not urls:
        parser.print_help()
        print("\n[ERRO] Nenhuma URL informada. Passe uma URL ou utilize --batch <arquivo>.", file=sys.stderr)
        return 1

    # Time range specification
    time_range: Optional[Tuple[int, int]] = None
    if args.start is not None or args.end is not None:
        start_val = args.start or 0
        if args.end is not None and args.end <= start_val:
            print("[ERRO] --end deve ser maior que --start.", file=sys.stderr)
            return 1
        # If no end specified, use a large integer limit or let yt-dlp handle it
        end_val = args.end if args.end is not None else 86400  # 24h default max
        time_range = (start_val, end_val)

    config_mgr = ConfigManager.get_instance(custom_output_dir=args.output_dir)
    target_output_dir = config_mgr.config.default_output_dir

    downloader = YtDlpAudioDownloader(config=config_mgr.config)
    reporter = ConsoleProgressReporter()

    exit_code = 0
    total = len(urls)

    for idx, url in enumerate(urls, start=1):
        if total > 1:
            print(f"\n--- Processando item {idx} de {total} ---")

        request = DownloadRequest(
            url=url,
            output_dir=target_output_dir,
            audio_format=args.format,
            audio_quality=args.quality,
            time_range=time_range,
            keep_original=args.keep_original,
        )

        result = downloader.download(request, reporter=reporter)
        if result.success:
            DownloadHistoryService().add_from_result(result)
        else:
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
