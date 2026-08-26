"""任务管理器命令行入口（版本 0.1.0）。"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .core import Task, TaskManagerError, TaskRecord, TaskStorageError, TaskStore


def build_parser() -> argparse.ArgumentParser:
    """构造只接受固定 CRUD 操作的命令行。"""
    parser = argparse.ArgumentParser(description="管理一个显式指定的本地 JSON 任务文件。")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path(".course-tasks.json"),
        help="任务 JSON 文件；默认当前目录的 .course-tasks.json。",
    )
    parser.add_argument("--json", action="store_true", help="将成功结果输出为稳定 JSON。")
    parser.add_argument("--verbose", action="store_true", help="将运行元数据写入标准错误。")
    commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

    add_parser = commands.add_parser("add", help="创建任务。")
    add_parser.add_argument("title", help="任务标题，1–200 个非空白字符。")
    add_parser.add_argument("--priority", type=int, default=3, help="优先级 1–5；默认 3。")

    list_parser = commands.add_parser("list", help="列出任务。")
    list_parser.add_argument("--all", action="store_true", help="同时显示已完成任务。")

    show_parser = commands.add_parser("show", help="查看一条任务。")
    show_parser.add_argument("id", type=int, help="任务编号。")

    update_parser = commands.add_parser("update", help="修改任务标题或优先级。")
    update_parser.add_argument("id", type=int, help="任务编号。")
    update_parser.add_argument("--title", help="新标题。")
    update_parser.add_argument("--priority", type=int, help="新优先级 1–5。")

    done_parser = commands.add_parser("done", help="将任务标记为已完成。")
    done_parser.add_argument("id", type=int, help="任务编号。")

    remove_parser = commands.add_parser("remove", help="删除一条任务。")
    remove_parser.add_argument("id", type=int, help="任务编号。")
    remove_parser.add_argument(
        "--yes", action="store_true", help="确认删除；没有此标志时拒绝操作。"
    )
    return parser


def configure_logging(verbose: bool) -> None:
    """仅由 CLI 配置日志；日志不包含任务标题。"""
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )


def _task_payload(task: Task) -> TaskRecord:
    return task.to_record()


def _emit_task(task: Task, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(_task_payload(task), ensure_ascii=False, sort_keys=True))
        return
    state = "完成" if task.done else "待办"
    print(f"[{task.id}] P{task.priority} {state} {task.title}")


def _emit_tasks(tasks: list[Task], *, as_json: bool) -> None:
    if as_json:
        payload = {"tasks": [_task_payload(task) for task in tasks]}
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    if not tasks:
        print("没有符合条件的任务。")
        return
    for task in tasks:
        _emit_task(task, as_json=False)


def run(args: argparse.Namespace) -> int:
    """执行一个 CRUD 命令，并以 0 表示成功。"""
    store = TaskStore(args.data)
    if args.command == "add":
        _emit_task(store.add(args.title, args.priority), as_json=args.json)
        return 0
    if args.command == "list":
        tasks = store.list_tasks()
        displayed = tasks if args.all else [task for task in tasks if not task.done]
        _emit_tasks(displayed, as_json=args.json)
        return 0
    if args.command == "show":
        _emit_task(store.get(args.id), as_json=args.json)
        return 0
    if args.command == "update":
        updated = store.update(args.id, title=args.title, priority=args.priority)
        _emit_task(updated, as_json=args.json)
        return 0
    if args.command == "done":
        _emit_task(store.complete(args.id), as_json=args.json)
        return 0
    if args.command == "remove":
        if not args.yes:
            raise TaskManagerError("删除任务需要显式提供 --yes。")
        _emit_task(store.remove(args.id), as_json=args.json)
        return 0
    raise TaskManagerError(f"不支持的命令：{args.command!r}。")


def main(argv: list[str] | None = None) -> int:
    """解析参数并将预期错误映射为稳定的退出码。"""
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)
    try:
        return run(args)
    except TaskStorageError as exc:
        logging.getLogger(__name__).error("文件操作失败：%s", exc)
        return 3
    except TaskManagerError as exc:
        logging.getLogger(__name__).error("请求被拒绝：%s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
