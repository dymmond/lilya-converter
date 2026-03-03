# Lilya Converter

<p align="center">
  <a href="https://lilya.dev"><img src="https://res.cloudinary.com/dymmond/image/upload/v1707501404/lilya/logo_quiotd.png" alt='Lilya'></a>
</p>

<p align="center">
    <em>Convert FastAPI codebases into Lilya using deterministic rules, explicit diagnostics, and reproducible reports.</em>
</p>

<p align="center">
<a href="https://github.com/dymmond/lilya-converter/actions/workflows/test-suite.yml/badge.svg?event=push&branch=main" target="_blank">
    <img src="https://github.com/dymmond/lilya-converter/actions/workflows/test-suite.yml/badge.svg?event=push&branch=main" alt="Test Suite">
</a>

<a href="https://pypi.org/project/lilya-converter" target="_blank">
    <img src="https://img.shields.io/pypi/v/lilya-converter?color=%2334D058&label=pypi%20package" alt="Package version">
</a>

<a href="https://pypi.org/project/lilya-converter" target="_blank">
    <img src="https://https://img.shields.io/pypi/pyversions/lilya-converter.svg?color=2334D058" alt="Supported Python versions">
</a>
</p>

---

**Documentation**: [https://lilya-converter.dymmond.com](https://lilya-converter.dymmond.com) 📚

**Source Code**: [https://github.com/dymmond/lilya-converter](https://github.com/dymmond/lilya-converter) 💻

**The official supported version is always the latest released**.

---

`lilya_converter` is a modular CLI that converts FastAPI projects into Lilya projects using AST-based, repo-grounded rules.

The converter is implemented with [Sayer](https://github.com/dymmond/sayer) commands and is built around:
- a project scanner,
- a deterministic transformation engine,
- safe file writing with dry-run and diff preview,
- structured conversion/verification reports.

## Scope

### What it does
- Scans FastAPI source trees (`analyze`) and reports detected apps, routers, routes, dependencies, middleware/event/exception patterns.
- Converts Python files with deterministic rule application (`convert`):
  - `FastAPI`/`APIRouter` imports mapped to Lilya imports.
  - `include_router(...)` converted to `include(path=..., app=...)`.
  - FastAPI `Depends(...)` route patterns converted to Lilya `Provide`/`Provides` dependency style.
  - `@app.exception_handler(...)` converted into `app.add_exception_handler(...)` registration calls.
  - FastAPI middleware import modules mapped to Lilya middleware modules where direct equivalents exist.
  - FastAPI `api_route`/`trace` decorators normalized to Lilya `route(..., methods=[...])`.
- Generates a Lilya scaffold entrypoint (`scaffold`).
- Shows mapping rules and applied mappings (`map rules`, `map applied`).
- Runs post-conversion structural checks (`verify`).

### What it does not do
- It does not fabricate unsupported runtime behavior.
- FastAPI function middleware (`@app.middleware("http")`) is reported for manual conversion.
- FastAPI `response_model` runtime filtering semantics are not auto-recreated in Lilya routes; unsupported decorator kwargs are removed and reported.
- Dynamic prefix/path merges that cannot be resolved deterministically are reported.

## Installation

```bash
pip install lilya-converter
```

For local development from source:

```bash
pip install -e .
```

CLI entrypoint:

```bash
lilya-converter --help
```

## Commands

### Analyze

```bash
lilya-converter analyze ./my-fastapi-app
lilya-converter analyze ./my-fastapi-app --json
lilya-converter analyze ./my-fastapi-app --output ./reports/scan.json
```

### Convert

```bash
lilya-converter convert ./my-fastapi-app ./my-lilya-app
lilya-converter convert ./my-fastapi-app ./my-lilya-app --dry-run --diff
lilya-converter convert ./my-fastapi-app ./my-lilya-app --report ./reports/convert.json
```

### Scaffold

```bash
lilya-converter scaffold ./my-fastapi-app ./my-lilya-scaffold
lilya-converter scaffold ./my-fastapi-app ./my-lilya-scaffold --dry-run
```

### Map

```bash
lilya-converter map rules
lilya-converter map applied ./reports/convert.json
```

### Verify

```bash
lilya-converter verify ./my-lilya-app
lilya-converter verify ./my-lilya-app --report ./reports/verify.json
```

## How Conversion Works

1. Scanner (`lilya_converter/scanner.py`) parses `.py` files with `ast` and collects conversion-relevant patterns.
2. Transformer (`lilya_converter/transformer.py`) applies rule-driven AST rewrites per file.
3. Engine (`lilya_converter/engine.py`) orchestrates conversion, report assembly, dry-run behavior, and writing.
4. Writer (`lilya_converter/writer.py`) handles deterministic file traversal and safe writes.

All outputs are deterministic:
- sorted file traversal,
- sorted rule/report entries,
- stable dependency map key ordering.

## Add a New Conversion Rule

1. Add transformation logic in [`lilya_converter/transformer.py`](/Users/tarsil/Projects/github/dymmond/lilya_converter/lilya_converter/transformer.py).
2. Register the rule id/summary in [`lilya_converter/rules.py`](/Users/tarsil/Projects/github/dymmond/lilya_converter/lilya_converter/rules.py).
3. Add unit tests for the transformation in [`tests/unit/test_transformer.py`](/Users/tarsil/Projects/github/dymmond/lilya_converter/tests/unit/test_transformer.py).
4. If behavior changes output, update golden fixtures in [`tests/fixtures/golden`](/Users/tarsil/Projects/github/dymmond/lilya_converter/tests/fixtures/golden).
5. Add or update integration assertions in [`tests/integration/test_golden_conversion.py`](/Users/tarsil/Projects/github/dymmond/lilya_converter/tests/integration/test_golden_conversion.py).

## Testing

Run full tests:

```bash
hatch run test:test -q
```

Current suite includes:
- rule/helper unit tests,
- scanner/engine tests,
- CLI integration tests,
- golden output tests,
- dry-run no-write checks,
- unsupported feature diagnostics checks,
- deterministic ordering checks.

## Building docs locally

The docs pipeline uses Zensical and a deterministic prebuild step:

```bash
hatch run docs:build
```

Useful docs commands:

```bash
hatch run docs:prepare  # expand include directives into build-ready markdown
hatch run docs:serve    # prepare + serve with live source watching on 127.0.0.1:8000
hatch run docs:clean    # remove generated docs/site/cache artifacts
```

The build command uses [`mkdocs.yaml`](/Users/tarsil/Projects/github/dymmond/lilya_converter/mkdocs.yaml) through Zensical compatibility and writes output to `site/`.

## Docs architecture

- Authoring sources live in [`docs/en/docs`](/Users/tarsil/Projects/github/dymmond/lilya_converter/docs/en/docs).
- Code/doc snippets are stored in [`docs_src`](/Users/tarsil/Projects/github/dymmond/lilya_converter/docs_src).
- Prebuild generation expands `{!> ... !}` include directives into concrete markdown under `docs/generated` using [`scripts/docs.py`](/Users/tarsil/Projects/github/dymmond/lilya_converter/scripts/docs.py) and [`scripts/docs_pipeline.py`](/Users/tarsil/Projects/github/dymmond/lilya_converter/scripts/docs_pipeline.py).
- Zensical renders the generated docs tree to static HTML in `site/`.
- Intentionally dropped MkDocs behaviors:
  - MkDocs hook callbacks (`scripts/hooks.py`) are removed.
  - `mkdocs-meta-descriptions-plugin` is removed from the active pipeline.
- Docs regression coverage is in [`tests/docs/test_docs_pipeline.py`](/Users/tarsil/Projects/github/dymmond/lilya_converter/tests/docs/test_docs_pipeline.py), including:
  - deterministic generated-markdown checks against fixture goldens,
  - docs build smoke assertions for key output artifacts,
  - checks that the active docs pipeline contains no MkDocs dependency/config.

## Troubleshooting

- If `verify` reports `verify.fastapi_import_remaining`, inspect files for unsupported patterns left intentionally unchanged.
- If route metadata kwargs are removed (`convert.route.kwargs_removed`), check Lilya route decorator signatures and reapply behavior manually where needed.
- If middleware decorators are removed (`convert.middleware.decorator_removed`), convert to class-based middleware patterns in Lilya.
