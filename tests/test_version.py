"""Unit tests for version control, SemVer comparisons, and sunset policy."""

from src.core.version import (
    VersionCheckResult,
    VersionService,
    VersionStatus,
    is_version_older,
    parse_semver,
)


def test_semver_parsing() -> None:
    assert parse_semver("1.0.0") == (1, 0, 0)
    assert parse_semver("v2.14.3") == (2, 14, 3)
    assert parse_semver("0.9.12-beta") == (0, 9, 12)
    assert parse_semver("invalid") == (0, 0, 0)


def test_version_comparisons() -> None:
    assert is_version_older("1.0.0", "1.0.1") is True
    assert is_version_older("1.0.0", "1.1.0") is True
    assert is_version_older("1.0.0", "2.0.0") is True
    assert is_version_older("1.0.1", "1.0.0") is False
    assert is_version_older("1.0.0", "1.0.0") is False


def test_version_service_active() -> None:
    service = VersionService(current_version="1.0.0", min_supported_version="1.0.0")
    result = service.check_status()
    assert result.status == VersionStatus.ACTIVE
    assert result.is_blocked is False


def test_version_service_deprecated_sunset() -> None:
    # Installed version is 1.0.0, but min required is 1.1.0
    service = VersionService(current_version="1.0.0", min_supported_version="1.1.0")
    result = service.check_status()
    assert result.status == VersionStatus.DEPRECATED
    assert result.is_blocked is True
    assert "descontinuada" in result.message


def test_version_service_custom_manifest() -> None:
    service = VersionService(current_version="1.0.0")
    manifest = {
        "latest_version": "2.0.0",
        "min_supported_version": "1.5.0",
        "download_url": "https://lookuplabs.com/downloads/setup.exe",
        "sunset_message": "Versão desativada pela Lookup Labs.",
    }
    result = service.check_status(custom_manifest=manifest)
    assert result.status == VersionStatus.DEPRECATED
    assert result.is_blocked is True
    assert result.download_url == "https://lookuplabs.com/downloads/setup.exe"
    assert result.message == "Versão desativada pela Lookup Labs."
