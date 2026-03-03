# Docs Toolchain Migration Research Notes

Date: 2026-03-03

## Scope and method

This document is grounded in direct file inspection of:
- Current repository: `/Users/tarsil/Projects/github/dymmond/lilya_converter`
- Zensical source repository (local clone): `/Users/tarsil/Projects/github/opensource/zensical`

No configuration key or CLI behavior is treated as supported unless it appears in the inspected source files below.

## 1) Current repository discovery (MkDocs state)

### 1.1 Primary MkDocs config and docs tree

Evidence:
- `/Users/tarsil/Projects/github/dymmond/lilya_converter/docs/en/mkdocs.yml`
- `/Users/tarsil/Projects/github/dymmond/lilya_converter/docs/en/docs/*.md`

Observed:
- Config file is `docs/en/mkdocs.yml` (not repo-root).
- Content source lives in `docs/en/docs`.
- Current nav is explicit (`Introduction`, `Commands`, `Conversion Rules`, etc.).
- Theme is `material` and includes palette/features/logo/favicon fields.
- Plugins currently configured:
  - `search`
  - `meta-descriptions`
- Markdown extensions configured include:
  - `toc`, `admonition`, `attr_list`, `md_in_html`, `extra`
  - `pymdownx.superfences` with Mermaid custom fence
  - `pymdownx.tabbed`
  - `mdx_include`
- `hooks` points to `../../scripts/hooks.py`.

### 1.2 Custom docs scripts depending on MkDocs internals

Evidence:
- `/Users/tarsil/Projects/github/dymmond/lilya_converter/scripts/docs.py`
- `/Users/tarsil/Projects/github/dymmond/lilya_converter/scripts/hooks.py`

Observed in `scripts/docs.py`:
- Imports MkDocs internals directly:
  - `mkdocs.commands.build`
  - `mkdocs.commands.serve`
  - `mkdocs.config`
  - `mkdocs.utils`
- Calls CLI `mkdocs build --site-dir ...` via subprocess.
- Contains translation-oriented config mutation logic for `docs/language_names.yml` and `extra.alternate`.
- Implements multi-language build orchestration (`build-all`, `new-lang`, etc.).

Observed in `scripts/hooks.py`:
- Implements MkDocs hook functions (`on_config`, `on_files`, `on_nav`, `on_page_markdown`, etc.).
- Uses MkDocs types from `mkdocs.structure.*` and `MkDocsConfig`.
- Injects missing-translation banner and file fallback behavior from `en`.

### 1.3 Automation and dependency integration

Evidence:
- `/Users/tarsil/Projects/github/dymmond/lilya_converter/pyproject.toml`
- `/Users/tarsil/Projects/github/dymmond/lilya_converter/Taskfile.yaml`
- `/Users/tarsil/Projects/github/dymmond/lilya_converter/.github/workflows/test-suite.yml`

Observed:
- Docs env depends on `mkdocs`, `mkdocs-material`, `mkdocs-meta-descriptions-plugin`, `mkdocs-macros-plugin`, `mkdocstrings`, `mdx-include`.
- Hatch docs scripts call `scripts/docs.py` and MkDocs-specific flows.
- Taskfile `build`/`serve` docs tasks route to hatch docs scripts.
- CI currently ignores `docs/**` in test workflow paths and has no docs build validation job.

## 2) Zensical source discovery (authoritative behavior)

### 2.1 CLI commands, config file discovery, and flags

Evidence:
- `/Users/tarsil/Projects/github/opensource/zensical/python/zensical/main.py`

Observed:
- Commands:
  - `zensical build`
  - `zensical serve`
  - `zensical new`
- `build` and `serve` support `--config-file` (`-f`).
- If config file is not provided, command searches in order:
  1. `zensical.toml`
  2. `mkdocs.yml`
  3. `mkdocs.yaml`
