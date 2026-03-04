# Release Notes

## 0.2.0

`lilya-converter` now supports a multi-framework adapter architecture.

### What's Included

- Framework-agnostic core orchestration (`core` package).
- Explicit deterministic adapter registry (`fastapi`, `flask`).
- New Flask-to-Lilya adapter (`--source flask`).
- FastAPI conversion moved into a dedicated adapter with compatibility shims.
- Unified typed exception model for adapter/registry/path errors.
- Typed conversion plan/result objects in orchestration.
- CLI source selection support with stable help output for supported sources.
- New Flask tests:
  - registry selection,
  - CLI parsing,
  - end-to-end fixture-to-golden conversion.

### Compatibility

- Existing FastAPI CLI behavior remains backwards compatible.
- Omitting `--source` still defaults to `fastapi`.

### Quick Start

```bash
lilya-converter analyze ./my-fastapi-app
lilya-converter convert ./my-fastapi-app ./my-lilya-app
lilya-converter convert ./my-flask-app ./my-lilya-app --source flask
lilya-converter verify ./my-lilya-app --source flask
```

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
