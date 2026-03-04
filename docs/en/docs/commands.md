# Command Reference

This is the full CLI reference with examples from basic to advanced.

Supported sources are listed in command help and resolved deterministically: `fastapi`, `flask`.

## `analyze`

Analyze a source root and report conversion-relevant structure.

```bash
lilya-converter analyze SOURCE [--source fastapi|flask] [--output REPORT.json] [--json]
```

### Basic (FastAPI default)

```bash
lilya-converter analyze ./fastapi_project
```

### Flask

```bash
lilya-converter analyze ./flask_project --source flask
```

### Advanced

```bash
lilya-converter analyze ./fastapi_project --json
```

Use this when you want machine-readable output in CI pipelines.

## `convert`

Convert a source root into a Lilya target root.

```bash
lilya-converter convert SOURCE TARGET \
  [--source fastapi|flask] \
  [--dry-run] \
  [--diff] \
  [--copy-non-python/--no-copy-non-python] \
  [--report REPORT.json]
```

### Basic (FastAPI default)

```bash
lilya-converter convert ./fastapi_project ./lilya_project
```

### Flask

```bash
lilya-converter convert ./flask_project ./lilya_project --source flask
```

### Intermediate (recommended preview)

```bash
lilya-converter convert ./fastapi_project ./lilya_project --dry-run --diff --report ./reports/convert.json
```

### Advanced

```bash
lilya-converter convert ./fastapi_project ./lilya_project --no-copy-non-python --report ./reports/convert.json
```

### Single-file workflow

The converter expects a source directory. For one-file conversion, use a minimal root.

```bash
mkdir -p ./tmp-single-source/app
cp ./fastapi_project/app/main.py ./tmp-single-source/app/main.py
lilya-converter convert ./tmp-single-source ./tmp-single-target --report ./reports/convert-single.json
```

## `scaffold`

Generate a minimal Lilya scaffold informed by source analysis.

```bash
lilya-converter scaffold SOURCE TARGET [--source fastapi|flask] [--dry-run]
```

### Basic

```bash
lilya-converter scaffold ./fastapi_project ./lilya_scaffold
```

### Flask

```bash
lilya-converter scaffold ./flask_project ./lilya_scaffold --source flask
```

## `map rules`

List all known conversion rules for one source framework.

```bash
lilya-converter map rules [--source fastapi|flask]
```

## `map applied`

Show which rules were actually applied in a conversion report.

```bash
lilya-converter map applied ./reports/convert.json
```

## `verify`

Run structural checks on converted output.

```bash
lilya-converter verify TARGET [--source fastapi|flask] [--report REPORT.json]
```

### Basic

```bash
lilya-converter verify ./lilya_project
```

### Flask

```bash
lilya-converter verify ./lilya_project --source flask
```

### What it checks

- Python syntax validation.
- Remaining source-framework import/call patterns.
- Unresolved local imports.

## Suggested production routine

1. `analyze`
2. `convert --dry-run --diff`
3. `convert`
4. `verify`
5. `map applied`
