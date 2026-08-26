"""知识笔记 API 的本地启动入口。"""

from __future__ import annotations

import argparse

import uvicorn


def _port(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("端口必须是整数。") from exc
    if not 1 <= port <= 65_535:
        raise argparse.ArgumentTypeError("端口必须在 1–65535 之间。")
    return port


def build_parser() -> argparse.ArgumentParser:
    """构造只启动本地开发服务器的命令行参数。"""
    parser = argparse.ArgumentParser(description="启动教学知识笔记 API。")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址；默认仅本机可访问。")
    parser.add_argument("--port", type=_port, default=8000, help="监听端口；默认 8000。")
    return parser


def main(argv: list[str] | None = None) -> int:
    """启动 Uvicorn；生产部署策略将在后续部署章节中单独讨论。"""
    args = build_parser().parse_args(argv)
    uvicorn.run("knowledge_api.api:app", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
