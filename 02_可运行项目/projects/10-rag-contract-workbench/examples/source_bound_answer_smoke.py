"""单次来源约束回答烟雾验收；仅用于公开教学文本，不输出正文或密钥。"""

from __future__ import annotations

import json

from rag_contract_workbench.answering import AnswerContractError, SourceBoundAnswerClient
from rag_contract_workbench.core import (
    CourseDocument,
    HashingEmbeddingProvider,
    InMemoryVectorIndex,
)
from rag_contract_workbench.openai_answer_transport import (
    AnswerTransportRejectedError,
    AnswerTransportUnavailableError,
    OpenAiSourceBoundAnswerTransport,
)


def main() -> int:
    index = InMemoryVectorIndex(HashingEmbeddingProvider(dimensions=1024))
    index.build(
        [
            CourseDocument(
                document_id="functions",
                title="函数课程笔记",
                version="v1",
                text="函数把重复步骤封装为可调用单元。参数把输入交给函数，返回值传出处理结果。",
            )
        ],
        chunk_size=80,
        overlap=0,
    )
    question = "函数如何接收输入？"
    retrieval = index.search(question, top_k=1, score_threshold=0.0)
    try:
        client = SourceBoundAnswerClient(OpenAiSourceBoundAnswerTransport())
        answer = client.answer(question, retrieval)
    except AnswerTransportUnavailableError:
        print(json.dumps({"status": "transport_unavailable"}, ensure_ascii=False))
        return 2
    except (AnswerTransportRejectedError, AnswerContractError):
        print(json.dumps({"status": "controlled_failure"}, ensure_ascii=False))
        return 2
    print(
        json.dumps(
            {
                "status": answer.status,
                "citation_count": len(answer.citations),
                "citation_chunk_ids": [citation.chunk_id for citation in answer.citations],
                "needs_human_review": answer.needs_human_review,
                "query_chars": answer.query_chars,
                "index_version": answer.index_version,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
