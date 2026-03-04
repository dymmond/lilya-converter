"""Compatibility exports for FastAPI transformer implementation.

The canonical FastAPI transformer now lives in ``lilya_converter.adapters.fastapi``.
"""

from lilya_converter.adapters.fastapi.transformer import (
    TransformResult,
    transform_python_file,
    transform_python_source,
)

__all__ = ["TransformResult", "transform_python_source", "transform_python_file"]
