"""Automated Build & Packaging script for EloTrack Windows Executable (.exe)."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent


def ensure_not_running() -> None:
    """Closes any existing EloTrack instances so build output files are not locked."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/f", "/im", "EloTrack.exe"], capture_output=True)


def ensure_icon() -> Path:
    """Verifies that the application icon exists or generates it."""
    assets_dir = ROOT_DIR / "assets"
    assets_dir.mkdir(exist_ok=True)
    ico_path = assets_dir / "elotrack.ico"
    png_path = assets_dir / "elotrack.png"

    if not ico_path.exists() or not png_path.exists():
        print("[*] Gerando ícone oficial EloTrack...")
        from PIL import Image, ImageDraw

        size = (256, 256)
        img = Image.new("RGBA", size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Dark card background
        draw.rounded_rectangle([8, 8, 248, 248], radius=52, fill=(15, 23, 42, 255), outline=(37, 99, 235, 255), width=6)
        draw.ellipse([36, 36, 220, 220], fill=(24, 24, 27, 255), outline=(59, 130, 246, 200), width=3)

        # Equalizer bars
        draw.rounded_rectangle([72, 100, 84, 156], radius=6, fill=(96, 165, 250, 255))
        draw.rounded_rectangle([96, 76, 108, 180], radius=6, fill=(59, 130, 246, 255))
        draw.rounded_rectangle([120, 56, 136, 200], radius=8, fill=(147, 197, 253, 255))
        draw.rounded_rectangle([148, 76, 160, 180], radius=6, fill=(59, 130, 246, 255))
        draw.rounded_rectangle([172, 100, 184, 156], radius=6, fill=(96, 165, 250, 255))

        # Lightning bolt
        bolt_coords = [(136, 80), (114, 130), (134, 130), (120, 184), (154, 122), (132, 122), (146, 80)]
        draw.polygon(bolt_coords, fill=(255, 255, 255, 240), outline=(37, 99, 235, 255))

        img.save(png_path, "PNG")
        img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        print(f"[+] Ícone gerado em: {ico_path}")

    return ico_path


def get_detected_ffmpeg() -> Path | None:
    """Finds installed FFmpeg executable on the build system."""
    from src.core.validator import EnvironmentValidator
    return EnvironmentValidator.get_ffmpeg_path()


def run_build(mode: str = "onefile", embed_ffmpeg: bool = False) -> int:
    """Runs PyInstaller build workflow."""
    print("=" * 60)
    print(f"[EloTrack] Empacotamento Windows Executavel (.exe)")
    print(f"Modo: {mode.upper()} | Embed FFmpeg: {embed_ffmpeg}")
    print("=" * 60)

    ensure_not_running()
    ico_path = ensure_icon()

    dist_dir = ROOT_DIR / "dist"
    build_dir = ROOT_DIR / "build"

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
    ]

    if mode == "onefile":
        cmd.append(str(ROOT_DIR / "elotrack.spec"))
    else:
        # Directory distribution
        cmd.extend([
            "--onedir",
            "--windowed",
            "--name", "EloTrack",
            f"--icon={ico_path}",
            "--collect-all", "customtkinter",
            "--collect-all", "pygame",
            "--collect-all", "yt_dlp",
            "--collect-all", "mutagen",
            f"--add-data=assets{os.pathsep}assets",
            "--hidden-import=src",
            "--hidden-import=src.core",
            "--hidden-import=src.core.history",
            "--hidden-import=src.core.search",
            "--hidden-import=src.gui",
            "--hidden-import=src.gui.fonts",
            "--hidden-import=mutagen",
            str(ROOT_DIR / "run_gui.py"),
        ])

    print(f"[*] Executando PyInstaller: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if result.returncode != 0:
        print(f"[-] Erro ao compilar com PyInstaller (código {result.returncode}).")
        return result.returncode

    # Optional FFmpeg embedding
    if embed_ffmpeg or mode == "onedir":
        ffmpeg_bin = get_detected_ffmpeg()
        if ffmpeg_bin and ffmpeg_bin.exists():
            if mode == "onedir":
                target_bin_dir = dist_dir / "EloTrack" / "bin"
                target_bin_dir.mkdir(parents=True, exist_ok=True)
                dest_ffmpeg = target_bin_dir / "ffmpeg.exe"
                print(f"[*] Copiando FFmpeg para pasta portátil: {dest_ffmpeg}...")
                shutil.copy2(ffmpeg_bin, dest_ffmpeg)
                # Also ffprobe if present
                ffprobe_candidate = ffmpeg_bin.parent / "ffprobe.exe"
                if ffprobe_candidate.exists():
                    shutil.copy2(ffprobe_candidate, target_bin_dir / "ffprobe.exe")
                print("[+] FFmpeg copiado com sucesso para o pacote portátil!")
            elif embed_ffmpeg and mode == "onefile":
                # For onefile standalone, we can provide a companion bin/ folder next to EloTrack.exe
                target_bin_dir = dist_dir / "bin"
                target_bin_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ffmpeg_bin, target_bin_dir / "ffmpeg.exe")
                print(f"[+] FFmpeg copiado para {target_bin_dir / 'ffmpeg.exe'}")

    print("\n" + "=" * 60)
    print("[SUCCESS] Build concluido com sucesso!")
    if mode == "onefile":
        target_exe = dist_dir / "EloTrack.exe"
        if target_exe.exists():
            mb_size = target_exe.stat().st_size / (1024 * 1024)
            print(f"[+] Executavel Portatil: {target_exe} ({mb_size:.1f} MB)")
    else:
        target_folder = dist_dir / "EloTrack"
        print(f"[+] Pasta de Distribuicao Portatil: {target_folder}")
    print("=" * 60)
    return 0


