"""基于 Chroma 向量数据库的语义搜索引擎，支持全量同步、增量更新和相似度查重。"""

import chromadb
from ..utils.path_utils import PathUtils
from ..utils.log_utils import LogUtils
from ..models.embedding_client import EmbeddingClient


class SearchEngine:
    """语义搜索引擎：使用 Chroma + Embedding 模型实现题目检索和去重。

    核心能力：
    - 向量化存储：将题目文本转为 embedding 存入 Chroma collection（余弦相似度空间）
    - 语义搜索：输入查询文本，返回 top_k 个相似题目（高于 similarity_threshold）
    - 去重检测：新增题目时检查是否存在相似度 >= dedup_threshold 的已有题目
    - 全量同步：sync_from_bank 将题库与索引对齐（新增/删除）
    """

    def __init__(
        self,
        embedding_client: EmbeddingClient,
        chroma_path: str = "data/chroma",
        top_k: int = 20,
        similarity_threshold: float = 0.5,
        dedup_threshold: float = 0.9,
    ):
        """初始化搜索引擎。

        Args:
            embedding_client: Embedding 客户端，提供 embed_query 方法
            chroma_path: ChromaDB 持久化存储路径
            top_k: 搜索返回的最大结果数
            similarity_threshold: 搜索的最低相似度阈值（低于此值的结果被过滤）
            dedup_threshold: 去重检测的相似度阈值（>= 此值视为重复）
        """
        self.embedding_client = embedding_client
        self.chroma_path = str(PathUtils.get_abs_path(chroma_path))
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.dedup_threshold = dedup_threshold

        PathUtils.ensure_dir(self.chroma_path)
        self.client = chromadb.PersistentClient(path=self.chroma_path)
        # 使用余弦距离作为向量空间度量
        self.collection = self.client.get_or_create_collection(
            name="questions",
            metadata={"hnsw:space": "cosine"},
        )

    def sync_from_bank(self, questions: list[dict]) -> None:
        """全量同步：将题库数据与 Chroma 索引对齐。

        对比题库 ID 集合与索引 ID 集合：
        - 题库有而索引无 → 添加到索引
        - 索引有而题库无 → 从索引删除

        Args:
            questions: 题库全部题目列表（每个题目含 id, question, domain）
        """
        existing_ids = set(self.collection.get()["ids"]) if self.collection.count() > 0 else set()
        bank_ids = {q["id"] for q in questions}

        # 删除索引中已不在题库的题目
        to_delete = existing_ids - bank_ids
        if to_delete:
            self.collection.delete(ids=list(to_delete))

        # 添加题库中尚未索引的新题目
        for q in questions:
            if q["id"] not in existing_ids:
                self.add_to_index(q["id"], q["question"], q.get("domain", ""))

        LogUtils.info(f"Synced {len(questions)} questions to Chroma index")

    def add_to_index(self, qid: str, question: str, domain: str) -> None:
        """将单个题目的向量和元数据添加到 Chroma 索引。

        Args:
            qid: 题目 ID
            question: 问题文本（同时作为 embedding 输入和文档存储）
            domain: 所属领域（存入 metadata）
        """
        embedding = self.embedding_client.embed_query(question)
        self.collection.add(
            ids=[qid],
            embeddings=[embedding],
            metadatas=[{"domain": domain}],
            documents=[question],
        )

    def update_index(self, qid: str, question: str, domain: str) -> None:
        """更新索引中的题目（先删除旧记录，再添加新记录）。

        ChromaDB 不支持原地更新 embedding，因此采用删+增策略。
        """
        self.collection.delete(ids=[qid])
        self.add_to_index(qid, question, domain)

    def remove_from_index(self, qid: str) -> None:
        """从索引中删除指定题目。

        Args:
            qid: 题目 ID
        """
        self.collection.delete(ids=[qid])

    def search(self, query: str, k: int = None) -> list[dict]:
        """语义搜索：返回与查询文本最相似的前 k 个题目。

        Args:
            query: 查询文本
            k: 返回结果数量（默认使用 self.top_k）

        Returns:
            结果列表，每项包含 id, domain, similarity, question
        """
        k = k or self.top_k
        if self.collection.count() == 0:
            return []

        embedding = self.embedding_client.embed_query(query)
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=min(k, self.collection.count()),
        )

        output = []
        if results["ids"] and results["ids"][0]:
            for i, qid in enumerate(results["ids"][0]):
                distance = results["distances"][0][i] if results["distances"] else 0
                # Chroma 存储的是余弦距离，similarity = 1 - distance（仅在余弦空间下成立）
                similarity = 1 - distance
                if similarity >= self.similarity_threshold:
                    output.append({
                        "id": qid,
                        "domain": results["metadatas"][0][i].get("domain", ""),
                        "similarity": round(similarity, 4),
                        "question": results["documents"][0][i] if results["documents"] else "",
                    })
        return output

    def check_duplicate(self, question: str) -> dict | None:
        """检查新题目是否与已有题目高度相似（去重检测）。

        仅在相似度 >= dedup_threshold（默认 0.9）时视为重复。

        Args:
            question: 待检查的题目文本

        Returns:
            重复题目信息字典（含 similarity 值），无重复返回 None
        """
        results = self.search(question, k=1)
        if results and results[0]["similarity"] >= self.dedup_threshold:
            return results[0]
        return None

    def get_collection_count(self) -> int:
        """返回当前 Chroma collection 中的文档数量。"""
        return self.collection.count()
