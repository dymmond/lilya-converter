# How To - Convert an Entire Project

Use this guide when you want to migrate a full FastAPI codebase to Lilya.

## Recommended command sequence

### 1. Analyze

```bash
lilya-converter analyze ./fastapi_project --output ./reports/scan.json
```

### 2. Dry-run with diff

```bash
lilya-converter convert ./fastapi_project ./lilya_project --dry-run --diff --report ./reports/convert.json
```

### 3. Convert for real

```bash
lilya-converter convert ./fastapi_project ./lilya_project --report ./reports/convert.json
```

### 4. Verify

```bash
lilya-converter verify ./lilya_project --report ./reports/verify.json
```

## Useful variants

Convert without copying non-Python files:

```bash
lilya-converter convert ./fastapi_project ./lilya_project --no-copy-non-python
```

Generate JSON scan output directly to stdout:

```bash
lilya-converter analyze ./fastapi_project --json
```

## Troubleshooting checklist

- Run `verify` after every real conversion run.
- Treat diagnostics as actionable migration tasks.
- Re-run `convert --dry-run --diff` after manual edits to validate deltas.
