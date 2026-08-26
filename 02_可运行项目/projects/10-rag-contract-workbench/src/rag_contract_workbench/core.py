"""受控 RAG 语料、切块、向量索引和检索合同（版本 0.1.0）。"""

from __future__ import annotations

import hashlib
import logging
import math
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Final, Protocol

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())

_IDENTIFIER: Final[re.Pattern[str]] = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
_FEATURES: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")
_ALLOWED_COLLECTIONS: Final[frozenset[str]] = frozenset({"course-public"})


class DocumentError(ValueError):
    """文档或来源元数据不符合受控语料合同。"""


class ChunkingError(ValueError):
    """切块参数或块内容不符合可复现切块合同。"""


class QueryError(ValueError):
    """查询或检索预算不符合受控检索合同。"""


class IndexErrorContract(ValueError):
    """索引构建或嵌入向量不符合索引合同。"""


@dataclass(frozen=True)
class CourseDocument:
    """仅用于课程公开语料的受控文档；真实敏感数据不应进入该教学项目。"""

    document_id: str
    title: str
    version: str
    text: str
    collection: str = "course-public"

    def __post_init__(self) -> None:
        _validate_identifier(self.document_id, "document_id")
        _validate_identifier(self.version, "version")
        _validate_collection(self.collection)
        if not isinstance(self.title, str) or not self.title.strip() or len(self.title) > 120:
            raise DocumentError("title 必须是 1–120 个字符的非空字符串。")
        if not isinstance(self.text, str):
            raise DocumentError("text 必须是字符串。")
        normalized_text = self.text.strip()
        if not normalized_text or len(normalized_text) > 10_000:
            raise DocumentError("text 必须是 1–10000 个字符的非空课程文本。")
        if _contains_disallowed_control(normalized_text):
            raise DocumentError("text 不能含未允许的控制字符。")
        object.__setattr__(self, "title", self.title.strip())
        object.__setattr__(self, "text", normalized_text)


@dataclass(frozen=True)
class Chunk:
    """可追溯、不可变的源文档片段。"""

    chunk_id: str
    document_id: str
    document_title: str
    source_version: str
    collection: str
    ordinal: int
    char_start: int
    char_end: int
    text: str
    content_sha256: str

    def __post_init__(self) -> None:
        _validate_identifier(self.chunk_id, "chunk_id")
        _validate_identifier(self.document_id, "document_id")
        _validate_identifier(self.source_version, "source_version")
        _validate_collection(self.collection)
        if self.ordinal < 0 or self.char_start < 0 or self.char_end <= self.char_start:
            raise ChunkingError("块序号和字符范围必须是有效的递增非负边界。")
        if not isinstance(self.text, str) or not self.text.strip():
            raise ChunkingError("块文本必须是非空字符串。")
        expected_hash = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        if self.content_sha256 != expected_hash:
            raise ChunkingError("块内容指纹与块文本不匹配。")


@dataclass(frozen=True)
class RetrievedChunk:
    """按分数排序的来源片段；分数只用于候选排序，不表示事实正确性。"""

    chunk: Chunk
    score: float


@dataclass(frozen=True)
class RetrievalResult:
    """一次检索的公开候选和最小元数据；不包含查询正文。"""

    collection: str
    index_version: str
    query_chars: int
    candidates_considered: int
    score_threshold: float
    results: tuple[RetrievedChunk, ...]


class EmbeddingProvider(Protocol):
    """可替换嵌入接口；生产提供方必须在独立适配层中实现。"""

    @property
    def dimensions(self) -> int: ...

    def embed_many(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]: ...


