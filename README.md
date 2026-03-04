# Lilya Converter

<p align="center">
  <a href="https://lilya.dev"><img src="https://res.cloudinary.com/dymmond/image/upload/v1707501404/lilya/logo_quiotd.png" alt='Lilya'></a>
</p>

<p align="center">
    <em>Convert FastAPI and Flask codebases into Lilya using deterministic rules, explicit diagnostics, and reproducible reports.</em>
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

Supported sources:

- `fastapi` (default; backwards compatible)
- `flask`

Architecture:

- framework-agnostic core orchestration,
- explicit adapter registry,
- framework-specific adapters,
- shared filesystem utilities,
- deterministic report/diagnostic models.

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

### FastAPI (default source)

```bash
lilya-converter analyze ./my-fastapi-app
lilya-converter convert ./my-fastapi-app ./my-lilya-app --dry-run --diff
lilya-converter convert ./my-fastapi-app ./my-lilya-app --report ./reports/convert.json
lilya-converter verify ./my-lilya-app --report ./reports/verify.json
```

### Flask

```bash
lilya-converter analyze ./my-flask-app --source flask
lilya-converter convert ./my-flask-app ./my-lilya-app --source flask --dry-run --diff
lilya-converter convert ./my-flask-app ./my-lilya-app --source flask --report ./reports/convert.json
lilya-converter verify ./my-lilya-app --source flask --report ./reports/verify.json
```

## Commands

```bash
lilya-converter analyze SOURCE [--source fastapi|flask] [--json] [--output REPORT.json]
lilya-converter convert SOURCE TARGET [--source fastapi|flask] [--dry-run] [--diff] [--report REPORT.json]
lilya-converter scaffold SOURCE TARGET [--source fastapi|flask] [--dry-run]
lilya-converter map rules [--source fastapi|flask]
lilya-converter map applied REPORT.json
lilya-converter verify TARGET [--source fastapi|flask] [--report REPORT.json]
```

## Adapter Extension Guide

See [Adding a New Adapter](docs/en/docs/adding-adapter.md) for:

- adapter package skeleton,
- explicit registry registration,
- test expectations,
- typing/docstring/error-handling conventions.

## Testing

Run full test suite:

```bash
hatch run test:test -q
```

## Building docs

```bash
hatch run docs:build
```
