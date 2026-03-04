from __future__ import annotations

import pytest

from lilya_converter.core.errors import UnsupportedSourceError
from lilya_converter.engine import mapping_rules, supported_sources


def test_supported_sources_are_sorted_and_explicit() -> None:
    """Ensure registry source keys are deterministic and explicit."""
    assert supported_sources() == ("fastapi", "flask")


def test_mapping_rules_resolve_flask_adapter() -> None:
    """Ensure mapping rule lookup routes to the Flask adapter."""
    rule_ids = {rule_id for rule_id, _summary in mapping_rules(source_framework="flask")}
    assert "register_blueprint_to_include" in rule_ids
    assert "flask_imports_to_lilya" in rule_ids


def test_mapping_rules_raise_for_unsupported_source() -> None:
    """Ensure unknown source identifiers raise a typed adapter error."""
    with pytest.raises(UnsupportedSourceError):
        mapping_rules(source_framework="unknown")