def build_installer() -> int:
    """Invokes Inno Setup (ISCC.exe) to generate the official Windows installer."""
    iss_file = ROOT_DIR / "installer" / "elotrack_setup.iss"
    if not iss_file.exists():
        print(f"[-] Arquivo de script Inno Setup não encontrado: {iss_file}")
        return 1

    iscc_candidates = [
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe")),
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
    ]
    iscc_path = None
    for cand in iscc_candidates:
        if cand.is_file():
            iscc_path = cand
            break

    if not iscc_path:
        which_iscc = shutil.which("iscc")
        if which_iscc:
            iscc_path = Path(which_iscc)

    if not iscc_path:
        print("[-] Compilador Inno Setup (ISCC.exe) não encontrado. Instale com: winget install JRSoftware.InnoSetup")
        return 1

    print("=" * 60)
    print(f"[EloTrack] Compilando Instalador Oficial do Windows com Inno Setup")
    print(f"ISCC: {iscc_path}")
    print("=" * 60)
    res = subprocess.run([str(iscc_path), str(iss_file)], cwd=str(ROOT_DIR))
    if res.returncode == 0:
        installer_dir = ROOT_DIR / "dist" / "installer"
        for setup_file in installer_dir.glob("EloTrack-Setup*.exe"):
            mb = setup_file.stat().st_size / (1024 * 1024)
            print("\n" + "=" * 60)
            print(f"[SUCCESS] Instalador Oficial criado: {setup_file} ({mb:.1f} MB)")
            print("=" * 60)
    return res.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EloTrack Executable Builder")
    parser.add_argument(
        "--mode",
        choices=["onefile", "onedir"],
        default="onedir",
        help="Build mode: 'onefile' (standalone .exe) or 'onedir' (portable folder)",
    )
    parser.add_argument(
        "--embed-ffmpeg",
        action="store_true",
        help="Copy system FFmpeg into distribution folder",
    )
    parser.add_argument(
        "--installer",
        action="store_true",
        help="Build official Windows Setup installer using Inno Setup",
    )
    args = parser.parse_args()

    if args.installer:
        ret = run_build(mode="onedir", embed_ffmpeg=True)
        if ret != 0:
            sys.exit(ret)
        sys.exit(build_installer())

    sys.exit(run_build(mode=args.mode, embed_ffmpeg=args.embed_ffmpeg))
