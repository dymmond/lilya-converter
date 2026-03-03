# Release Notes

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
