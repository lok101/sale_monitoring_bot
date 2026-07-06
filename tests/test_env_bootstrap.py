from __future__ import annotations

from sale_monitoring_bot.project_paths import ENV_FILE, PROJECT_ROOT


def test_project_root_contains_pyproject() -> None:
    assert (PROJECT_ROOT / "pyproject.toml").is_file()


def test_env_file_path_is_in_project_root() -> None:
    assert ENV_FILE.parent == PROJECT_ROOT
    assert ENV_FILE.name == ".env"
