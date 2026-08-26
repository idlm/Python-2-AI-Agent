"""兼容入口：请在新代码中改用 `auto_archive.core`。"""

from auto_archive.core import (
    ArchiveAction,
    ArchiveInputError,
    execute_archive,
    load_config,
    plan_archive,
    rollback_from_manifest,
    write_manifest,
)

__all__ = [
    "ArchiveAction",
    "ArchiveInputError",
    "execute_archive",
    "load_config",
    "plan_archive",
    "rollback_from_manifest",
    "write_manifest",
]
