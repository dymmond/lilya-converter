# Tutorial - First Conversion

Follow this step-by-step tutorial to migrate your first FastAPI project.

## Prerequisites

- Python 3.10+
- A FastAPI project directory (example: `./fastapi_project`)

## Step 1 - Install the CLI

```bash
pip install lilya-converter
```

## Step 2 - Analyze the project

```bash
lilya-converter analyze ./fastapi_project --output ./reports/scan.json
```

This tells you what the converter detected: routes, dependencies, middleware patterns, and potential unsupported constructs.

## Step 3 - Dry-run conversion with diff

```bash
lilya-converter convert ./fastapi_project ./lilya_project --dry-run --diff --report ./reports/convert.json
```

Review:
- terminal diff output,
- `./reports/convert.json` diagnostics,
- whether any manual follow-up is needed.

## Step 4 - Run actual conversion

```bash
lilya-converter convert ./fastapi_project ./lilya_project --report ./reports/convert.json
```

## Step 5 - Verify converted output

```bash
lilya-converter verify ./lilya_project --report ./reports/verify.json
```

## Step 6 - Inspect applied rules

```bash
lilya-converter map rules
lilya-converter map applied ./reports/convert.json
```

## Next

- For single-file migration, see [Convert a Single File](how-to-convert-single-file.md).
- For advanced command options, see [Command Reference](commands.md).
