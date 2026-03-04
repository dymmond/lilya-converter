"""Compatibility exports for FastAPI mapping rules.

The canonical FastAPI rule registry now lives in ``lilya_converter.adapters.fastapi``.
"""

from lilya_converter.adapters.fastapi.rules import RULES
from lilya_converter.core.rules import MappingRule

__all__ = ["MappingRule", "RULES"]
