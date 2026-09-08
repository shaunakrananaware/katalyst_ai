"""Local ONNX sentence embeddings; neither model nor documents load at startup."""
from threading import RLock
import numpy as np

class LazyRetriever:
    def __init__(self, model_factory=None):
        self.model = None
        self.model_factory = model_factory
        self.cache = {}
        self.lock = RLock()
        self.document_embedding_batches = 0

    def _model(self):
        if self.model is None:
            if self.model_factory:
                self.model = self.model_factory()
            else:
                from fastembed import TextEmbedding
                self.model = TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2')
        return self.model

    def search(self, lead_id, chunks, query, top_k):
        if not chunks: return []
        with self.lock:
            model = self._model()
            if lead_id not in self.cache:
                vectors = np.asarray(list(model.embed([c['text'] for c in chunks])), dtype=float)
                vectors /= np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
                self.cache[lead_id] = (chunks, vectors)
                self.document_embedding_batches += 1
            cached_chunks, vectors = self.cache[lead_id]
            q = np.asarray(list(model.embed([query]))[0], dtype=float)
            q /= max(np.linalg.norm(q), 1e-12)
            scores = vectors @ q
            order = np.argsort(-scores, kind='stable')[:top_k]
            return [{**cached_chunks[int(i)], 'similarity': round(float(scores[i]), 6)} for i in order]

RETRIEVER = LazyRetriever()
