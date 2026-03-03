from __future__ import annotations

from pathlib import Path

from lilya_converter.writer import copy_file, iter_files, safe_write


def test_iter_files_is_sorted_and_skips_hidden_paths(tmp_path: Path) -> None:
    (tmp_path / "b.py").write_text("b\n", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    (tmp_path / ".hidden.py").write_text("ignored\n", encoding="utf-8")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "c.py").write_text("c\n", encoding="utf-8")
    (tmp_path / "pkg" / ".ignored.py").write_text("ignored\n", encoding="utf-8")

    files = iter_files(tmp_path)
    assert [str(path.relative_to(tmp_path)) for path in files] == ["a.txt", "b.py", "pkg/c.py"]


def test_safe_write_creates_parent_dirs(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "main.py"
    safe_write(target, "print('ok')\n")
    assert target.read_text(encoding="utf-8") == "print('ok')\n"


def test_copy_file_copies_metadata_and_contents(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    target = tmp_path / "sub" / "target.txt"
    source.write_text("hello\n", encoding="utf-8")

    copy_file(source, target)

    assert target.read_text(encoding="utf-8") == "hello\n"
