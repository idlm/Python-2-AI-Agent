"""asyncio 可靠性示例测试。"""

import asyncio
import importlib.util
import logging
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parents[2] / "examples" / "module_06" / "async_reliability.py"
SPEC = importlib.util.spec_from_file_location("async_reliability", MODULE_PATH)
assert SPEC and SPEC.loader
async_reliability = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = async_reliability
SPEC.loader.exec_module(async_reliability)


class AsyncReliabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_batch_returns_results_in_input_order(self) -> None:
        results = await async_reliability.run_batch(
            [
                async_reliability.TimedJob("slow", 0.02, "第二"),
                async_reliability.TimedJob("fast", 0.01, "第一"),
            ],
            timeout_seconds=0.2,
        )

        self.assertEqual([result.name for result in results], ["slow", "fast"])
        self.assertEqual([result.value for result in results], ["第二", "第一"])

    async def test_timeout_cancels_running_job_and_runs_cleanup(self) -> None:
        events: list[str] = []

        with self.assertRaises(async_reliability.BatchTimedOutError):
            await async_reliability.run_batch(
                [async_reliability.TimedJob("slow", 0.2, "不可记录的正文")],
                timeout_seconds=0.01,
                events=events,
            )

        self.assertIn("started:slow", events)
        self.assertIn("cancelled:slow", events)
        self.assertIn("cleaned:slow", events)

    async def test_task_failure_cancels_sibling_and_cleans_both(self) -> None:
        events: list[str] = []

        with self.assertRaises(ExceptionGroup) as caught:
            await async_reliability.run_batch(
                [
                    async_reliability.TimedJob("broken", 0.01, "x", should_fail=True),
                    async_reliability.TimedJob("sibling", 0.2, "y"),
                ],
                timeout_seconds=0.5,
                events=events,
            )

        self.assertTrue(
            any(
                isinstance(error, async_reliability.JobExecutionError)
                for error in caught.exception.exceptions
            )
        )
        self.assertIn("cleaned:broken", events)
        self.assertIn("cancelled:sibling", events)
        self.assertIn("cleaned:sibling", events)

    async def test_explicit_cancellation_propagates_after_cleanup(self) -> None:
        events: list[str] = []
        task = asyncio.create_task(
            async_reliability.run_job(
                async_reliability.TimedJob("cancel-me", 1.0, "不应写入日志"), events
            )
        )
        await asyncio.sleep(0)
        task.cancel()

        with self.assertRaises(asyncio.CancelledError):
            await task

        self.assertIn("cancelled:cancel-me", events)
        self.assertIn("cleaned:cancel-me", events)

    async def test_logs_do_not_include_result_value(self) -> None:
        secret = "异步任务返回但绝不写日志的正文"
        logger = logging.getLogger(async_reliability.__name__)
        with self.assertLogs(logger, level="INFO") as captured:
            results = await async_reliability.run_batch(
                [async_reliability.TimedJob("logged", 0, secret)], timeout_seconds=0.1
            )

        self.assertEqual(results[0].value, secret)
        log_text = "\n".join(captured.output)
        self.assertIn("async_job_completed name=logged", log_text)
        self.assertNotIn(secret, log_text)

    async def test_nonpositive_timeout_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            await async_reliability.run_batch([], timeout_seconds=0)

    def test_job_validates_name_and_delay(self) -> None:
        with self.assertRaises(ValueError):
            async_reliability.TimedJob(" ", 0, "x")
        with self.assertRaises(ValueError):
            async_reliability.TimedJob("negative", -1, "x")


if __name__ == "__main__":
    unittest.main(verbosity=2)
