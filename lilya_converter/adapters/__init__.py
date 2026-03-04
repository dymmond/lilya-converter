"""Adapter package and default adapter registration helpers."""

from __future__ import annotations

from lilya_converter.adapters.fastapi import FastAPIAdapter
from lilya_converter.adapters.flask import FlaskAdapter
from lilya_converter.core.protocols import SourceFrameworkAdapter


def create_default_adapters() -> list[SourceFrameworkAdapter]:
    """Create the explicit default adapter set.

    Returns:
        Deterministic list of source adapters.
    """
    return [FastAPIAdapter(), FlaskAdapter()]


__all__ = ["FastAPIAdapter", "FlaskAdapter", "create_default_adapters"]
