# Research Notes (Repo-Grounded)

Date: 2026-03-03

This document records only patterns verified in these local repos:
- `/Users/tarsil/Projects/github/dymmond/sayer`
- `/Users/tarsil/Projects/github/opensource/fastapi`
- `/Users/tarsil/Projects/github/dymmond/lilya`

## 1) Sayer CLI Ground Truth

### 1.1 Application and command model
- Sayer apps are created with `Sayer(...)` and commands are registered with `@app.command(...)`.
- The app is executed via `app()`/`app.run(...)`.
- Citations:
  - `/Users/tarsil/Projects/github/dymmond/sayer/sayer/app.py:31` (`class Sayer`)
  - `/Users/tarsil/Projects/github/dymmond/sayer/sayer/app.py:355` (`def command(self, *args, **kwargs)`)
  - `/Users/tarsil/Projects/github/dymmond/sayer/sayer/app.py:400` (`def run(self, args: list[str] | None = None)`)

### 1.2 Parameter style
- Sayer supports typed command params and metadata via `Annotated[..., Option/Argument/Param/Env/JsonParam]`.
- Citations:
  - `/Users/tarsil/Projects/github/dymmond/sayer/sayer/params.py`
  - `/Users/tarsil/Projects/github/dymmond/sayer/tests/test_callback.py` (multiple `Annotated[..., Option(...)]` usages)

### 1.3 Testing style
- Sayer’s own tests use `SayerTestClient(...).invoke([...])` (Click runner wrapper) for CLI assertions.
- Citations:
  - `/Users/tarsil/Projects/github/dymmond/sayer/sayer/testing.py:27` (`class SayerTestClient`)
  - `/Users/tarsil/Projects/github/dymmond/sayer/sayer/testing.py:41` (`def invoke(...)`)
  - `/Users/tarsil/Projects/github/dymmond/sayer/tests/test_sayer_client.py`

## 2) Lilya Ground Truth (Target Runtime)

### 2.1 App and routing primitives
- Primary app is `Lilya(...)`.
- Routing can be declared with:
  - decorators (`@app.get`, `@app.post`, etc.)
  - explicit `Path(path, handler, methods=[...])`
  - nested routing via `Include(path, app=...)` or `Include(path, routes=[...])`.
- Citations:
  - `/Users/tarsil/Projects/github/dymmond/lilya/lilya/apps.py:633` (`class Lilya`)
  - `/Users/tarsil/Projects/github/dymmond/lilya/lilya/routing/router.py:561` (`def add_route`)
  - `/Users/tarsil/Projects/github/dymmond/lilya/lilya/routing/router.py:514` (`def include`)
  - `/Users/tarsil/Projects/github/dymmond/lilya/lilya/routing/mixins.py` (method decorators)
  - `/Users/tarsil/Projects/github/dymmond/lilya/docs_src/routing/router/childlilya/app.py`

### 2.2 Dependency injection model
- Dependency providers are registered in maps like `dependencies={"x": Provide(...)}` at app/include/path levels.
- Handler consumption patterns:
  - explicit marker: `x=Provides()`
  - implicit name injection: parameter name present in merged dependency map with empty default.
- Resolution behavior confirms only requested/signature-matching dependencies are resolved.
- Citations:
  - `/Users/tarsil/Projects/github/dymmond/lilya/lilya/dependencies.py:56` (`class Provide`)
  - `/Users/tarsil/Projects/github/dymmond/lilya/lilya/dependencies.py:339` (`class Provides`)
  - `/Users/tarsil/Projects/github/dymmond/lilya/tests/dependencies/test_dependencies.py:35` (`x=Provides()`)
  - `/Users/tarsil/Projects/github/dymmond/lilya/lilya/_internal/_responses.py:1021-1042` (requested dependency selection logic)

### 2.3 Query/Header/Cookie parameter markers
- Lilya has native parameter markers:
  - `lilya.params.Query`
  - `lilya.params.Header`
  - `lilya.params.Cookie`
