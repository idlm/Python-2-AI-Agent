"""安全插件系统 CLI 端到端测试。"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = PROJECT_ROOT / "src" / "cli.py"
EXAMPLE_CONFIG = PROJECT_ROOT / "examples" / "plugins.json"


class CliTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(CLI_PATH), *arguments],
            cwd=PROJECT_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_list_outputs_only_allowed_plugin_names(self) -> None:
        result = self.run_cli("--config", str(EXAMPLE_CONFIG), "--list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["agent_note", "task"])

    def test_transform_creates_metadata_only_audit_record(self) -> None:
        secret_text = "不应落入审计日志的正文"
        with tempfile.TemporaryDirectory() as directory:
            audit_path = Path(directory) / "audit.jsonl"
            result = self.run_cli(
                "--config",
                str(EXAMPLE_CONFIG),
                "--plugin",
                "task",
                "--text",
                secret_text,
                "--audit-log",
                str(audit_path),
            )
            record_text = audit_path.read_text(encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, f"任务：{secret_text}\n")
        self.assertNotIn(secret_text, record_text)
        record = json.loads(record_text)
        self.assertTrue(record["success"])
        self.assertEqual(record["plugin"], "task")

    def test_unknown_plugin_returns_controlled_nonzero_exit(self) -> None:
        result = self.run_cli(
            "--config", str(EXAMPLE_CONFIG), "--plugin", "unregistered", "--text", "x"
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("未知插件", result.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
