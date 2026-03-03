# How To - Convert a Single File

The converter works on a source root directory.
To convert one file safely, use a minimal directory containing only that file (and any local modules it imports).

## Single-file workflow

Assume you want to convert:

- source file: `./fastapi_project/app/main.py`

### 1. Create a minimal source root

```bash
mkdir -p ./tmp-single-source/app
cp ./fastapi_project/app/main.py ./tmp-single-source/app/main.py
```

If `main.py` imports local modules, copy those modules too.

### 2. Run conversion against that minimal root

```bash
lilya-converter convert ./tmp-single-source ./tmp-single-target --report ./reports/convert-single.json
```

### 3. Verify output

```bash
lilya-converter verify ./tmp-single-target --report ./reports/verify-single.json
```

### 4. Apply result back to your project

```bash
cp ./tmp-single-target/app/main.py ./fastapi_project/app/main.py
```

## Dry-run version

```bash
lilya-converter convert ./tmp-single-source ./tmp-single-target --dry-run --diff --report ./reports/convert-single.json
```
