"""受控内存索引清除与重建示例；不读取凭据、不访问网络、不输出课程正文。"""

from __future__ import annotations

import json

from rag_contract_workbench.core import (
    CourseDocument,
    HashingEmbeddingProvider,
    InMemoryVectorIndex,
)


def main() -> int:
    index = InMemoryVectorIndex(HashingEmbeddingProvider(dimensions=256))
    documents = [
        CourseDocument(
            document_id="maintenance-demo",
            title="索引维护公开教学文本",
            version="v1",
            text="索引清除只移除当前进程内存快照。重建必须重新提交已授权文档。",
        )
    ]
    first_version = index.build(documents, chunk_size=40, overlap=0)
    cleared_version = index.clear()
    rebuilt_version = index.build(documents, chunk_size=40, overlap=0)
    print(
        json.dumps(
            {
                "cleared_matches_first": cleared_version == first_version,
                "rebuilt_matches_content_version": rebuilt_version == first_version,
                "document_count": len(documents),
                "status": "rebuilt",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
