# Get Started

This page gives you a production-safe quick start with Lilya Converter.

## 1. Install

```bash
pip install lilya-converter
```

## 2. Choose a source key

| Framework | Source key |
| --- | --- |
| FastAPI | `fastapi` (default) |
| Flask | `flask` |
| Django | `django` |
| Litestar | `litestar` |
| Starlette | `starlette` |

## 3. Inspect your project

```bash
lilya-converter analyze ./source_project --source SOURCE_KEY --output ./reports/scan.json
```

FastAPI shorthand (default source):

```bash
lilya-converter analyze ./fastapi_project --output ./reports/scan.json
```

## 4. Preview conversion (no writes)

```bash
lilya-converter convert ./source_project ./lilya_project \
  --source SOURCE_KEY \
  --dry-run \
  --diff \
  --report ./reports/convert.json
```

## 5. Run conversion

```bash
lilya-converter convert ./source_project ./lilya_project --source SOURCE_KEY --report ./reports/convert.json
```

## 6. Verify target output

```bash
lilya-converter verify ./lilya_project --source SOURCE_KEY --report ./reports/verify.json
```

## 7. Example source selections

```bash
lilya-converter convert ./fastapi_project ./lilya_project
lilya-converter convert ./flask_project ./lilya_project --source flask
lilya-converter convert ./django_project ./lilya_project --source django
lilya-converter convert ./litestar_project ./lilya_project --source litestar
lilya-converter convert ./starlette_project ./lilya_project --source starlette
```

## Typical workflow

1. Run `analyze` to inspect patterns detected by the selected adapter.
2. Run `convert --dry-run --diff` to preview impact.
3. Run `convert` without dry-run.
4. Run `verify` and resolve diagnostics.
5. Commit converted output once checks pass.

For concrete `stdout` and report examples, see [Examples and Outputs](examples-and-outputs.md).
