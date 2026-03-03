# Lilya Converter

Convert FastAPI codebases into Lilya using deterministic rules, explicit diagnostics, and reproducible reports.

## Install

```bash
pip install lilya-converter
```

## Start Here

1. [Get Started](get-started.md)
2. [Tutorial - First Conversion](tutorial-first-conversion.md)
3. [How-To Guides](how-to-convert-project.md)
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
