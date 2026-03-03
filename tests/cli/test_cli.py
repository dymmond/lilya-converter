from __future__ import annotations

import json
from pathlib import Path

from sayer.testing import SayerTestClient

from lilya_converter.cli import app


def test_analyze_command_outputs_summary(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")

    client = SayerTestClient(app)
    result = client.invoke(["analyze", str(source)])

    assert result.exit_code == 0
    assert "Files scanned: 1" in result.output


def test_convert_command_dry_run_and_report_output(tmp_path: Path) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    report_path = tmp_path / "report.json"
    source.mkdir()
    (source / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")

    client = SayerTestClient(app)
    result = client.invoke(
        [
            "convert",
            str(source),
            str(target),
            "--dry-run",
            "--report",
            str(report_path),
            "--diff",
        ]
    )

    assert result.exit_code == 0
    assert "Dry-run: True" in result.output
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["dry_run"] is True
    assert not target.exists()


def test_map_rules_command_lists_rules() -> None:
    client = SayerTestClient(app)
    result = client.invoke(["map", "rules"])

    assert result.exit_code == 0
    assert "include_router_to_include" in result.output


def test_map_applied_command_reads_report(tmp_path: Path) -> None:
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"applied_rules": ["a", "b"]}), encoding="utf-8")

    client = SayerTestClient(app)
    result = client.invoke(["map", "applied", str(report)])

    assert result.exit_code == 0
    assert "Applied rule count: 2" in result.output


def test_verify_command_returns_error_on_parse_failure(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    (target / "main.py").write_text("def broken(:\n", encoding="utf-8")

    client = SayerTestClient(app)
    result = client.invoke(["verify", str(target)])

    assert result.exit_code != 0
    assert "Verification failed" in result.output
