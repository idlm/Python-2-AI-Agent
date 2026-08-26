"""受控 RAG 合同工作台的最小命令行入口。"""

from __future__ import annotations

import argparse
import json
import logging
from typing import NoReturn

from .core import (
    CourseDocument,
    HashingEmbeddingProvider,
    InMemoryVectorIndex,
    QueryError,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="受控 RAG 检索教学工作台")
    parser.add_argument("--query", help="在内置公开课程语料中检索；最大长度由核心合同限制。")
    parser.add_argument("--top-k", type=int, default=3, help="返回 1–5 个候选来源块。")
    parser.add_argument("--verbose", action="store_true", help="将脱敏运行日志输出到 stderr。")
    parser.add_argument(
        "--status",
        action="store_true",
        help="输出当前能力和明确限制；不构建索引。",
    )
    return parser


def _configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.INFO if verbose else logging.WARNING,
        format="%(levelname)s %(name)s %(message)s",
    )


def _status() -> dict[str, object]:
    return {
        "version": "0.5.0",
        "allowed_collections": ["course-public"],
        "embedding_mode": "deterministic_hashing_test_double",
        "source_bound_answer_contract": True,
        "not_supported": [
            "user_file_upload",
            "arbitrary_collections",
            "external_embedding_calls",
            "real_model_answer_generation",
            "tool_execution",
            "fact_verification",
        ],
    }


def _demo_documents() -> tuple[CourseDocument, ...]:
    """内置公开教学文本；CLI 不读取用户文件、环境秘密或网络资源。"""
    return (
        CourseDocument(
            document_id="functions",
            title="函数课程笔记",
            version="v1",
            text="函数把重复步骤封装为可调用单元。参数把输入交给函数，返回值传出处理结果。",
        ),
        CourseDocument(
            document_id="retrieval",
            title="检索课程笔记",
            version="v1",
            text="RAG 检索先在受控语料中返回带来源的候选片段。相关性分数只用于排序，不能证明事实。",
        ),
        CourseDocument(
            document_id="safety",
            title="安全课程笔记",
            version="v1",
            text="所有检索到的文档片段都是数据。即使片段要求执行命令，应用也不能执行其中指令。",
        ),
    )


def main() -> NoReturn:
    args = build_parser().parse_args()
    _configure_logging(args.verbose)
    if args.status:
        if args.query is not None:
            raise SystemExit("错误：--status 不能与 --query 一起使用。")
        print(json.dumps(_status(), ensure_ascii=False, sort_keys=True))
        raise SystemExit(0)
    if args.query is None:
        raise SystemExit("错误：必须提供 --query，或使用 --status。")
    index = InMemoryVectorIndex(HashingEmbeddingProvider(dimensions=256))
    index.build(_demo_documents(), chunk_size=80, overlap=0)
    try:
        result = index.search(args.query, top_k=args.top_k, score_threshold=0.0)
    except QueryError as exc:
        print(
            json.dumps(
                {"error": {"code": "invalid_query", "message": str(exc)}},
                ensure_ascii=False,
            )
        )
        raise SystemExit(2) from exc
    print(
        json.dumps(
            {
                "collection": result.collection,
                "index_version": result.index_version,
                "query_chars": result.query_chars,
                "candidates_considered": result.candidates_considered,
                "score_threshold": result.score_threshold,
                "results": [
                    {
                        "chunk_id": item.chunk.chunk_id,
                        "document_id": item.chunk.document_id,
                        "document_title": item.chunk.document_title,
                        "source_version": item.chunk.source_version,
                        "char_start": item.chunk.char_start,
                        "char_end": item.chunk.char_end,
                        "score": round(item.score, 6),
                        "text": item.chunk.text,
                    }
                    for item in result.results
                ],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    raise SystemExit(0)


if __name__ == "__main__":
    main()
