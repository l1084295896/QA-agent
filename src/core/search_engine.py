import chromadb
from ..utils.path_utils import PathUtils
from ..utils.log_utils import LogUtils
from ..models.embedding_client import EmbeddingClient


class SearchEngine:
    """Semantic search via Chroma. Supports full sync + incremental updates."""

    def __init__(
        self,
        embedding_client: EmbeddingClient,
        chroma_path: str = "data/chroma",
        top_k: int = 20,
        similarity_threshold: float = 0.5,
        dedup_threshold: float = 0.9,
    ):
        self.embedding_client = embedding_client
        self.chroma_path = str(PathUtils.get_abs_path(chroma_path))
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.dedup_threshold = dedup_threshold

        PathUtils.ensure_dir(self.chroma_path)
        self.client = chromadb.PersistentClient(path=self.chroma_path)
        self.collection = self.client.get_or_create_collection(
            name="questions",
            metadata={"hnsw:space": "cosine"},
        )

    def sync_from_bank(self, questions: list[dict]) -> None:
        """Full rebuild: add new, remove deleted."""
        existing_ids = set(self.collection.get()["ids"]) if self.collection.count() > 0 else set()
        bank_ids = {q["id"] for q in questions}

        to_delete = existing_ids - bank_ids
        if to_delete:
            self.collection.delete(ids=list(to_delete))

        for q in questions:
            if q["id"] not in existing_ids:
                self.add_to_index(q["id"], q["question"], q.get("domain", ""))

        LogUtils.info(f"Synced {len(questions)} questions to Chroma index")

    def add_to_index(self, qid: str, question: str, domain: str) -> None:
        embedding = self.embedding_client.embed_query(question)
        self.collection.add(
            ids=[qid],
            embeddings=[embedding],
            metadatas=[{"domain": domain}],
            documents=[question],
        )

    def update_index(self, qid: str, question: str, domain: str) -> None:
        self.collection.delete(ids=[qid])
        self.add_to_index(qid, question, domain)

    def remove_from_index(self, qid: str) -> None:
        self.collection.delete(ids=[qid])

    def search(self, query: str, k: int = None) -> list[dict]:
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
        results = self.search(question, k=1)
        if results and results[0]["similarity"] >= self.dedup_threshold:
            return results[0]
        return None

    def get_collection_count(self) -> int:
        return self.collection.count()
