# Commands

This page documents each command in detail, including purpose, options, and practical examples.

## analyze

Analyze a FastAPI project and report conversion-relevant structure.

```bash
lilya-converter analyze SOURCE [--output REPORT.json] [--json]
```

### What it reports

- App/router constructor discovery.
- Route decorators and method/path metadata.
- `include_router(...)` usage.
- Dependency declarations in constructors/decorators/signatures.
- Middleware/event/exception-handler markers.

### Examples

```bash
lilya-converter analyze ./fastapi_project
lilya-converter analyze ./fastapi_project --json
lilya-converter analyze ./fastapi_project --output ./reports/scan.json
```

## convert

Transform a FastAPI project into Lilya output.

```bash
lilya-converter convert SOURCE TARGET \
  [--dry-run] \
  [--diff] \
  [--copy-non-python/--no-copy-non-python] \
  [--report REPORT.json]
```

### Option behavior

- `--dry-run`: computes conversion without writing files.
- `--diff`: prints unified diffs for changed Python files.
- `--copy-non-python`: copies non-Python assets to target (default enabled).
- `--report`: writes structured conversion report JSON.

### Examples

```bash
lilya-converter convert ./fastapi_project ./lilya_project
lilya-converter convert ./fastapi_project ./lilya_project --dry-run --diff
lilya-converter convert ./fastapi_project ./lilya_project --report ./reports/convert.json
```

## scaffold

Generate a minimal Lilya scaffold using scan findings.

```bash
lilya-converter scaffold SOURCE TARGET [--dry-run]
```

### Examples

```bash
lilya-converter scaffold ./fastapi_project ./lilya_scaffold
lilya-converter scaffold ./fastapi_project ./lilya_scaffold --dry-run
```

## map rules

List all supported conversion rule IDs and descriptions.

```bash
lilya-converter map rules
```

Use this for rule visibility and migration audits.

## map applied

Display applied rules from a previously generated conversion report.

```bash
lilya-converter map applied ./reports/convert.json
```

Useful when reviewing what was actually transformed in one run.

## verify

Run post-conversion checks against a generated Lilya project.

```bash
lilya-converter verify TARGET [--report REPORT.json]
```

### Checks include

- Python syntax validation.
- Remaining FastAPI import/call patterns.
- Unresolved local import modules.

### Examples

```bash
lilya-converter verify ./lilya_project
lilya-converter verify ./lilya_project --report ./reports/verify.json
```

## Recommended Migration Routine

1. `analyze`
2. `convert --dry-run --diff`
3. `convert`
4. `verify`
5. Review diagnostics and apply manual follow-ups
