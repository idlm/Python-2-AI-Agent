"""受控 API 采集器的命令行入口。"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from urllib.parse import urlsplit

from .client import ClientPolicy, CollectionError, SafeApiClient, build_async_client

LOGGER = logging.getLogger(__name__)


def _parameter(value: str) -> tuple[str, str]:
    key, separator, item_value = value.partition("=")
    if not separator or not key or not item_value:
        raise argparse.ArgumentTypeError("查询参数必须采用 key=value 形式且两侧非空。")
    return key, item_value


def build_parser() -> argparse.ArgumentParser:
    """构造显式、最小化的单端点 JSON 采集命令。"""
    parser = argparse.ArgumentParser(description="以受控超时与重试读取一个 HTTPS JSON API 端点。")
    parser.add_argument("--base-url", required=True, help="HTTPS API 基址，例如 https://api.example.com。")
    parser.add_argument("--endpoint", required=True, help="基址下的 GET 路径，例如 /v1/records。")
    parser.add_argument(
        "--param",
        action="append",
        default=[],
        type=_parameter,
        help="查询参数 key=value。",
    )
    parser.add_argument("--max-attempts", type=int, default=3, help="最大 GET 尝试次数，默认 3。")
    parser.add_argument("--verbose", action="store_true", help="将脱敏运行元数据输出到标准错误。")
    return parser


async def _collect(args: argparse.Namespace) -> dict[str, object]:
    base = urlsplit(args.base_url)
    if not base.hostname:
        raise ValueError("基址必须包含主机名。")
    policy = ClientPolicy(
        base_url=args.base_url,
        allowed_hosts=frozenset({base.hostname}),
        user_agent="python-private-course-collector/0.1",
    )
    params = dict(args.param)
    async with build_async_client(policy) as client:
        collector = SafeApiClient(client, policy)
        return await collector.get_json(args.endpoint, params=params)


def main(argv: list[str] | None = None) -> int:
    """运行单次 GET JSON 采集；成功 JSON 到 stdout，运行日志到 stderr。"""
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(message)s",
    )
    try:
        result = asyncio.run(_collect(args))
    except (CollectionError, ValueError) as exc:
        LOGGER.error("collection_failed error_type=%s", type(exc).__name__)
        error_payload = {"error": {"code": "collection_failed", "message": str(exc)}}
        print(json.dumps(error_payload, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
