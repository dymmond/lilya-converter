"""Rule metadata models shared by framework adapters.

This module defines the typed rule descriptor used by adapter-specific
conversion rule registries and CLI map output.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MappingRule:
    """Describe one conversion mapping rule.

    Args:
        id: Stable machine-readable rule identifier.
        summary: Human-readable summary of the rule behavior.
    """

    id: str
    summary: str
