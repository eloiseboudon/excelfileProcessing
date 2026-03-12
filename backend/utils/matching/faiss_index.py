"""FAISS index for approximate nearest neighbor search on embeddings.

Builds an in-memory FAISS index over label embeddings and provides
sub-millisecond candidate retrieval for product matching.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional, Tuple

import numpy as np

_FAISS_DIR = os.environ.get("FAISS_INDEX_DIR", "/app/data/faiss")


class FAISSIndex:
    """FAISS-backed ANN index for matching embeddings.

    Uses IndexFlatIP (inner product = cosine similarity on normalized vectors).
    For the expected volume (<10K entries), flat index is optimal.
    """

    def __init__(self) -> None:
        self._index = None
        self._id_map: List[int] = []
        self._dim: int = 0

    @property
    def size(self) -> int:
        return len(self._id_map)

    def build(self, embeddings: Dict[int, np.ndarray]) -> None:
        """Build the index from a dict of {id: embedding_vector}.

        Args:
            embeddings: mapping from entity ID to normalized float32 vector.
        """
        import faiss

        if not embeddings:
            self._index = None
            self._id_map = []
            return

        ids = list(embeddings.keys())
        vectors = np.array([embeddings[i] for i in ids], dtype=np.float32)
        self._dim = vectors.shape[1]
        self._id_map = ids

        self._index = faiss.IndexFlatIP(self._dim)
        self._index.add(vectors)

    def search(
        self, query_embedding: np.ndarray, top_k: int = 100
    ) -> List[Tuple[int, float]]:
        """Search the index for nearest neighbors.

        Args:
            query_embedding: normalized float32 vector.
            top_k: number of results to return.

        Returns:
            List of (entity_id, cosine_similarity_score) sorted by score desc.
        """
        if self._index is None or self._index.ntotal == 0:
            return []

        query = query_embedding.reshape(1, -1).astype(np.float32)
        k = min(top_k, self._index.ntotal)
        scores, indices = self._index.search(query, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self._id_map):
                results.append((self._id_map[idx], float(score)))
        return results

    def save(self, name: str = "label_index") -> str:
        """Persist the index to disk."""
        import faiss

        if self._index is None:
            return ""
        os.makedirs(_FAISS_DIR, exist_ok=True)
        path = os.path.join(_FAISS_DIR, f"{name}.faiss")
        faiss.write_index(self._index, path)

        ids_path = os.path.join(_FAISS_DIR, f"{name}_ids.npy")
        np.save(ids_path, np.array(self._id_map))
        return path

    def load(self, name: str = "label_index") -> bool:
        """Load a persisted index from disk. Returns True if successful."""
        import faiss

        path = os.path.join(_FAISS_DIR, f"{name}.faiss")
        ids_path = os.path.join(_FAISS_DIR, f"{name}_ids.npy")
        if not os.path.exists(path) or not os.path.exists(ids_path):
            return False

        self._index = faiss.read_index(path)
        self._id_map = np.load(ids_path).tolist()
        self._dim = self._index.d
        return True
