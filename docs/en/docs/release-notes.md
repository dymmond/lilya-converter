# Release Notes

## 0.2.0

### Added

- Framework-agnostic orchestration layer in `lilya_converter/core`.
- Explicit deterministic adapter registry for `fastapi`, `flask`, `django`, `litestar`, and `starlette`.
- New Flask adapter (`--source flask`).
- New Django adapter (`--source django`) with URLConf conversion and app materialization from `urlpatterns`.
- New Litestar adapter (`--source litestar`) with decorator and `route_handlers` conversion.
- New Starlette adapter (`--source starlette`) with `Route`, `Mount`, and `WebSocketRoute` conversion.
- Django-specific target path mapping from `management/commands/*` to `directives/operations/*`.
- Typed conversion plan/result models for analyze, convert, scaffold, and verify flows.
- Unified typed exceptions for registry and orchestration errors.
- Expanded tests for Flask, Django, Litestar, and Starlette adapters.
- Updated documentation with multi-framework support matrix and conversion examples.

### Changed

- FastAPI conversion implementation moved into a dedicated adapter package.
- CLI commands now route through adapter selection with `--source`.
- Default CLI behavior remains FastAPI when `--source` is omitted.
- Conversion output path handling now supports adapter-level remapping hooks.

### Fixed

- Ensured normalized route/include paths stay non-empty and Lilya-compatible.
- Improved Python 3.10 compatibility for CLI optional argument annotations.

## 0.1.0

`lilya-converter` is now available as a brand-new CLI to help migrate FastAPI codebases to Lilya with deterministic, report-driven workflows.

### What's Included

- `analyze`: scan FastAPI projects and report apps, routers, routes, dependencies, and conversion-relevant patterns.
- `convert`: transform FastAPI code to Lilya with dry-run and diff support.
- `scaffold`: generate a Lilya project entrypoint scaffold.
- `map rules`: inspect conversion rules.
- `map applied`: inspect which rules were applied from a conversion report.
- `verify`: run post-conversion checks and emit verification diagnostics.

### Key Behaviors

- Deterministic output and stable reporting for reproducible migrations.
- Structured diagnostics for unsupported or partially-supported patterns.
- Safe conversion workflow with preview-first options (`--dry-run`, `--diff`).

### Quick Start

```bash
lilya-converter analyze ./my-fastapi-app --json
lilya-converter convert ./my-fastapi-app ./my-lilya-app --dry-run --diff
lilya-converter verify ./my-lilya-app --report ./reports/verify.json
```
