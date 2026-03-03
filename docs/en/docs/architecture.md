# Architecture

This page describes internal converter architecture and extension points.

## Design Goals

- Deterministic output for repeatable migrations.
- Explicit diagnostics for unsupported/partial mappings.
- Modular architecture to add new rules safely.
- CLI-first workflows with report persistence.

## Module Responsibilities

## `lilya_converter/cli.py`

- Declares Sayer commands.
- Validates CLI inputs.
- Delegates orchestration to engine APIs.
- Renders status/diagnostic output.

## `lilya_converter/scanner.py`

- Performs non-mutating AST analysis.
- Extracts FastAPI structures relevant to conversion planning.
- Emits scanner diagnostics (for example unsupported middleware decorators).

## `lilya_converter/transformer.py`

- Performs AST rewrites per Python file.
- Maintains rule application state and diagnostics.
- Generates transformed source plus unified diff.

## `lilya_converter/engine.py`

- Coordinates scan/convert/scaffold/verify flows.
- Handles file iteration and write policy (`dry-run`, copy flags).
- Produces report objects for persistence and automation.

## `lilya_converter/writer.py`

- Deterministic file traversal.
- Safe writes and file copy helpers.

## `lilya_converter/models.py`

- Typed report/diagnostic domain model definitions.

## `lilya_converter/rules.py`

- Rule registry surfaced by map commands and reports.

## Conversion Flow

1. Source files are discovered in sorted order.
2. Python files are transformed via AST.
3. Diagnostics and applied rules are aggregated.
4. Files are written/copied depending on dry-run mode.
5. Structured reports are emitted.

## Verification Flow

1. Parse each Python file in target tree.
2. Record syntax errors.
3. Detect unresolved local imports.
4. Detect remaining FastAPI signatures/patterns.
5. Emit sorted diagnostics.

## Extension Guide

To add a new conversion rule:

1. Implement rule logic in `transformer.py`.
2. Register the rule in `rules.py`.
3. Add unit tests for transformation behavior.
4. Add or update fixture/golden integration tests.
5. Update command/docs examples if behavior changes user expectations.

## Testing Strategy

- Unit tests verify low-level scanner/transformer/writer/engine semantics.
- CLI tests validate command behavior and report handling.
- Golden tests compare converted file trees exactly.
- Dry-run tests ensure no writes occur.

## Determinism Guarantees

- Sorted filesystem traversal.
- Stable diagnostic ordering.
- Stable applied rule ordering.
- Stable dependency dictionary key ordering.
