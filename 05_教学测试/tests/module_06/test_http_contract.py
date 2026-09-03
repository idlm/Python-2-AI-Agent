"""HTTP 契约示例测试。"""

import importlib.util
import logging
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parents[3] / "examples" / "module_06" / "http_contract.py"
SPEC = importlib.util.spec_from_file_location("http_contract", MODULE_PATH)
assert SPEC and SPEC.loader
http_contract = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = http_contract
SPEC.loader.exec_module(http_contract)


class HttpContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = http_contract.NoteStore()

    def test_post_creates_and_get_lists_note(self) -> None:
        created = http_contract.dispatch(
            http_contract.Request("POST", "/notes", {"title": "HTTP", "content": "定义边界"}),
            self.store,
        )
        listed = http_contract.dispatch(http_contract.Request("GET", "/notes"), self.store)

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.payload["id"], 1)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.payload["notes"][0]["title"], "HTTP")

    def test_get_by_id_returns_created_resource(self) -> None:
        http_contract.dispatch(
            http_contract.Request("POST", "/notes", {"title": "API", "content": "输入输出"}),
            self.store,
        )

        response = http_contract.dispatch(http_contract.Request("GET", "/notes/1"), self.store)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.payload["content"], "输入输出")

    def test_missing_resource_returns_controlled_404(self) -> None:
        response = http_contract.dispatch(http_contract.Request("GET", "/notes/99"), self.store)

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.payload["error"]["code"], "note_not_found")

    def test_unknown_path_and_invalid_identifier_return_404(self) -> None:
        self.assertEqual(
            http_contract.dispatch(http_contract.Request("GET", "/unknown"), self.store).status_code,
            404,
        )
        self.assertEqual(
            http_contract.dispatch(http_contract.Request("GET", "/notes/zero"), self.store).status_code,
            404,
        )

    def test_wrong_method_returns_405(self) -> None:
        response = http_contract.dispatch(http_contract.Request("DELETE", "/notes"), self.store)

        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.payload["error"]["code"], "method_not_allowed")

    def test_body_requires_exact_schema(self) -> None:
        missing = http_contract.dispatch(
            http_contract.Request("POST", "/notes", {"title": "只有标题"}), self.store
        )
        unknown = http_contract.dispatch(
            http_contract.Request(
                "POST", "/notes", {"title": "标题", "content": "正文", "command": "rm -rf /"}
            ),
            self.store,
        )

        self.assertEqual(missing.status_code, 422)
        self.assertEqual(unknown.status_code, 422)
        self.assertEqual(unknown.payload["error"]["code"], "invalid_request")

    def test_body_rejects_blank_and_non_string_values(self) -> None:
        blank = http_contract.dispatch(
            http_contract.Request("POST", "/notes", {"title": "  ", "content": "正文"}), self.store
        )
        wrong_type = http_contract.dispatch(
            http_contract.Request("POST", "/notes", {"title": "标题", "content": 42}), self.store
        )

        self.assertEqual(blank.status_code, 422)
        self.assertEqual(wrong_type.status_code, 422)

    def test_logs_never_include_request_body(self) -> None:
        secret = "不应写入日志的服务正文"
        logger = logging.getLogger(http_contract.__name__)
        with self.assertLogs(logger, level="INFO") as captured:
            response = http_contract.dispatch(
                http_contract.Request("POST", "/notes", {"title": "标题", "content": secret}),
                self.store,
            )

        self.assertEqual(response.status_code, 201)
        self.assertNotIn(secret, "\n".join(captured.output))
        self.assertIn("status=201", "\n".join(captured.output))


if __name__ == "__main__":
    unittest.main(verbosity=2)
