"""Typed exception hierarchy for conversion orchestration and adapter lookup."""

from __future__ import annotations


class LilyaConverterError(Exception):
    """Base exception for converter failures."""


class AdapterRegistryError(LilyaConverterError):
    """Base exception for adapter registry operations."""


class UnsupportedSourceError(AdapterRegistryError):
    """Raised when a requested source framework is not registered.

    Args:
        source: Requested source framework identifier.
        supported_sources: Deterministically sorted known source identifiers.
    """

    def __init__(self, source: str, supported_sources: tuple[str, ...]) -> None:
        self.source = source
        self.supported_sources = supported_sources
        supported_text = ", ".join(supported_sources) if supported_sources else "(none)"
        super().__init__(f"Unsupported source framework '{source}'. Supported sources: {supported_text}")


class DuplicateAdapterError(AdapterRegistryError):
    """Raised when attempting to register an adapter with an existing source key.

    Args:
        source: Source framework identifier that is already registered.
    """

    def __init__(self, source: str) -> None:
        self.source = source
        super().__init__(f"Adapter for source '{source}' is already registered.")


class ConversionPathError(LilyaConverterError):
    """Raised when a required source/target path is invalid.

    Args:
        message: Human-readable path validation error message.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
