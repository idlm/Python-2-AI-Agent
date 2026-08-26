"""CLI 工具平台配置与日志边界测试。"""

from pathlib import Path

import pytest

from cli_tool_platform.settings import (
    ConfigurationError,
    Settings,
    load_settings,
    load_toml_settings,
    normalize_log_level,
)


def write_config(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "settings.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_defaults_are_safe_and_deterministic() -> None:
    assert load_settings(environ={}) == Settings(app_name="cli-tool-platform", log_level="INFO")


def test_toml_settings_are_loaded(tmp_path: Path) -> None:
    path = write_config(tmp_path, 'app_name = "course-cli"\nlog_level = "warning"\n')
    assert load_settings(config_path=path, environ={}) == Settings(
        app_name="course-cli", log_level="WARNING"
    )


def test_environment_overrides_trusted_toml(tmp_path: Path) -> None:
    path = write_config(tmp_path, 'app_name = "file-name"\nlog_level = "INFO"\n')
    settings = load_settings(
        config_path=path,
        environ={"COURSE_APP_NAME": "environment-name", "COURSE_LOG_LEVEL": "error"},
    )
    assert settings == Settings(app_name="environment-name", log_level="ERROR")


def test_unknown_toml_field_is_rejected(tmp_path: Path) -> None:
    path = write_config(tmp_path, 'app_name = "ok"\nmodule = "os"\n')
    with pytest.raises(ConfigurationError, match="不允许字段"):
        load_toml_settings(path)


def test_invalid_toml_is_reported_with_position(tmp_path: Path) -> None:
    path = write_config(tmp_path, "app_name = [\n")
    with pytest.raises(ConfigurationError, match="有效 TOML"):
        load_toml_settings(path)


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="不支持的 log_level"):
        normalize_log_level("trace")


def test_missing_configuration_file_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="找不到配置文件"):
        load_toml_settings(tmp_path / "missing.toml")
