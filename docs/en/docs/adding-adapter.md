# Adding a New Adapter

Use this guide to add a new source framework adapter (for example `django`, `litestar`, `sanic`, `falcon`).

## Adapter architecture

The converter is split into:

- Core orchestration: registry + conversion pipeline (`lilya_converter/core`).
- Source adapters: framework-specific scanner/transformer/rules (`lilya_converter/adapters/<source>`).
- CLI routing: source selection and report output (`lilya_converter/cli.py`).

## 1. Create adapter package

Create `lilya_converter/adapters/<source>/` with:

- `scanner.py`
- `transformer.py`
- `rules.py`
- `adapter.py`
- `__init__.py`

## 2. Implement adapter interface

Match the protocol in `lilya_converter/core/protocols.py`:

- `source: str`
- `display_name: str`
- `analyze(source_root)`
- `transform_python_file(path, source_root)`
- `mapping_rules()`
- `scaffold(source_root, target_root, dry_run=False)`
- `collect_verify_diagnostics(relative_path, source)`

Optional adapter extension points:

- `target_relative_path(relative_path)` for framework-specific output path remapping (for example, Django `management/commands/*` to Lilya `directives/operations/*`).

## 3. Register adapter explicitly

Update `lilya_converter/adapters/__init__.py` and add your adapter to `create_default_adapters()`.

Do not use dynamic auto-discovery. Keep registration deterministic.

## 4. Add mapping rules

Create typed rules in `lilya_converter/adapters/<source>/rules.py` using `MappingRule`.

Rule IDs must be:

- stable,
- machine-readable,
- unique per adapter.

## 5. Add tests

Add tests in one pytest suite run:

- Registry tests (`tests/unit/test_registry.py` style).
- CLI source parsing tests (`tests/cli/test_cli.py` style).
- End-to-end fixture-to-golden conversion (`tests/integration/`).

Recommended fixture layout:

- `tests/fixtures/<source>/<scenario>/...`
- `tests/fixtures/golden_<source>/<scenario>/...`

If your adapter remaps output paths, add at least one fixture and assertion that validates the remapped target location.

## 6. Conventions

- Use complete type hints.
- Use Google-style docstrings on all public classes/functions.
- Emit typed diagnostics (`Diagnostic`) for partial/unsupported mappings.
- Keep output deterministic (sorted traversal, stable rule ordering).
- Keep compatibility shims intact when changing historical public modules.

## 7. Verify before merge

Run:

```bash
hatch run test:test -q
hatch run docs:build
```
