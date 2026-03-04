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

**The official supported version is always the latest released**.

---

## Installation

```bash
pip install lilya-converter
```

## Start Here

1. [Get Started](get-started.md)
2. [First Conversion](tutorial-first-conversion.md)
3. [Guides](how-to-convert-project.md)
4. [Examples and Outputs](examples-and-outputs.md)
5. [Command Reference](commands.md)
6. [Adding a New Adapter](adding-adapter.md)

## Framework Support Matrix

| Source | Key | Status | Notes |
| --- | --- | --- | --- |
| FastAPI | `fastapi` | Stable | Default source and backwards-compatible CLI behavior |
| Flask | `flask` | Stable | Blueprint and route conversion |
| Django | `django` | Stable | URLConf conversion and management-command path remapping |
| Litestar | `litestar` | Stable | Decorator and route_handlers conversion |
| Starlette | `starlette` | Stable | Route/Mount conversion |

## What You Get

- Multi-framework adapter architecture.
- Deterministic conversion output.
- Rule-level diagnostics and reports.
- Dry-run and unified diff previews.
- Verification checks after conversion.

## Quick Command Preview

```python
{!> ../../../docs_src/cli/examples.py !}
```

## Conversion Preview

### FastAPI input

```python
{!> ../../../docs_src/conversion/fastapi_input.py !}
```

### Lilya output

```python
{!> ../../../docs_src/conversion/lilya_output.py !}
```

### Flask input

```python
{!> ../../../docs_src/conversion/flask_input.py !}
```

### Flask Lilya output

```python
{!> ../../../docs_src/conversion/flask_output.py !}
```

### Django URLConf input

```python
{!> ../../../docs_src/conversion/django_input_urls.py !}
```

### Django Lilya output

```python
{!> ../../../docs_src/conversion/django_output_urls.py !}
```

### Litestar input

```python
{!> ../../../docs_src/conversion/litestar_input.py !}
```

### Litestar Lilya output

```python
{!> ../../../docs_src/conversion/litestar_output.py !}
```

### Starlette input

```python
{!> ../../../docs_src/conversion/starlette_input.py !}
```

### Starlette Lilya output

```python
{!> ../../../docs_src/conversion/starlette_output.py !}
```
