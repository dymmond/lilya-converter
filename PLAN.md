# Multi-Framework Refactor Plan

## Phase Checklist
- [x] Phase 0 - Inventory (no code changes)
- [x] Phase 1 - Target architecture proposal (no code changes)
- [x] Phase 2 - Implement core + registry (small commit)
- [x] Phase 3 - Move FastAPI implementation into adapter (no behavior change except include path normalization to '/').
- [x] Phase 4 - Add Flask adapter
- [x] Phase 5 - Update CLI + docs

## Phase 0 - Inventory Summary

### Current package layout and responsibilities
- `lilya_converter/__main__.py`: module entrypoint (`python -m lilya_converter`) that runs the Sayer app.
- `lilya_converter/cli.py`: Sayer CLI definition and command handlers.
- `lilya_converter/engine.py`: orchestration layer for analyze/convert/scaffold/verify and report serialization.
- `lilya_converter/scanner.py`: `FastAPIScanner` AST scanner for FastAPI-specific structure detection.
- `lilya_converter/transformer.py`: AST rewrite pipeline for FastAPI-to-Lilya conversion.
- `lilya_converter/writer.py`: deterministic filesystem traversal and write/copy helpers.
- `lilya_converter/models.py`: typed report/diagnostic dataclasses (`ScanReport`, `ConversionReport`, `VerifyReport`, etc.).
- `lilya_converter/rules.py`: static conversion rule registry exposed by `map rules`.

### Current CLI commands and entrypoint
- Packaging entrypoint (`pyproject.toml`): `lilya-converter = lilya_converter.__main__:run`.
- Root CLI app (`lilya_converter/cli.py`): `analyze`, `convert`, `scaffold`, `map`, `verify`.
- Nested CLI app (`map`): `rules`, `applied`.

### FastAPI-specific coupling points (current state)
- Scanner/transformer/engine/models/CLI/docs/tests were FastAPI-shaped and source-specific.

### Test suite structure
- Unit: engine/scanner/transformer/writer.
- Integration: fixture-to-golden conversion.
- CLI: command behavior.
- Docs: docs pipeline and build smoke.

### Documentation system and locations
- Authoring: `docs/en/docs`.
- Snippets: `docs_src`.
- Generation: `scripts/docs.py` + `scripts/docs_pipeline.py`.
- Config: `mkdocs.yaml`.

## Phase 1 - Target Architecture Proposal

### New tree layout
- `lilya_converter/core/`: framework-agnostic orchestration, plans, registry, errors, protocols, shared rule type.
- `lilya_converter/adapters/fastapi/`: FastAPI scanner/transformer/rules/adapter.
- `lilya_converter/adapters/flask/`: Flask scanner/transformer/rules/adapter.
- `lilya_converter/utils/`: shared filesystem helpers.
- Compatibility shims remain at top-level modules (`engine.py`, `scanner.py`, `transformer.py`, `rules.py`, `writer.py`).

### Migration mapping old -> new
- `lilya_converter/scanner.py` -> `lilya_converter/adapters/fastapi/scanner.py` (shim kept).
- `lilya_converter/transformer.py` -> `lilya_converter/adapters/fastapi/transformer.py` (shim kept).
- `lilya_converter/rules.py` -> `lilya_converter/adapters/fastapi/rules.py` + `core/rules.py` (shim kept).
- `lilya_converter/writer.py` -> `lilya_converter/utils/filesystem.py` (shim kept).
- `lilya_converter/engine.py` -> wraps `lilya_converter/core/orchestrator.py`.

### Compatibility strategy
- Keep legacy imports and function names stable.
- Keep CLI default source as FastAPI (`--source` optional).
- Route CLI through engine/core only.
- Explicit adapter registry, no auto-discovery.
