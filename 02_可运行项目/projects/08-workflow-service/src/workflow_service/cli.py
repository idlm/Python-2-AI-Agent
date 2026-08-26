"""项目 8 的受控命令行入口。"""

from __future__ import annotations

import argparse
import json
from typing import NoReturn


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="受控服务工作流教学原型")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument(
        "--status",
        action="store_true",
        help="输出当前原型的能力与明确未提供的可靠性保证。",
    )
    actions.add_argument(
        "--serve",
        action="store_true",
        help="以本地教学模式启动 FastAPI 服务；不启动持久队列或长期 worker。",
    )
    parser.add_argument("--host", default="127.0.0.1", help="只允许本地回环地址。")
    parser.add_argument("--port", type=int, default=8018, help="本地监听端口（1–65535）。")
    return parser


def main() -> NoReturn:
    args = build_parser().parse_args()
    if args.status:
        print(
            json.dumps(
                {
                    "version": "0.1.0",
                    "capabilities": [
                        "state_machine",
                        "idempotency",
                        "bounded_in_process_queue",
                        "controlled_transitions",
                    ],
                    "not_guaranteed": [
                        "persistent_queue",
                        "cross_process_delivery",
                        "crash_safe_execution",
                    ],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        raise SystemExit(0)
    if args.host not in {"127.0.0.1", "localhost"}:
        raise SystemExit("错误：教学服务器只允许 --host 127.0.0.1 或 localhost。")
    if not 1 <= args.port <= 65_535:
        raise SystemExit("错误：--port 必须在 1–65535 之间。")
    import uvicorn

    uvicorn.run("workflow_service.api:app", host=args.host, port=args.port, log_level="warning")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