- Handler signatures use defaults like `q: str = Query()`.
- Citations:
  - `/Users/tarsil/Projects/github/dymmond/lilya/lilya/params.py:21`
  - `/Users/tarsil/Projects/github/dymmond/lilya/tests/params/test_query_params.py`
  - `/Users/tarsil/Projects/github/dymmond/lilya/tests/params/test_headers.py`
  - `/Users/tarsil/Projects/github/dymmond/lilya/tests/params/test_cookie.py`

### 2.4 Middleware model
- Middleware is configured with `DefineMiddleware(SomeMiddleware, **kwargs)` and attached via `Lilya(..., middleware=[...])`.
- Citations:
  - `/Users/tarsil/Projects/github/dymmond/lilya/lilya/middleware/base.py:12` (`class DefineMiddleware`)
  - `/Users/tarsil/Projects/github/dymmond/lilya/docs_src/middleware/adding_middleware.py`

### 2.5 Lifespan/events
- Supported patterns:
  - `on_startup=[...]`, `on_shutdown=[...]`
  - `lifespan=asynccontextmanager(...)`
- Citations:
  - `/Users/tarsil/Projects/github/dymmond/lilya/lilya/apps.py:880` onward (`on_startup`, `on_shutdown`, `lifespan` args)
  - `/Users/tarsil/Projects/github/dymmond/lilya/docs_src/events/start_shutdown.py`
  - `/Users/tarsil/Projects/github/dymmond/lilya/docs_src/events/lifespan.py`

### 2.6 Exception handlers
- App-level `exception_handlers={ExcType: handler}` is supported.
- Citations:
  - `/Users/tarsil/Projects/github/dymmond/lilya/lilya/apps.py` (constructor `exception_handlers`)
  - `/Users/tarsil/Projects/github/dymmond/lilya/docs_src/exception_handlers/example_use.py`
  - `/Users/tarsil/Projects/github/dymmond/lilya/tests/exception_handlers/test_exception_handlers.py`

### 2.7 OpenAPI/docs in Lilya
- OpenAPI can be enabled with `enable_openapi=True` and enhanced with `@openapi(...)` metadata decorators.
- Citations:
  - `/Users/tarsil/Projects/github/dymmond/lilya/lilya/apps.py:1102` (`enable_openapi`)
  - `/Users/tarsil/Projects/github/dymmond/lilya/docs_src/openapi/example.py`
  - `/Users/tarsil/Projects/github/dymmond/lilya/lilya/contrib/openapi/decorator.py`

## 3) FastAPI Ground Truth (Source Patterns to Parse)

### 3.1 App/router construction
- Primary app: `FastAPI(...)`.
- Router: `APIRouter(...)`, included via `app.include_router(router, prefix=..., dependencies=..., tags=...)`.
- Citations:
  - `/Users/tarsil/Projects/github/opensource/fastapi/fastapi/applications.py:45` (`class FastAPI`)
  - `/Users/tarsil/Projects/github/opensource/fastapi/fastapi/routing.py:1001` (`class APIRouter`)
  - `/Users/tarsil/Projects/github/opensource/fastapi/fastapi/applications.py:1359` (`include_router`)
  - `/Users/tarsil/Projects/github/opensource/fastapi/docs_src/bigger_applications/app_an_py310/main.py`

### 3.2 Path operation decorators and metadata
- Decorators support `response_model`, `status_code`, `response_class`, `responses`, etc.
- Citations:
  - `/Users/tarsil/Projects/github/opensource/fastapi/fastapi/applications.py:1162` (`add_api_route`)
  - `/Users/tarsil/Projects/github/opensource/fastapi/fastapi/routing.py:1332` (`APIRouter.add_api_route`)
  - `/Users/tarsil/Projects/github/opensource/fastapi/docs_src/response_model/tutorial001_py310.py`
  - `/Users/tarsil/Projects/github/opensource/fastapi/docs_src/custom_response/tutorial001_py310.py`
  - `/Users/tarsil/Projects/github/opensource/fastapi/docs_src/response_status_code/tutorial001_py310.py`

### 3.3 Dependency syntax
- `Depends` is a dataclass marker (`dependency`, `use_cache`, `scope`).
- Dependency uses appear in:
  - function signature defaults: `x=Depends(dep)`
  - `Annotated[..., Depends(dep)]`
  - decorator lists: `dependencies=[Depends(dep)]`
  - app/router constructor lists.
