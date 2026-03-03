# Lilya Converter

`lilya_converter` is a deterministic FastAPI-to-Lilya conversion CLI built on top of Sayer.

It is designed for production migration workflows where you need:
- explicit conversion rules,
- actionable diagnostics,
- dry-run + diff preview,
- reproducible outputs and reports.

## Why It Exists

FastAPI and Lilya are both ASGI ecosystems, but they expose different routing, dependency, and metadata APIs.

`lilya_converter` bridges that gap by applying source-grounded AST transformations with explicit diagnostics when parity is partial or unsupported.

## What It Converts

- FastAPI app/router declarations and imports into Lilya equivalents.
- `include_router(...)` call sites into `include(path=..., app=...)`.
- Route dependency markers (`Depends(...)`) into Lilya `Provide`/`Provides` forms.
- FastAPI exception handler decorators into Lilya registration calls.
- Selected middleware/response import paths where direct Lilya equivalents exist.

## What Requires Manual Follow-up

- FastAPI function middleware decorators (`@app.middleware("http")`).
- Decorator kwargs without direct Lilya route arguments (for example `response_model`).
- Dynamic patterns that cannot be merged deterministically.

## End-to-End Workflow

1. Analyze your source project:

```bash
lilya-converter analyze ./fastapi_project --output ./reports/scan.json
```

2. Preview conversion and inspect diffs:

```bash
lilya-converter convert ./fastapi_project ./lilya_project --dry-run --diff --report ./reports/convert.json
```

3. Run real conversion:

```bash
lilya-converter convert ./fastapi_project ./lilya_project --report ./reports/convert.json
```

4. Verify the result:

```bash
lilya-converter verify ./lilya_project --report ./reports/verify.json
```

## CLI Examples

{!> ../../../docs_src/cli/examples.py !}

## Conversion Example

FastAPI input:

{!> ../../../docs_src/conversion/fastapi_input.py !}

Lilya output:

{!> ../../../docs_src/conversion/lilya_output.py !}

## Dependency Conversion Example

FastAPI dependency style:

{!> ../../../docs_src/conversion/dependencies_fastapi.py !}

Lilya dependency style:

{!> ../../../docs_src/conversion/dependencies_lilya.py !}

## Determinism Guarantees

- File traversal order is stable.
- Applied rules are sorted in reports.
- Diagnostics are sorted by file/line/code.
- Generated dependency maps use stable key ordering.

## Next Reads

- [Commands](commands.md)
- [Conversion Rules](conversion-rules.md)
- [Architecture](architecture.md)
- [Contributing](contributing.md)
