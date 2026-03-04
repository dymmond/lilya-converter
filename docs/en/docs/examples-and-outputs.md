# Examples and Outputs

This page shows concrete source inputs, converted output, and report excerpts.

## FastAPI to Lilya Example

FastAPI input:

```python
{!> ../../../docs_src/conversion/fastapi_input.py !}
```

Converted Lilya output:

```python
{!> ../../../docs_src/conversion/lilya_output.py !}
```

## Flask to Lilya Example

Flask input:

```python
{!> ../../../docs_src/conversion/flask_input.py !}
```

Converted Lilya output:

```python
{!> ../../../docs_src/conversion/flask_output.py !}
```

## Example Analyze Output

```text
{!> ../../../docs_src/examples/analyze_stdout.txt !}
```

## Example `scan.json` Excerpt

```json
{!> ../../../docs_src/reports/scan_report_excerpt.json !}
```

## Example `convert.json` Excerpt

```json
{!> ../../../docs_src/reports/convert_report_excerpt.json !}
```

## Example `verify.json` Excerpt

```json
{!> ../../../docs_src/reports/verify_report_excerpt.json !}
```

## Reading The Reports

1. Use `scan.json` to confirm route/include detection before conversion.
2. Use `convert.json` to inspect rule application and warnings.
3. Use `verify.json` to identify residual source-framework artifacts.