class HashingEmbeddingProvider:
    """确定性词法测试嵌入，专用于本课程离线合同测试，绝不声称具有语义检索质量。"""

    def __init__(self, dimensions: int = 64) -> None:
        if dimensions < 8 or dimensions > 4096:
            raise IndexErrorContract("教学哈希嵌入维度必须在 8–4096 之间。")
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed_many(self, texts: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        vectors: list[tuple[float, ...]] = []
        for text in texts:
            if not isinstance(text, str) or not text.strip():
                raise IndexErrorContract("嵌入输入必须是非空字符串。")
            vector = [0.0] * self._dimensions
            features = tuple(_features(text))
            if not features:
                raise IndexErrorContract("嵌入输入必须至少含一个可索引字符。")
            for feature in features:
                digest = hashlib.sha256(feature.casefold().encode("utf-8")).digest()
                bucket = int.from_bytes(digest[:4], "big") % self._dimensions
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vector[bucket] += sign
            vectors.append(_l2_normalize(vector))
        return tuple(vectors)


@dataclass(frozen=True)
class _IndexSnapshot:
    collection: str
    index_version: str
    chunks: tuple[Chunk, ...]
    vectors: tuple[tuple[float, ...], ...]


class InMemoryVectorIndex:
    """单进程、非持久、只读查询的教学索引；不是生产向量数据库或权限系统。"""

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        *,
        allowed_collections: frozenset[str] = _ALLOWED_COLLECTIONS,
        max_documents: int = 20,
    ) -> None:
        if embedding_provider.dimensions < 1:
            raise IndexErrorContract("嵌入提供方维度必须大于零。")
        allowed_names_are_valid = all(
            _IDENTIFIER.fullmatch(name) for name in allowed_collections
        )
        if not allowed_collections or not allowed_names_are_valid:
            raise IndexErrorContract("允许集合必须含至少一个有效 collection 名称。")
        if max_documents < 1 or max_documents > 100:
            raise IndexErrorContract("课程索引文档上限必须在 1–100 之间。")
        self._provider = embedding_provider
        self._allowed_collections = allowed_collections
        self._max_documents = max_documents
        self._snapshot: _IndexSnapshot | None = None

    def build(
        self,
        documents: Sequence[CourseDocument],
        *,
        chunk_size: int = 360,
        overlap: int = 60,
    ) -> str:
        """原子替换内存快照；只有完整嵌入、维度验证后才发布新索引版本。"""
        if not documents:
            raise IndexErrorContract("索引至少需要一份课程文档。")
        if len(documents) > self._max_documents:
            raise IndexErrorContract("文档数量超过当前课程索引上限。")
        collection = documents[0].collection
        if collection not in self._allowed_collections:
            raise IndexErrorContract("文档 collection 不在当前索引允许列表中。")
        if any(document.collection != collection for document in documents):
            raise IndexErrorContract("一次构建只能包含同一个受控 collection。")
        document_ids = tuple(document.document_id for document in documents)
        if len(set(document_ids)) != len(document_ids):
            raise IndexErrorContract("同一索引快照中的 document_id 不可重复。")
        chunks = tuple(
            chunk
            for document in documents
            for chunk in chunk_document(document, chunk_size=chunk_size, overlap=overlap)
        )
        vectors = self._provider.embed_many(tuple(chunk.text for chunk in chunks))
        _validate_vectors(vectors, expected_count=len(chunks), dimensions=self._provider.dimensions)
        version_source = "|".join(
            f"{chunk.chunk_id}:{chunk.content_sha256}" for chunk in chunks
        ).encode("utf-8")
        index_version = hashlib.sha256(version_source).hexdigest()[:16]
        self._snapshot = _IndexSnapshot(
            collection=collection,
            index_version=index_version,
            chunks=chunks,
            vectors=vectors,
        )
        LOGGER.info(
            "rag_index_built collection=%s document_count=%s chunk_count=%s "
            "dimensions=%s index_version=%s",
            collection,
            len(documents),
            len(chunks),
            self._provider.dimensions,
            index_version,
        )
        return index_version

    def clear(self, *, collection: str = "course-public") -> str:
        """清除当前内存快照并返回被清除的版本；不是持久删除或跨进程保证。"""
        snapshot = self._require_snapshot()
        if collection != snapshot.collection:
            raise QueryError("清除 collection 与当前索引快照不匹配。")
        self._snapshot = None
        LOGGER.info(
            "rag_index_cleared collection=%s index_version=%s",
            collection,
            snapshot.index_version,
        )
        return snapshot.index_version

    def search(
        self,
        query: str,
        *,
        collection: str = "course-public",
        top_k: int = 3,
        score_threshold: float = 0.05,
    ) -> RetrievalResult:
        """返回受控数量、排序稳定、带来源的候选块；不生成答案或执行块中内容。"""
        snapshot = self._require_snapshot()
        _validate_query(query, collection, top_k, score_threshold)
        if collection != snapshot.collection:
            raise QueryError("查询 collection 与当前索引快照不匹配。")
        query_vector = self._provider.embed_many((query,))[0]
        _validate_vectors((query_vector,), expected_count=1, dimensions=self._provider.dimensions)
        ranked = sorted(
            (
                RetrievedChunk(chunk=chunk, score=_cosine_similarity(query_vector, vector))
                for chunk, vector in zip(snapshot.chunks, snapshot.vectors, strict=True)
            ),
            key=lambda item: (-item.score, item.chunk.chunk_id),
        )
        selected = tuple(item for item in ranked if item.score >= score_threshold)[:top_k]
        LOGGER.info(
            "rag_search_completed collection=%s index_version=%s query_chars=%s "
            "candidates=%s returned=%s top_k=%s threshold=%s",
            collection,
            snapshot.index_version,
            len(query),
            len(ranked),
            len(selected),
            top_k,
            score_threshold,
        )
        return RetrievalResult(
            collection=collection,
            index_version=snapshot.index_version,
            query_chars=len(query),
            candidates_considered=len(ranked),
            score_threshold=score_threshold,
            results=selected,
        )

    def _require_snapshot(self) -> _IndexSnapshot:
        if self._snapshot is None:
            raise QueryError("索引尚未构建，不能查询。")
        return self._snapshot


