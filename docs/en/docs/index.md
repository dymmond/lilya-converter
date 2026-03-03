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
4. [Command Reference](commands.md)

## What You Get

- Deterministic conversion outputs.
- Rule-level diagnostics and reports.
- Dry-run and unified diff previews.
- Verification checks after conversion.

## Quick Command Preview

```python
{!> ../../../docs_src/cli/examples.py !}
```

## Conversion Preview

### FastAPI input:

```python
{!> ../../../docs_src/conversion/fastapi_input.py !}
```

### Lilya output:

```python
{!> ../../../docs_src/conversion/lilya_output.py !}
```
