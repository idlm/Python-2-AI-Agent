"""受限 Agent 的最小公开事件报告；不保存目标、参数或模型文本。"""

from __future__ import annotations

import json
import tempfile
from dataclasses import asdict
from pathlib import Path

from .core import AgentEvent


def write_public_event_report(events: tuple[AgentEvent, ...], path: Path) -> None:
    """原子写入事件结构摘要；调用方不得传入正文或秘密。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"event_count": len(events), "events": [asdict(event) for event in events]}
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
        prefix=f".{path.name}.",
    ) as temporary:
        json.dump(payload, temporary, ensure_ascii=False, sort_keys=True)
        temporary.write("\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)
