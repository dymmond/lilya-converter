# Command Reference

This is the full CLI reference with examples from basic to advanced.

Supported source keys are listed in command help and resolved deterministically.

## `analyze`

Analyze a source root and report conversion-relevant structure.

```bash
lilya-converter analyze SOURCE [--source SOURCE_KEY] [--output REPORT.json] [--json]
```

Examples:

```bash
lilya-converter analyze ./fastapi_project
lilya-converter analyze ./django_project --source django --output ./reports/scan.json
```

## `convert`

Convert a source root into a Lilya target root.

```bash
lilya-converter convert SOURCE TARGET \
  [--source SOURCE_KEY] \
  [--dry-run] \
  [--diff] \
  [--copy-non-python/--no-copy-non-python] \
  [--report REPORT.json]
```

Examples:

```bash
lilya-converter convert ./fastapi_project ./lilya_project
lilya-converter convert ./flask_project ./lilya_project --source flask
lilya-converter convert ./litestar_project ./lilya_project --source litestar --dry-run --diff
lilya-converter convert ./starlette_project ./lilya_project --source starlette --report ./reports/convert.json
```

## `scaffold`

Generate a minimal Lilya scaffold informed by source analysis.

```bash
lilya-converter scaffold SOURCE TARGET [--source SOURCE_KEY] [--dry-run]
```

Examples:

```bash
lilya-converter scaffold ./fastapi_project ./lilya_scaffold
lilya-converter scaffold ./django_project ./lilya_scaffold --source django
```

## `map rules`

List all known conversion rules for one source framework.

```bash
lilya-converter map rules [--source SOURCE_KEY]
```

Example:

```bash
lilya-converter map rules --source starlette
```

## `map applied`

Show which rules were actually applied in a conversion report.

```bash
lilya-converter map applied ./reports/convert.json
```

## `verify`

Run structural checks on converted output.

```bash
lilya-converter verify TARGET [--source SOURCE_KEY] [--report REPORT.json]
```

Examples:

```bash
lilya-converter verify ./lilya_project
lilya-converter verify ./lilya_project --source django --report ./reports/verify.json
```

## What Verify Checks

- Python syntax validity.
- Remaining source-framework import/call patterns.
- Unresolved local imports.

## Suggested Production Routine

1. `analyze`
2. `convert --dry-run --diff`
3. `convert`
4. `verify`
5. `map applied`

For concrete output examples, see [Examples and Outputs](examples-and-outputs.md).
