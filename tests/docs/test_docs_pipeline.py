from __future__ import annotations

import shutil
from pathlib import Path

import pytest

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore[no-redef]

from scripts.docs_pipeline import prepare_docs_tree, run_zensical


@pytest.mark.docs
def test_prepare_docs_tree_matches_golden_fixture(tmp_path: Path) -> None:
    fixture_root = Path("tests/fixtures/docs_pipeline")
    source_dir = fixture_root / "source"
    golden_dir = fixture_root / "golden"
    output_dir = tmp_path / "generated"

    generated = prepare_docs_tree(source_dir, output_dir)

    generated_relative = sorted(path.relative_to(output_dir).as_posix() for path in generated)
    golden_relative = sorted(
        path.relative_to(golden_dir).as_posix() for path in golden_dir.rglob("*") if path.is_file()
    )
    assert generated_relative == golden_relative

    for relative in golden_relative:
        output_file = output_dir / relative
        golden_file = golden_dir / relative
        assert output_file.read_text(encoding="utf-8") == golden_file.read_text(encoding="utf-8")


@pytest.mark.docs
def test_docs_build_smoke_generates_expected_artifacts(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    repo_root = Path.cwd()
    shutil.copy2(repo_root / "mkdocs.yaml", workspace / "mkdocs.yaml")

    source_docs_dir = workspace / "docs" / "en" / "docs"
    source_docs_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(repo_root / "docs" / "en" / "docs", source_docs_dir, dirs_exist_ok=True)

    shutil.copytree(repo_root / "docs_src", workspace / "docs_src", dirs_exist_ok=True)

    generated_docs = workspace / "docs" / "generated"
    prepare_docs_tree(source_docs_dir, generated_docs)

    generated_index = (generated_docs / "index.md").read_text(encoding="utf-8")
    assert "{!>" not in generated_index
    assert "lilya-converter analyze ./fastapi_project --json" in generated_index

    run_zensical(
        project_root=workspace,
        config_file=workspace / "mkdocs.yaml",
        command="build",
        clean=True,
    )

    site_dir = workspace / "site"
    assert site_dir.is_dir()
    assert (site_dir / "index.html").is_file()
    assert (site_dir / "get-started" / "index.html").is_file()
    assert (site_dir / "tutorial-first-conversion" / "index.html").is_file()
    assert (site_dir / "commands" / "index.html").is_file()
    assert (site_dir / "how-to-convert-single-file" / "index.html").is_file()
    assert (site_dir / "conversion-rules" / "index.html").is_file()
    assert (site_dir / "search.json").is_file()
    assert (site_dir / "stylesheets" / "extra.css").is_file()

    index_html = (site_dir / "index.html").read_text(encoding="utf-8")
    assert "how-to-convert-single-file/" in index_html
    assert "stylesheets/extra.css" in index_html
    assert "language-python highlight" in index_html
    assert '<span class="kn">' in index_html


@pytest.mark.docs
def test_docs_pipeline_contains_no_mkdocs_dependency() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    docs_dependencies = pyproject["tool"]["hatch"]["envs"]["docs"]["dependencies"]

    assert any(dependency.startswith("zensical") for dependency in docs_dependencies)
    assert all("mkdocs" not in dependency for dependency in docs_dependencies)

    assert not Path("docs/en/mkdocs.yml").exists()
    assert not Path("scripts/hooks.py").exists()

    docs_script = Path("scripts/docs.py").read_text(encoding="utf-8")
    assert "mkdocs build" not in docs_script
