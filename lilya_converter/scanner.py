"""Compatibility exports for FastAPI scanner implementation.

The canonical FastAPI scanner now lives in ``lilya_converter.adapters.fastapi``.
"""

from lilya_converter.adapters.fastapi.scanner import FastAPIScanner

__all__ = ["FastAPIScanner"]
