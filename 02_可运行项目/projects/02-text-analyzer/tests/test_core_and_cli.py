"""文本分析工具 0.2.0 的核心与 CLI 测试。"""

from pathlib import Path

from text_analyzer.cli import main
from text_analyzer.core import (
    TextInputError,
    analyze_text,
    count_words,
    format_report,
    read_text_file,
)


def test_legacy_normalization_statistics_and_report_are_preserved() -> None:
    assert count_words("  a   b  ") == 2
    assert analyze_text("a b\nc") == {"characters": 5, "words": 3, "lines": 2}
    assert format_report("a b") == "字符数：3；词数：2；行数：1"


def test_non_string_text_is_rejected() -> None:
    try:
        analyze_text(123)  # type: ignore[arg-type]
    except TypeError as exc:
        assert str(exc) == "text 必须是字符串"
    else:
        raise AssertionError("非字符串输入必须抛出 TypeError")


def test_utf8_file_can_be_read(tmp_path: Path) -> None:
    file_path = tmp_path / "input.txt"
    file_path.write_text("你好 world\n", encoding="utf-8")
    assert read_text_file(file_path) == "你好 world\n"


def test_missing_non_utf8_and_oversized_files_are_rejected(tmp_path: Path) -> None:
    missing = tmp_path / "missing.txt"
    try:
        read_text_file(missing)
    except TextInputError as exc:
        assert "找不到输入文件" in str(exc)
    else:
        raise AssertionError("缺失文件必须被拒绝")

    binary = tmp_path / "binary.dat"
    binary.write_bytes(b"\xff")
    try:
        read_text_file(binary)
    except TextInputError as exc:
        assert "UTF-8" in str(exc)
    else:
        raise AssertionError("非 UTF-8 文件必须被拒绝")

    large = tmp_path / "large.txt"
    large.write_text("12345", encoding="utf-8")
    try:
        read_text_file(large, max_bytes=4)
    except TextInputError as exc:
        assert "超过" in str(exc)
    else:
        raise AssertionError("超过大小上限的文件必须被拒绝")


def test_cli_text_and_json_output(capsys) -> None:
    exit_code = main(["--text", "a b\nc", "--json"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == '{"characters": 5, "lines": 2, "words": 3}\n'
    assert "text_analyzed" in captured.err


def test_cli_file_and_controlled_input_error(tmp_path: Path, capsys) -> None:
    file_path = tmp_path / "input.txt"
    file_path.write_text("a b", encoding="utf-8")
    assert main(["--file", str(file_path)]) == 0
    success = capsys.readouterr()
    assert success.out == "字符数：3；词数：2；行数：1\n"

    assert main(["--file", str(tmp_path / "missing.txt")]) == 2
    failure = capsys.readouterr()
    assert "输入被拒绝" in failure.err
