"""Core framework-agnostic orchestration and registry interfaces."""

from lilya_converter.core.errors import (
    AdapterRegistryError,
    ConversionPathError,
    DuplicateAdapterError,
    LilyaConverterError,
    UnsupportedSourceError,
)
from lilya_converter.core.orchestrator import ConversionOrchestrator
from lilya_converter.core.plans import (
    AnalysisPlan,
    AnalysisResult,
    ConversionPlan,
    ConversionResult,
    ScaffoldPlan,
    ScaffoldResult,
    VerificationPlan,
    VerificationResult,
)
from lilya_converter.core.registry import AdapterRegistry

__all__ = [
    "AdapterRegistry",
    "AdapterRegistryError",
    "AnalysisPlan",
    "AnalysisResult",
    "ConversionOrchestrator",
    "ConversionPathError",
    "ConversionPlan",
    "ConversionResult",
    "DuplicateAdapterError",
    "LilyaConverterError",
    "ScaffoldPlan",
    "ScaffoldResult",
    "UnsupportedSourceError",
    "VerificationPlan",
    "VerificationResult",
]