- Citations:
  - `/Users/tarsil/Projects/github/opensource/fastapi/fastapi/params.py:747` (`class Depends`)
  - `/Users/tarsil/Projects/github/opensource/fastapi/fastapi/param_functions.py:2284` (`def Depends(...)`)
  - `/Users/tarsil/Projects/github/opensource/fastapi/docs_src/dependencies/tutorial012_py310.py`
  - `/Users/tarsil/Projects/github/opensource/fastapi/docs_src/bigger_applications/app_an_py310/routers/items.py`

### 3.4 Middleware, lifespan/events, exception handlers
- Middleware patterns:
  - `app.add_middleware(SomeMiddleware, ...)`
  - `@app.middleware("http")` function middleware.
- Events/lifespan patterns:
  - `@app.on_event("startup"|"shutdown")`
  - `FastAPI(lifespan=...)`.
- Exception handlers:
  - decorator `@app.exception_handler(SomeException)`
  - constructor `exception_handlers={...}`.
- Citations:
  - `/Users/tarsil/Projects/github/opensource/fastapi/fastapi/applications.py:4629` (`middleware` decorator)
  - `/Users/tarsil/Projects/github/opensource/fastapi/docs_src/advanced_middleware/tutorial002_py310.py`
  - `/Users/tarsil/Projects/github/opensource/fastapi/docs_src/middleware/tutorial001_py310.py`
  - `/Users/tarsil/Projects/github/opensource/fastapi/docs_src/events/tutorial001_py310.py`
  - `/Users/tarsil/Projects/github/opensource/fastapi/docs_src/events/tutorial003_py310.py`
  - `/Users/tarsil/Projects/github/opensource/fastapi/docs_src/handling_errors/tutorial003_py310.py`

## 4) Repo-Grounded Conversion Strategy (Initial)

### 4.1 Core mappings to implement
- `FastAPI(...)` -> `Lilya(...)` with mapped kwargs where equivalent exists.
- `APIRouter(...)` -> `Router(...)` and `app.include_router(...)` -> `Include(...)` route nesting.
- FastAPI route decorators (`get/post/put/delete/patch/options/head`) -> Lilya route decorators.
- FastAPI dependency signatures (`Depends`) -> Lilya dependency map (`Provide`) + handler consumption (`Provides`).
- FastAPI `Query/Header/Cookie` defaults -> Lilya `Query/Header/Cookie` defaults (where structurally mappable).
- FastAPI `on_event` / `lifespan` -> Lilya `on_startup`/`on_shutdown`/`lifespan`.
- FastAPI `exception_handlers` -> Lilya `exception_handlers`.

### 4.2 Deterministic generation requirements
- Stable file discovery order (sorted paths).
- Stable import rendering order.
- Stable rule execution order and report ordering.

## 5) Confirmed Gaps / Risk Areas

- FastAPI decorator middleware (`@app.middleware("http")`) has no direct equivalent pattern in Lilya docs/source that accepts `(request, call_next)` middleware functions.
- Repo-grounded fallback: detect and report as unsupported; do not auto-generate behavior-altering middleware shims unless directly backed by Lilya patterns.
- Evidence:
  - FastAPI function middleware pattern: `/Users/tarsil/Projects/github/opensource/fastapi/docs_src/middleware/tutorial001_py310.py`
  - Lilya middleware model is class-based ASGI middleware with `DefineMiddleware`: `/Users/tarsil/Projects/github/dymmond/lilya/lilya/middleware/base.py`.

- FastAPI runtime response filtering semantics via `response_model` do not have a 1:1 explicit route-argument equivalent in Lilya routing APIs.
- Repo-grounded fallback: preserve handler code and optionally map documentation-oriented metadata through Lilya OpenAPI decorator when safe, otherwise report as partial conversion.
- Evidence:
  - FastAPI route `response_model` in `add_api_route`: `/Users/tarsil/Projects/github/opensource/fastapi/fastapi/routing.py:1332`
  - Lilya routing `Path`/decorators do not expose `response_model` argument: `/Users/tarsil/Projects/github/dymmond/lilya/lilya/routing/router.py:561`, `/Users/tarsil/Projects/github/dymmond/lilya/lilya/routing/mixins.py`.
