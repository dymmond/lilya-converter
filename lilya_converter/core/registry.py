"""Deterministic registry for source-framework adapters."""

from __future__ import annotations

from dataclasses import dataclass, field

from lilya_converter.core.errors import DuplicateAdapterError, UnsupportedSourceError
from lilya_converter.core.protocols import SourceFrameworkAdapter


@dataclass
class AdapterRegistry:
    """Store and resolve framework adapters by stable source identifier.

    Args:
        adapters: Optional initial adapter collection.

    Raises:
        DuplicateAdapterError: If two adapters share the same ``source`` key.
    """

    adapters: list[SourceFrameworkAdapter] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate and normalize initial adapter collection.

        Raises:
            DuplicateAdapterError: If duplicate sources are present.
        """
        items = list(self.adapters)
        self.adapters = []
        for adapter in items:
            self.register(adapter)

    def register(self, adapter: SourceFrameworkAdapter) -> None:
        """Register one adapter instance.

        Args:
            adapter: Adapter instance to register.

        Raises:
            DuplicateAdapterError: If an adapter for ``adapter.source`` already exists.
        """
        key = adapter.source.lower().strip()
        if any(existing.source.lower().strip() == key for existing in self.adapters):
            raise DuplicateAdapterError(adapter.source)
        self.adapters.append(adapter)
        self.adapters.sort(key=lambda item: item.source)

    def get(self, source: str) -> SourceFrameworkAdapter:
        """Resolve an adapter by source key.

        Args:
            source: Source framework identifier.

        Returns:
            The matching adapter instance.

        Raises:
            UnsupportedSourceError: If no adapter exists for ``source``.
        """
        normalized = source.lower().strip()
        for adapter in self.adapters:
            if adapter.source.lower().strip() == normalized:
                return adapter
        raise UnsupportedSourceError(source=source, supported_sources=self.supported_sources())

    def supported_sources(self) -> tuple[str, ...]:
        """Return deterministically sorted source identifiers.

        Returns:
            Tuple of source keys sorted ascending.
        """
        return tuple(sorted(adapter.source for adapter in self.adapters))