def chunk_document(
    document: CourseDocument,
    *,
    chunk_size: int = 360,
    overlap: int = 60,
) -> tuple[Chunk, ...]:
    """按稳定字符窗口切块，优先在中文句末或换行处收束，并保留原始位置。"""
    if chunk_size < 40 or chunk_size > 2_000:
        raise ChunkingError("chunk_size 必须在 40–2000 字符之间。")
    if overlap < 0 or overlap >= chunk_size:
        raise ChunkingError("overlap 必须非负且小于 chunk_size。")
    text = document.text
    chunks: list[Chunk] = []
    start = 0
    ordinal = 0
    while start < len(text):
        provisional_end = min(start + chunk_size, len(text))
        end = _choose_boundary(text, start, provisional_end)
        raw_chunk = text[start:end]
        left_trimmed = len(raw_chunk) - len(raw_chunk.lstrip())
        right_trimmed = len(raw_chunk) - len(raw_chunk.rstrip())
        chunk_start = start + left_trimmed
        chunk_end = end - right_trimmed
        chunk_text = text[chunk_start:chunk_end]
        if chunk_text:
            chunk_id = f"{document.document_id}-{ordinal}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=document.document_id,
                    document_title=document.title,
                    source_version=document.version,
                    collection=document.collection,
                    ordinal=ordinal,
                    char_start=chunk_start,
                    char_end=chunk_end,
                    text=chunk_text,
                    content_sha256=hashlib.sha256(chunk_text.encode("utf-8")).hexdigest(),
                )
            )
            ordinal += 1
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    if not chunks:
        raise ChunkingError("文档没有产生可索引的非空块。")
    return tuple(chunks)


def _choose_boundary(text: str, start: int, provisional_end: int) -> int:
    if provisional_end >= len(text):
        return provisional_end
    markers = ("\n", "。", "！", "？", ".", "!", "?")
    candidates = [text.rfind(marker, start + 1, provisional_end) for marker in markers]
    boundary = max(candidates)
    if boundary > start + 20:
        return boundary + 1
    return provisional_end


def _features(text: str) -> Iterable[str]:
    for token in _FEATURES.findall(text):
        if len(token) == 1 and "\u4e00" <= token <= "\u9fff":
            yield token
        else:
            yield token


def _validate_identifier(value: str, name: str) -> None:
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise DocumentError(f"{name} 必须是 1–64 个小写字母、数字、下划线或短横线。")


def _validate_collection(collection: str) -> None:
    _validate_identifier(collection, "collection")
    if collection not in _ALLOWED_COLLECTIONS:
        raise DocumentError("collection 不在当前课程允许列表中。")


def _validate_query(query: str, collection: str, top_k: int, score_threshold: float) -> None:
    if not isinstance(query, str) or not query.strip() or len(query) > 500:
        raise QueryError("查询必须是 1–500 个字符的非空字符串。")
    if _contains_disallowed_control(query):
        raise QueryError("查询不能含未允许的控制字符。")
    if collection not in _ALLOWED_COLLECTIONS:
        raise QueryError("查询 collection 不在当前允许列表中。")
    if top_k < 1 or top_k > 5:
        raise QueryError("top_k 必须在 1–5 之间。")
    if not -1.0 <= score_threshold <= 1.0:
        raise QueryError("score_threshold 必须在 -1.0–1.0 之间。")


def _validate_vectors(
    vectors: Sequence[Sequence[float]],
    *,
    expected_count: int,
    dimensions: int,
) -> None:
    if len(vectors) != expected_count:
        raise IndexErrorContract("嵌入数量与输入数量不匹配。")
    for vector in vectors:
        if len(vector) != dimensions:
            raise IndexErrorContract("嵌入维度与索引合同不匹配。")
        if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in vector):
            raise IndexErrorContract("嵌入向量必须只含有限数值。")
        if math.isclose(math.sqrt(sum(value * value for value in vector)), 0.0):
            raise IndexErrorContract("嵌入向量不能是零向量。")


def _l2_normalize(vector: Sequence[float]) -> tuple[float, ...]:
    norm = math.sqrt(sum(value * value for value in vector))
    if math.isclose(norm, 0.0):
        raise IndexErrorContract("不能规范化零向量。")
    return tuple(value / norm for value in vector)


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if math.isclose(left_norm, 0.0) or math.isclose(right_norm, 0.0):
        raise IndexErrorContract("不能计算零向量的余弦相似度。")
    return numerator / (left_norm * right_norm)


def _contains_disallowed_control(text: str) -> bool:
    return any(ord(character) < 32 and character not in {"\n", "\t"} for character in text)