- `build` supports `--clean`; `serve` supports `--dev-addr`, `--open`.
- `--strict` exists but currently prints a warning: unsupported.

### 2.2 Config format and parsing model

Evidence:
- `/Users/tarsil/Projects/github/opensource/zensical/python/zensical/config.py`
- `/Users/tarsil/Projects/github/opensource/zensical/crates/zensical/src/config.rs`

Observed:
- Parsing supports:
  - TOML (`parse_zensical_config`) with optional `[project]` root table.
  - YAML MkDocs compatibility (`parse_mkdocs_config`).
- Required key: `site_name`.
- Defaults include:
  - `site_dir = "site"`
  - `docs_dir = "docs"`
  - `use_directory_urls = true`
  - `dev_addr = "localhost:8000"`
- `site_dir` and `docs_dir` must not contain `..`.
- Rust `Config::new` comments explicitly state support for both `mkdocs.yml` and `zensical.toml`, with Python-side parsing retained for compatibility.

### 2.3 Supported project/theme/search config surfaces

Evidence:
- `/Users/tarsil/Projects/github/opensource/zensical/crates/zensical/src/config/project.rs`
- `/Users/tarsil/Projects/github/opensource/zensical/crates/zensical/src/config/theme.rs`
- `/Users/tarsil/Projects/github/opensource/zensical/crates/zensical/src/config/plugins.rs`
- `/Users/tarsil/Projects/github/opensource/zensical/python/zensical/bootstrap/zensical.toml`

Observed:
- Project fields include:
  - core site metadata, repo fields, `nav`, `extra_css`, `extra_javascript`, `extra_templates`, `markdown_extensions` (via `mdx_configs`), and `plugins`.
- Theme fields include:
  - `variant`, `language`, `direction`, `features`, `font`, `favicon`, `logo`, `icon`, `palette`, `custom_dir`.
- Plugins represented in Rust config are only:
  - `search` (`enabled`, `separator`)
  - `offline` (`enabled`)
- `extra_javascript` is normalized to structured objects with keys: `path`, `type`, `async`, `defer`.

### 2.4 Markdown and compatibility model

Evidence:
- `/Users/tarsil/Projects/github/opensource/zensical/python/zensical/markdown.py`
- `/Users/tarsil/Projects/github/opensource/zensical/python/zensical/config.py`
- `/Users/tarsil/Projects/github/opensource/zensical/python/zensical/compat/mkdocstrings.py`
- `/Users/tarsil/Projects/github/opensource/zensical/python/zensical/compat/autorefs.py`

Observed:
- Markdown rendering uses Python Markdown directly:
  - `Markdown(extensions=config["markdown_extensions"], extension_configs=config["mdx_configs"])`
- Extension config conversion exists (`_convert_markdown_extensions`), including support for dict/list extension definitions.
- Explicit compat shims exist for:
  - `mkdocstrings`
  - `mkdocs-autorefs`
- No generic MkDocs plugin runtime is implemented in inspected files.

### 2.5 Navigation and build outputs

Evidence:
- `/Users/tarsil/Projects/github/opensource/zensical/crates/zensical/src/structure/nav.rs`
- `/Users/tarsil/Projects/github/opensource/zensical/crates/zensical/src/workflow.rs`
- `/Users/tarsil/Projects/github/opensource/zensical/crates/zensical/src/config.rs`

Observed:
- Navigation behavior:
  - explicit nav supported
  - implicit nav generated from docs tree when `nav` is empty
- Build writes into resolved `site_dir`.
- Build process creates/copies:
  - rendered pages
  - static assets
  - `search.json`
  - optionally `search.js` when offline plugin enabled
  - `objects.inv` when mkdocstrings inventory exists

## 3) MkDocs feature-by-feature mapping for this repo

Mapping is based on current usage in `docs/en/mkdocs.yml` and scripts under `scripts/`.

### 3.1 Config and metadata

