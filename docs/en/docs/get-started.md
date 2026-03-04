# Get Started

This page gives you a production-safe quick start with Lilya Converter.

## 1. Install

```bash
pip install lilya-converter
```

## 2. Pick source framework

- FastAPI: use default source (`fastapi`).
- Flask: pass `--source flask`.

## 3. Inspect your project

### FastAPI

```bash
lilya-converter analyze ./fastapi_project --output ./reports/scan.json
```

### Flask

```bash
lilya-converter analyze ./flask_project --source flask --output ./reports/scan.json
```

## 4. Preview conversion (no writes)

### FastAPI

```bash
lilya-converter convert ./fastapi_project ./lilya_project --dry-run --diff --report ./reports/convert.json
```

### Flask

```bash
lilya-converter convert ./flask_project ./lilya_project --source flask --dry-run --diff --report ./reports/convert.json
```

## 5. Run conversion

### FastAPI

```bash
lilya-converter convert ./fastapi_project ./lilya_project --report ./reports/convert.json
```

### Flask

```bash
lilya-converter convert ./flask_project ./lilya_project --source flask --report ./reports/convert.json
```

## 6. Verify target output

### FastAPI

```bash
lilya-converter verify ./lilya_project --report ./reports/verify.json
```

### Flask

```bash
lilya-converter verify ./lilya_project --source flask --report ./reports/verify.json
```

## Typical workflow

1. Run `analyze` to understand patterns detected by the active adapter.
2. Run `convert --dry-run --diff` to preview impact.
3. Run `convert` without dry-run.
4. Run `verify` and resolve diagnostics.
5. Commit converted output once checks pass.

For concrete sample outputs (`stdout`, `scan.json`, `convert.json`, `verify.json`), see [Examples and Outputs](examples-and-outputs.md).
