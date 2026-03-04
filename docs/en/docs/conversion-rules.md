# Conversion Rules

The converter applies deterministic, source-grounded mappings from each source framework to Lilya.

## Rule Model

- Rules are adapter-specific and explicitly registered.
- Each rule has a stable ID (`map rules`).
- Applied rules are reported per conversion (`map applied`).
- Unsupported or partial mappings emit diagnostics with file and line context.

## FastAPI Rules

### Imports and constructors

- FastAPI app/router imports map to Lilya imports.
- Response and middleware imports map only when Lilya has direct equivalents.
- Unsupported constructor kwargs are removed and reported.

### Routing and dependencies

- `include_router(...)` -> `include(path=..., app=...)`.
- `api_route(...)` and `trace(...)` normalize to Lilya route methods.
- Router `prefix=` is merged into route paths where deterministic.
- `Depends(...)` and `Annotated[..., Depends(...)]` are normalized to Lilya dependency maps.

### Middleware and handlers

- FastAPI exception-handler decorators become `add_exception_handler(...)` calls.
- Unsupported decorator middleware patterns are removed with diagnostics.

## Flask Rules

- Flask/Blueprint imports map to Lilya app/router imports.
- Blueprint `url_prefix` is merged into route decorators where deterministic.
- `register_blueprint(...)` -> `include(path=..., app=...)` with non-empty path normalization.
- Unsupported route and constructor kwargs are removed with diagnostics.

## Django Rules

- `django.urls.path(...)` and `re_path(...)` -> Lilya `Path(...)`.
- `django.urls.include(...)` -> Lilya `Include(path=..., app=...)`.
- `urlpatterns` modules are materialized as `app = Lilya(routes=urlpatterns)`.
- Converter syntax (`<int:id>`) is normalized to Lilya syntax (`{id:int}`).
- Project path mapping:
  - `management/commands/*` -> `directives/operations/*`.

## Litestar Rules

- Litestar imports map to Lilya app/routing imports.
- Module-level HTTP decorators (`@get`, `@post`, etc.) are converted to explicit `Path(...)` routes.
- `route_handlers` in `Litestar(...)` and `Router(...)` are normalized to Lilya `routes`.
- `Router(path=...)` is materialized via `Include(path=..., app=router)` at app level.

## Starlette Rules

- Starlette imports map to Lilya import aliases:
  - `Starlette` -> `Lilya`,
  - `Route` -> `Path`,
  - `Mount` -> `Include`,
  - `WebSocketRoute` -> `WebSocketPath`.
- `Route(...)`, `Mount(...)`, and `WebSocketRoute(...)` call signatures are normalized.
- `mount(...)` calls normalize to Lilya include semantics.
- `add_route(route=...)` calls normalize to `add_route(handler=...)`.

## Path Normalization

For frameworks with route/include path values, converter output enforces Lilya path expectations:

- path values are never empty,
- path values are normalized to start with `/` where deterministically possible.

## Worked Examples

### FastAPI dependencies

```python
{!> ../../../docs_src/conversion/dependencies_fastapi.py !}
```

```python
{!> ../../../docs_src/conversion/dependencies_lilya.py !}
```

### FastAPI complex conversion

```python
{!> ../../../docs_src/conversion/complex_fastapi.py !}
```

```python
{!> ../../../docs_src/conversion/complex_lilya.py !}
```

## Operational Guidance

- Run `map rules --source SOURCE_KEY` before conversion.
- Run `map applied REPORT.json` after conversion to audit triggered rules.
- Treat diagnostics as migration checklist items.
