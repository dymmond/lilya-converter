# Lilya Converter

<p align="center">
  <a href="https://lilya.dev"><img src="https://res.cloudinary.com/dymmond/image/upload/v1707501404/lilya/logo_quiotd.png" alt='Lilya'></a>
</p>

<p align="center">
    <em>Convert web framework codebases into Lilya with deterministic rules, explicit diagnostics, and reproducible reports.</em>
</p>

<p align="center">
<a href="https://github.com/dymmond/lilya-converter/actions/workflows/test-suite.yml/badge.svg?event=push&branch=main" target="_blank">
    <img src="https://github.com/dymmond/lilya-converter/actions/workflows/test-suite.yml/badge.svg?event=push&branch=main" alt="Test Suite">
</a>

<a href="https://pypi.org/project/lilya-converter" target="_blank">
    <img src="https://img.shields.io/pypi/v/lilya-converter?color=2334D058&label=pypi%20package" alt="Package version">
</a>

<a href="https://pypi.org/project/lilya-converter" target="_blank">
    <img src="https://img.shields.io/pypi/pyversions/lilya-converter.svg?color=2334D058" alt="Supported Python versions">
</a>
</p>

---

**Documentation**: [https://lilya-converter.dymmond.com](https://lilya-converter.dymmond.com) 📚

**Source Code**: [https://github.com/dymmond/lilya-converter](https://github.com/dymmond/lilya-converter) 💻

---

`lilya_converter` is a modular CLI for converting source framework projects into Lilya.

## Supported Sources

| Source | Key | Notes |
| --- | --- | --- |
| FastAPI | `fastapi` | Default source, backwards-compatible behavior |
| Flask | `flask` | Blueprint and route conversion |
| Django | `django` | URLConf conversion + management command path remap |
| Litestar | `litestar` | Decorator/route_handlers conversion |
| Starlette | `starlette` | Route/Mount conversion |

## Architecture

- framework-agnostic core orchestration,
- explicit adapter registry,
- framework-specific adapters,
- shared filesystem utilities,
- deterministic report and diagnostic models.

## Installation

```bash
pip install lilya-converter
```

For local development:

```bash
pip install -e .
```

CLI entrypoint:

```bash
lilya-converter --help
```

## Usage

FastAPI remains the default source:

```bash
lilya-converter analyze ./my-fastapi-app
lilya-converter convert ./my-fastapi-app ./my-lilya-app --dry-run --diff
```

Select another framework explicitly:

```bash
lilya-converter analyze ./my-django-app --source django
lilya-converter convert ./my-flask-app ./my-lilya-app --source flask
lilya-converter convert ./my-litestar-app ./my-lilya-app --source litestar
lilya-converter convert ./my-starlette-app ./my-lilya-app --source starlette
lilya-converter verify ./my-lilya-app --source django --report ./reports/verify.json
```

## Commands

```bash
lilya-converter analyze SOURCE [--source SOURCE_KEY] [--json] [--output REPORT.json]
lilya-converter convert SOURCE TARGET [--source SOURCE_KEY] [--dry-run] [--diff] [--report REPORT.json]
lilya-converter scaffold SOURCE TARGET [--source SOURCE_KEY] [--dry-run]
lilya-converter map rules [--source SOURCE_KEY]
lilya-converter map applied REPORT.json
lilya-converter verify TARGET [--source SOURCE_KEY] [--report REPORT.json]
```

Run `lilya-converter convert --help` to see supported source keys in deterministic order.

## Adapter Extension Guide

See [Adding a New Adapter](docs/en/docs/adding-adapter.md) for:

- adapter package skeleton,
- explicit registry registration,
- test expectations,
- typing, docstring, and error-handling conventions.

## Testing

Run full test suite:

```bash
hatch run test:test -q
```

## Building docs

```bash
hatch run docs:build
```
