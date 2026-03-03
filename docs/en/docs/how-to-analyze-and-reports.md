# How To - Analyze and Work With Reports

Use this guide to inspect projects before and after conversion.

## Analyze report

Write structured scan report:

```bash
lilya-converter analyze ./fastapi_project --output ./reports/scan.json
```

Print full scan report JSON to stdout:

```bash
lilya-converter analyze ./fastapi_project --json
```

## Conversion report

```bash
lilya-converter convert ./fastapi_project ./lilya_project --report ./reports/convert.json
```

Use `map applied` to inspect rules used in that run:

```bash
lilya-converter map applied ./reports/convert.json
```

List all available rule IDs:

```bash
lilya-converter map rules
```

## Verify report

```bash
lilya-converter verify ./lilya_project --report ./reports/verify.json
```

## Practical report review order

1. `scan.json`: confirm detected structures are complete.
2. `convert.json`: inspect transformed files and diagnostics.
3. `verify.json`: check unresolved imports and remaining FastAPI artifacts.