- `site_name`, `site_description`, `site_url`, `repo_name`, `repo_url`, `edit_uri`
  - Status: **Supported in Zensical project config**
  - Evidence: `python/zensical/config.py`, `crates/zensical/src/config/project.rs`

### 3.2 Theme settings currently used

- `theme.language`
  - Status: **Supported** (`project.theme.language`)
- `theme.palette` (scheme/media/primary/accent/toggle)
  - Status: **Supported**
- `theme.features`
  - Status: **Supported**
- `theme.logo`, `theme.favicon`
  - Status: **Supported**
- `theme.name: material`
  - Status: **Not a typed Zensical theme field** in Rust `Theme` struct.
  - Migration approach: use Zensical theme fields (`variant`, `palette`, `features`, etc.), not MkDocs theme-name switching.

### 3.3 Navigation

- `nav` list with title->file mappings
  - Status: **Supported**
  - Evidence: `_convert_nav` in `python/zensical/config.py`, `Navigation::new` in Rust.

### 3.4 Plugins currently used in repo

- `search`
  - Status: **Supported directly**
  - Evidence: `_convert_plugins` + Rust `Plugins.search`.
- `meta-descriptions`
  - Status: **Not implemented as a dedicated runtime plugin in inspected Zensical source**.
  - Evidence looked at:
    - `python/zensical/config.py` (`_convert_plugins` defaults only for `search`/`offline`)
    - `crates/zensical/src/config/plugins.rs` (typed plugin model contains only `search`, `offline`)
  - Migration approach: remove plugin and replace with deterministic prebuild/content checks in local scripts/tests.

### 3.5 Markdown extensions currently used

- `toc`, `admonition`, `attr_list`, `md_in_html`, `pymdownx.*`
  - Status: **Supported via Python Markdown extension pipeline**, assuming extension packages are installed.
  - Evidence: `python/zensical/markdown.py`, `_convert_markdown_extensions`.
- `mdx_include`
  - Status: **Not a Zensical-specific feature; only available if external extension is installed.**
  - Migration approach: avoid runtime dependency by prebuilding include snippets into Markdown before `zensical build`.

### 3.6 Hooks and custom MkDocs hook script

- `hooks: ../../scripts/hooks.py` and MkDocs hook callbacks (`on_config`, `on_files`, `on_nav`, `on_page_markdown`)
  - Status: **No equivalent hook API found in inspected Zensical source**.
  - Evidence looked at:
    - grep terms used on Zensical source: `hooks`, `on_config`, `on_files`, `on_nav`, `on_page`
    - inspected CLI/config/markdown/workflow files show no generic hook registration.
  - Migration approach: replace hook effects with deterministic prebuild scripts and explicit docs generation.

## 4) Gaps, unknowns, and decisions

### 4.1 Translation flow from current scripts

Current repo has only `docs/en`; no additional language folders currently present.
Evidence:
- `docs/en/...` exists; no `docs/<lang>/...` siblings observed.

Decision:
- Remove MkDocs translation orchestration and hook-dependent fallback behavior from docs build path.
- Keep scope to single-language deterministic docs build for current repository state.

### 4.2 Unsupported MkDocs plugin behavior

No direct runtime support identified for:
- `mkdocs-meta-descriptions-plugin`
- arbitrary MkDocs plugin lifecycle hooks

Decision:
- Replace with deterministic prebuild validation and tests under this repository’s control.

## 5) Migration design constraints derived from research

1. Use a Zensical-supported primary config file (`mkdocs.yaml` compatibility mode is valid per `python/zensical/main.py` and `python/zensical/config.py`).
2. Use `zensical build`/`zensical serve` CLI (optionally `--config-file`).
3. Keep only Zensical-proven config keys and plugin settings.
4. Replace MkDocs hooks with prebuild docs generation scripts.
5. Ensure docs pipeline is testable without relying on MkDocs internals.
6. Remove MkDocs dependencies unless a specific compatibility dependency is explicitly required and justified.
