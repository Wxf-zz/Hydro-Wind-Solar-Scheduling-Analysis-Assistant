from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

SOURCES = {
    "chen-et-al-2022-hydro-wind-solar-scheduling-survey.pdf": (
        "KB-001",
        "Power Generation Scheduling for a Hydro-Wind-Solar Hybrid System: "
        "A Systematic Survey and Prospect",
    ),
    "zhang-et-al-2018-yalong-river-operation.pdf": (
        "KB-002",
        "Short-Term Optimal Operation of a Wind-PV-Hydro Complementary Installation: "
        "Yalong River, Sichuan Province, China",
    ),
}

PAGE_TAGS = {
    ("KB-001", 4): "互补调度 研究框架 发电预测 风险管理 机组组合 多时间尺度",
    ("KB-001", 7): "弃风光 弃电 功率平衡 风险",
    ("KB-001", 8): "功率平衡 切负荷 备用容量",
    ("KB-001", 20): "失负荷 出力不足 负荷损失",
    ("KB-001", 21): "弃风光率 清洁能源消纳",
    ("KB-002", 7): "季节互补 风光冬春 水电夏秋",
    ("KB-002", 9): "日内互补 水电调节 风光波动",
    ("KB-002", 10): "功率平衡 水量平衡 流量平衡 库容 出库流量 约束",
    ("KB-002", 15): "出库流量 调节",
    ("KB-002", 16): "水电补偿 风电波动 光伏波动 风光出力",
}


@dataclass(frozen=True)
class Evidence:
    source_id: str
    title: str
    page: int
    quote: str
    score: float


@dataclass(frozen=True)
class _Chunk:
    source_id: str
    title: str
    page: int
    quote: str
    search_text: str


class KnowledgeIndex:
    """保存本地文本块及其 TF-IDF 表示，并返回可定位证据。"""

    def __init__(self, chunks: list[_Chunk]):
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(2, 4))
        self.matrix = self.vectorizer.fit_transform([chunk.search_text for chunk in chunks])

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        min_score: float = 0.05,
    ) -> list[Evidence]:
        if not query.strip() or top_k <= 0:
            return []

        query_vector = self.vectorizer.transform([query.strip()])
        scores = cosine_similarity(query_vector, self.matrix).ravel()
        ranked = scores.argsort()[::-1]
        results: list[Evidence] = []
        seen_pages: set[tuple[str, int]] = set()

        for index in ranked:
            score = float(scores[index])
            chunk = self.chunks[int(index)]
            page_key = (chunk.source_id, chunk.page)
            if score < min_score or page_key in seen_pages:
                continue
            results.append(
                Evidence(chunk.source_id, chunk.title, chunk.page, chunk.quote, score)
            )
            seen_pages.add(page_key)
            if len(results) == top_k:
                break

        return results


def _chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    step = size - overlap
    return [cleaned[start : start + size] for start in range(0, len(cleaned), step)]


def build_knowledge_index(source_dir: Path) -> KnowledgeIndex:
    """读取两篇固定 PDF，并建立只存在于内存中的本地检索索引。"""
    chunks: list[_Chunk] = []
    for filename, (source_id, title) in SOURCES.items():
        path = source_dir / filename
        if not path.exists():
            raise FileNotFoundError(f"知识源不存在：{path}")

        reader = PdfReader(path)
        for page_number, page in enumerate(reader.pages, start=1):
            tags = PAGE_TAGS.get((source_id, page_number), "")
            quotes = _chunk_text(page.extract_text() or "")
            for chunk_number, quote in enumerate(quotes):
                recall_tags = tags if chunk_number == 0 else ""
                search_text = f"{title} {recall_tags} {quote}"
                chunks.append(_Chunk(source_id, title, page_number, quote, search_text))

    if not chunks:
        raise ValueError("知识库没有可检索文本。")
    return KnowledgeIndex(chunks)
