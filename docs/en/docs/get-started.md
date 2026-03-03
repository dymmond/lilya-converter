# Get Started

This page gives you a production-safe quick start with Lilya Converter.

## 1. Install

```bash
pip install lilya-converter
```

## 2. Inspect your FastAPI project

```bash
lilya-converter analyze ./fastapi_project --output ./reports/scan.json
```

## 3. Preview conversion (no writes)

```bash
lilya-converter convert ./fastapi_project ./lilya_project --dry-run --diff --report ./reports/convert.json
```

## 4. Run conversion

```bash
lilya-converter convert ./fastapi_project ./lilya_project --report ./reports/convert.json
```

## 5. Verify target output

```bash
lilya-converter verify ./lilya_project --report ./reports/verify.json
```

## Typical workflow

1. Run `analyze` to understand patterns detected by the scanner.
2. Run `convert --dry-run --diff` to preview impact.
3. Run `convert` without dry-run.
4. Run `verify` and resolve diagnostics.
5. Commit converted output once checks pass.
