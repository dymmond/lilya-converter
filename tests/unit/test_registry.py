from __future__ import annotations

import pytest

from lilya_converter.core.errors import UnsupportedSourceError
from lilya_converter.engine import mapping_rules, supported_sources


def test_supported_sources_are_sorted_and_explicit() -> None:
    """Ensure registry source keys are deterministic and explicit."""
    assert supported_sources() == ("django", "fastapi", "flask", "litestar", "starlette")


def test_mapping_rules_resolve_flask_adapter() -> None:
    """Ensure mapping rule lookup routes to the Flask adapter."""
    rule_ids = {rule_id for rule_id, _summary in mapping_rules(source_framework="flask")}
    assert "register_blueprint_to_include" in rule_ids
    assert "flask_imports_to_lilya" in rule_ids


def test_mapping_rules_resolve_django_adapter() -> None:
    """Ensure mapping rule lookup routes to the Django adapter."""
    rule_ids = {rule_id for rule_id, _summary in mapping_rules(source_framework="django")}
    assert "django_path_to_lilya_path" in rule_ids
    assert "django_include_to_lilya_include" in rule_ids


def test_mapping_rules_resolve_litestar_adapter() -> None:
    """Ensure mapping rule lookup routes to the Litestar adapter."""
    rule_ids = {rule_id for rule_id, _summary in mapping_rules(source_framework="litestar")}
    assert "litestar_decorators_to_paths" in rule_ids
    assert "litestar_app_route_handlers_to_routes" in rule_ids


def test_mapping_rules_resolve_starlette_adapter() -> None:
    """Ensure mapping rule lookup routes to the Starlette adapter."""
    rule_ids = {rule_id for rule_id, _summary in mapping_rules(source_framework="starlette")}
    assert "starlette_route_to_path" in rule_ids
    assert "starlette_mount_to_include" in rule_ids


def test_mapping_rules_raise_for_unsupported_source() -> None:
    """Ensure unknown source identifiers raise a typed adapter error."""
    with pytest.raises(UnsupportedSourceError):
        mapping_rules(source_framework="unknown")
