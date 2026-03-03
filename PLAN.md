# PLAN — MkDocs to Zensical Migration

## 0) Recon and grounding

- [x] Inspect current docs toolchain in this repo (`docs/en/mkdocs.yml`, `scripts/docs.py`, `scripts/hooks.py`, docs tree, dependency and CI wiring).
- [x] Inspect Zensical source repo for authoritative behavior (CLI, config parser, typed config schema, plugin/compatibility model, output behavior).
- [x] Write grounded findings and MkDocs->Zensical mappings to `docs/research-notes.md`.

## 1) Minimal Zensical migration

- [x] Add a Zensical-compatible root config file (`mkdocs.yaml`) with minimal working settings (`site_name`, `docs_dir`, `site_dir`, nav, theme).
- [x] Remove MkDocs-only config usage from active docs pipeline (`docs/en/mkdocs.yml` removed from active build path).
- [x] Ensure a clean `zensical build` path works from repository root through scriptable command(s).

## 2) Theme/nav/assets parity (supported subset only)

- [x] Map current docs metadata (name/description/url/repo/edit) into Zensical-compatible keys proven by source.
- [x] Map current navigation structure into the active config nav entries.
- [x] Map current palette/features/icons/logo/favicon only where Zensical typed config supports them.
- [x] Remove/avoid unsupported or unproven MkDocs theme keys.

## 3) Plugin and extension migration

- [x] Classify current MkDocs plugins into direct support/compatibility/unsupported in `docs/research-notes.md` with repo evidence.
- [x] Keep `search` only if configured through Zensical-supported plugin model.
- [x] Remove unsupported plugin configuration (`meta-descriptions`) from active build config.
- [x] Replace MkDocs-hook-dependent behavior with deterministic prebuild logic in local scripts.
- [x] Eliminate runtime dependence on MkDocs include/plugin hooks by generating Markdown content before `zensical build`.

## 4) `scripts/docs` refactor

- [x] Rewrite `scripts/docs.py` to remove MkDocs imports and MkDocs CLI invocation.
- [x] Add deterministic prebuild step that renders include snippets into build-ready Markdown.
- [x] Add `build` and `serve` commands using `zensical` CLI.
- [x] Add a reproducible clean/prepare flow for generated docs artifacts.
- [x] Remove or retire obsolete MkDocs hook file (`scripts/hooks.py`) if no longer used.

## 5) Dependency, task, and CI updates

- [x] Update docs environment dependencies in `pyproject.toml`:
  - [x] Remove MkDocs/MkDocs Material/MkDocs plugin dependencies not required after migration.
  - [x] Add `zensical` dependency with version constraints aligned to project style.
- [x] Update hatch docs scripts to use new `scripts/docs.py` commands.
- [x] Update `Taskfile.yaml` docs tasks to call the updated hatch docs scripts.
- [x] Update CI workflow(s) to run docs build and docs tests.

## 6) Testing (local + CI)

- [x] Add docs build smoke test that executes the docs pipeline and asserts command success.
- [x] Assert generated artifact directory exists and includes key files (`index.html`, key nav pages, `search.json`).
- [x] Add tests for deterministic generated Markdown output from `scripts/docs` (fixture + golden comparison).
- [x] Assert generated docs content is included in final docs source used for build.
- [x] Add regression check that MkDocs dependencies/config are removed from active pipeline unless explicitly justified.

## 7) Documentation updates

- [x] Update `README.md` with:
  - [x] “Building docs locally” using the new Zensical pipeline.
  - [x] “Docs architecture” (source docs, generated docs, build output, test strategy).
- [x] Update docs contributor instructions that still mention MkDocs-specific commands/assumptions.
- [x] Document known limitations or intentionally dropped MkDocs behaviors.

## 8) Verification and final audit

- [x] Run targeted docs tests locally.
- [x] Run full project tests if impacted by dependency/script changes.
- [x] Confirm no active `mkdocs` CLI/API usage remains in docs build path.
- [x] Re-check `PLAN.md` and mark completed items accurately.
