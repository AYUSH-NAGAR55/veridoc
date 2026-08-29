"""Step 8 — Create the knowledge base.

Verified page content (and verified structured fields) get chunked and
turned into a retrievable index. The architecture is written against a
small `VectorIndex` interface so swapping this TF-IDF implementation for
Sentence-Transformers + FAISS (the target stack) is a drop-in change —
see the class docstring below.
"""
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def chunk_page_text(text: str, page_number: int, section_label: str = "", max_chars: int = 700) -> list[dict]:
    text = text.strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 1 > max_chars and current:
            chunks.append(current.strip())
            current = para
        else:
            current = f"{current}\n{para}" if current else para
    if current:
        chunks.append(current.strip())
    return [{"page_number": page_number, "section_label": section_label, "text": c} for c in chunks]


class VectorIndex:
    """TF-IDF + cosine similarity retrieval.

    Ships in place of Sentence-Transformers + FAISS so the demo runs with
    no model downloads. `fit(chunks)` and `search(query, k)` are the only
    two methods a FAISS-backed implementation would also need to expose.
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = None
        self.chunks: list[dict] = []

    def fit(self, chunks: list[dict]):
        self.chunks = chunks
        texts = [c["text"] for c in chunks] or [""]
        self.matrix = self.vectorizer.fit_transform(texts)

    def search(self, query: str, k: int = 4) -> list[tuple[dict, float]]:
        if self.matrix is None or not self.chunks:
            return []
        q_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self.matrix)[0]
        top_idx = np.argsort(sims)[::-1][:k]
        return [(self.chunks[i], float(sims[i])) for i in top_idx if sims[i] > 0]
