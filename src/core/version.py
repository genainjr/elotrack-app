"""Version definition, SemVer comparisons, and version lifecycle / sunset management."""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.request
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

__version__ = "1.0.0"
DEFAULT_MIN_SUPPORTED_VERSION = "1.0.0"
DEFAULT_DOWNLOAD_URL = "https://lookuplabs.com/downloads/EloTrack-Setup.exe"


class VersionStatus(str, Enum):
    """Lifecycle states of the installed application version."""

    ACTIVE = "active"
    UPDATE_AVAILABLE = "update_available"
    DEPRECATED = "deprecated"


@dataclass
class VersionCheckResult:
    """Outcome of a version lifecycle verification."""

    status: VersionStatus
    current_version: str
    min_supported_version: str
    latest_version: str
    download_url: str
    message: str

    @property
    def is_blocked(self) -> bool:
        """Returns True if the current version is obsolete and must not execute."""
        return self.status == VersionStatus.DEPRECATED


def parse_semver(version_str: str) -> Tuple[int, int, int]:
    """Extracts (major, minor, patch) integers from a version string."""
    clean = version_str.strip().lstrip("vV")
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", clean)
    if not match:
        return (0, 0, 0)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def is_version_older(v1: str, v2: str) -> bool:
    """Returns True if v1 is strictly older than v2 (SemVer comparison)."""
    return parse_semver(v1) < parse_semver(v2)


class VersionService:
    """Evaluates software lifecycle, remote update policies, and sunset invalidation."""

    def __init__(
        self,
        current_version: str = __version__,
        min_supported_version: str = DEFAULT_MIN_SUPPORTED_VERSION,
        update_url: Optional[str] = None,
    ) -> None:
        self.current_version = current_version
        self.min_supported_version = os.getenv("ELO_TRACK_MIN_VERSION", min_supported_version)
        self.update_url = update_url or os.getenv("ELO_TRACK_UPDATE_URL")

    def check_status(self, custom_manifest: Optional[dict] = None) -> VersionCheckResult:
        """Determines if the installed version is active, out of date, or completely deprecated."""
        min_version = self.min_supported_version
        latest_version = self.current_version
        download_url = DEFAULT_DOWNLOAD_URL
        sunset_msg = (
            f"Esta versão do Elo Track (v{self.current_version}) foi descontinuada e não funciona mais. "
            "Por favor, instale a versão oficial mais recente para continuar."
        )

        manifest = custom_manifest
        if manifest is None and self.update_url:
            try:
                req = urllib.request.Request(
                    self.update_url,
                    headers={"User-Agent": f"EloTrack/{self.current_version}"},
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    if resp.status == 200:
                        manifest = json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                logger.debug("Falha na consulta remota de versão (%s): %s", self.update_url, exc)

        if manifest and isinstance(manifest, dict):
            min_version = manifest.get("min_supported_version", min_version)
            latest_version = manifest.get("latest_version", latest_version)
            download_url = manifest.get("download_url", download_url)
            if "sunset_message" in manifest:
                sunset_msg = manifest["sunset_message"]

        # Enforced sunset check
        if is_version_older(self.current_version, min_version):
            return VersionCheckResult(
                status=VersionStatus.DEPRECATED,
                current_version=self.current_version,
                min_supported_version=min_version,
                latest_version=latest_version,
                download_url=download_url,
                message=sunset_msg,
            )

        # Update available (non-blocking)
        if is_version_older(self.current_version, latest_version):
            return VersionCheckResult(
                status=VersionStatus.UPDATE_AVAILABLE,
                current_version=self.current_version,
                min_supported_version=min_version,
                latest_version=latest_version,
                download_url=download_url,
                message=f"Nova versão v{latest_version} disponível para atualização.",
            )

        return VersionCheckResult(
            status=VersionStatus.ACTIVE,
            current_version=self.current_version,
            min_supported_version=min_version,
            latest_version=latest_version,
            download_url=download_url,
            message="Versão oficial atualizada e homologada.",
        )
