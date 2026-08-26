from __future__ import annotations

import json
from pathlib import Path

from bounded_agent_core.core import ActionKind, AgentStatus, AgentTask, BoundedAgent
from bounded_agent_core.events import write_public_event_report


def test_public_event_report_contains_only_event_contract(tmp_path: Path) -> None:
    agent = BoundedAgent(lambda _: "sensitive-tool-result")
    task = agent.start(AgentTask(task_id="event-1", goal="private-goal-must-not-appear"))
    task, event = agent.step(task, ActionKind.LOOKUP_PUBLIC_FACT, "private-argument")
    output = tmp_path / "events.json"

    write_public_event_report((event,), output)

    payload = json.loads(output.read_text(encoding="utf-8"))
    text = output.read_text(encoding="utf-8")
    assert payload["event_count"] == 1
    assert set(payload["events"][0]) == {
        "action",
        "result_category",
        "status",
        "step_count",
        "task_id",
    }
    assert task.status is AgentStatus.RUNNING
    assert "private-goal-must-not-appear" not in text
    assert "private-argument" not in text
    assert "sensitive-tool-result" not in text
