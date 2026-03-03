# How To - Verify and Fix Conversion Issues

Run verification immediately after conversion:

```bash
lilya-converter verify ./lilya_project --report ./reports/verify.json
```

## What verify checks

- Python syntax validity in converted files.
- Remaining FastAPI imports/call patterns.
- Unresolved local import modules.

## Typical fixes

### `verify.fastapi_import_remaining`

- Open the referenced file.
- Replace remaining FastAPI-specific patterns manually.
- Re-run `verify`.

### `verify.unresolved_local_import`

- Confirm referenced module exists in target tree.
- Fix import path or move missing file.
- Re-run `verify`.

### `verify.syntax_error`

- Fix syntax at the reported line.
- Re-run `verify`.

## Tight feedback loop

```bash
lilya-converter convert ./fastapi_project ./lilya_project --dry-run --diff
lilya-converter convert ./fastapi_project ./lilya_project
lilya-converter verify ./lilya_project
```
