# Conversion Rules

This converter applies only source-grounded mappings found in local FastAPI/Lilya/Sayer repositories.

## Rule Categories

## Import and Constructor Rules

- FastAPI app/router imports map to Lilya app/router imports.
- Response/middleware import modules are mapped only when Lilya has direct equivalents.
- Unsupported constructor kwargs are removed and reported.

## Routing Rules

- `include_router(...)` becomes `include(path=..., app=...)`.
- `api_route(...)` becomes `route(..., methods=[...])`.
- `trace(...)` becomes `route(..., methods=["TRACE"])`.
- Router `prefix=` is extracted and merged into route paths where deterministic.

## Dependency Rules

- Signature defaults `Depends(dep)` become `Provide(dep)` route dependencies + `Provides()` defaults.
- `Annotated[..., Depends(dep)]` metadata is normalized to Lilya dependency maps.
- Decorator/constructor dependency lists are converted to dependency dictionaries.

## Error and Middleware Rules

- `@app.exception_handler(ExceptionType)` becomes `app.add_exception_handler(ExceptionType, handler)`.
- FastAPI function middleware decorators are removed with explicit diagnostics.
- Class middleware imports/calls are preserved where direct Lilya mapping exists.

## Complex Conversion Behaviors

## Router Prefix Handling

FastAPI commonly combines router prefixes and include prefixes.

Converter behavior:
- route paths receive extracted router prefixes,
- include paths preserve explicit include prefixes,
- dynamic combinations that cannot be resolved deterministically are reported.

## Dependency Layering

Dependencies can exist simultaneously at:
- app/router constructors,
- include-router call sites,
- route decorators,
- route handler signatures.

Converter behavior:
- merges dependency layers into Lilya route/include-compatible dependency dictionaries,
- generates deterministic synthetic names where needed,
- reports unsupported shapes.

## Response Metadata Gaps

FastAPI metadata like `response_model` does not map 1:1 to Lilya route decorator arguments.

Converter behavior:
- removes unsupported kwargs,
- preserves executable handler code,
- emits diagnostics for manual review.

## Worked Dependency Example

FastAPI:

```python
{!> ../../../docs_src/conversion/dependencies_fastapi.py !}
```

Lilya:

```python
{!> ../../../docs_src/conversion/dependencies_lilya.py !}
```

## Worked Complex Example

FastAPI:

```python
{!> ../../../docs_src/conversion/complex_fastapi.py !}
```

Lilya:

```python
{!> ../../../docs_src/conversion/complex_lilya.py !}
```

## Operational Guidance

- Use `map rules` before conversion to inspect available mappings.
- Use `map applied` after conversion to audit which rules were triggered.
- Treat diagnostics as required migration checklist items.
