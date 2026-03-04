"""Adapter package and default adapter registration helpers."""

from __future__ import annotations

from lilya_converter.adapters.django import DjangoAdapter
from lilya_converter.adapters.fastapi import FastAPIAdapter
from lilya_converter.adapters.flask import FlaskAdapter
from lilya_converter.adapters.litestar import LitestarAdapter
from lilya_converter.adapters.starlette import StarletteAdapter
from lilya_converter.core.protocols import SourceFrameworkAdapter


def create_default_adapters() -> list[SourceFrameworkAdapter]:
    """Create the explicit default adapter set.

    Returns:
        Deterministic list of source adapters.
    """
    return [FastAPIAdapter(), FlaskAdapter(), DjangoAdapter(), LitestarAdapter(), StarletteAdapter()]


__all__ = [
    "DjangoAdapter",
    "FastAPIAdapter",
    "FlaskAdapter",
    "LitestarAdapter",
    "StarletteAdapter",
    "create_default_adapters",
]
