"""对受控 OpenAI-compatible 代理进行一次最小结构化输出烟雾验收。"""

from __future__ import annotations

import json
import logging

from llm_contract_client.openai_transport import OpenAiChatTransport
from llm_contract_client.structured import StructuredSummaryClient


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s %(name)s %(message)s",
    )
    client = StructuredSummaryClient(
        OpenAiChatTransport(),
        max_input_chars=240,
        max_output_tokens=128,
        max_attempts=1,
    )
    result = client.summarize(
        "Python 函数把可重复步骤封装为可调用单元。函数可以接收参数并返回结果，"
        "从而减少重复代码。",
        request_id="module-09-structured-smoke",
    )
    evidence = {
        "model": result.model,
        "request_id": result.request_id,
        "attempts": result.attempts,
        "input_chars": result.input_chars,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "key_point_count": len(result.key_points),
        "uncertainty": result.uncertainty,
        "schema_validated_locally": True,
    }
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
