
"""
Lightweight TF-IDF retrieval for AgentFlow AI.

Features:
- Knowledge-base documents
- Overlapping text chunks
- TF-IDF vectorization using scikit-learn
- Cosine-similarity retrieval
- One-time index construction and caching

This module performs retrieval, not LLM answer generation.
"""

from functools import lru_cache
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


CHUNK_SIZE = 80
CHUNK_OVERLAP = 15


# --------------------------------------------------
# 1. Knowledge base
# --------------------------------------------------

KNOWLEDGE_BASE = [
    {
        "id": "KB-001",
        "title": "Production API Outage",
        "solution": (
            "Check service health, application logs, recent deployments, "
            "and database connectivity. Roll back a recent deployment only "
            "if the incident evidence supports it and an authorized "
            "operator approves."
        ),
    },
    {
        "id": "KB-002",
        "title": "Payment Processing Failures",
        "solution": (
            "Inspect payment-provider status, transaction error codes, "
            "and service logs. Verify whether failed transactions were "
            "charged before attempting retries. Never expose payment "
            "credentials."
        ),
    },
    {
        "id": "KB-003",
        "title": "Password Reset Email Issues",
        "solution": (
            "Check spam folders, email delivery logs, and mail-provider "
            "status. Verify the account's registered email address and "
            "inspect rate limits. Never request or store a user's password."
        ),
    },
    {
        "id": "KB-004",
        "title": "Slow Dashboard Performance",
        "solution": (
            "Measure API response times, inspect slow database queries, "
            "review browser network requests, and check resource "
            "utilization. Optimize the measured bottleneck before "
            "changing infrastructure."
        ),
    },
]


# --------------------------------------------------
# 2. Split documents into overlapping chunks
# --------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into word-based chunks with overlapping context."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be non-negative and smaller than chunk_size."
        )

    words = text.split()

    if not words:
        return []

    chunks = []
    start = 0
    step = chunk_size - overlap

    while start < len(words):
        chunks.append(" ".join(words[start:start + chunk_size]))

        if start + chunk_size >= len(words):
            break

        start += step

    return chunks


def build_document_chunks() -> list[dict[str, Any]]:
    """Convert knowledge-base documents into searchable chunks."""

    chunks = []

    for document in KNOWLEDGE_BASE:
        full_text = (
            f"Title: {document['title']}\n"
            f"Troubleshooting guidance: {document['solution']}"
        )

        for chunk_number, content in enumerate(
            chunk_text(full_text), start=1
        ):
            chunks.append({
                "id": document["id"],
                "title": document["title"],
                "solution": document["solution"],
                "chunk_id": f"{document['id']}-CHUNK-{chunk_number}",
                "chunk_number": chunk_number,
                "content": content,
            })

    return chunks


# --------------------------------------------------
# 3. Build and cache the lightweight TF-IDF index
# --------------------------------------------------

@lru_cache(maxsize=1)
def load_vector_index():
    """
    Build the TF-IDF index once per process.

    TF-IDF vectors are L2-normalized by default, so their dot
    product corresponds to cosine similarity.
    """

    chunks = build_document_chunks()

    if not chunks:
        raise ValueError("The knowledge base contains no searchable text.")

    vectorizer = TfidfVectorizer(
        lowercase=True,
        ngram_range=(1, 2),
        strip_accents="unicode",
    )

    texts = [chunk["content"] for chunk in chunks]
    document_matrix = vectorizer.fit_transform(texts)

    print(
        "TF-IDF index ready: "
        f"{len(chunks)} chunks from {len(KNOWLEDGE_BASE)} documents."
    )

    return vectorizer, chunks, document_matrix


# --------------------------------------------------
# 4. Retrieve relevant documents
# --------------------------------------------------

def search_documents(
    query: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """
    Retrieve knowledge-base documents using TF-IDF cosine similarity.

    Returns one result per document, ranked by its best matching chunk.
    The output structure remains compatible with the existing RAG API.
    """

    if not isinstance(query, str) or not query.strip():
        return []

    if limit <= 0:
        return []

    vectorizer, chunks, document_matrix = load_vector_index()

    query_vector = vectorizer.transform([query.strip()])

    similarities = cosine_similarity(
        query_vector,
        document_matrix,
    ).ravel()

    ranked_indices = np.argsort(-similarities)

    results = []
    seen_document_ids = set()

    for index in ranked_indices:
        chunk = chunks[int(index)]
        document_id = chunk["id"]

        if document_id in seen_document_ids:
            continue

        seen_document_ids.add(document_id)

        results.append({
            "id": document_id,
            "title": chunk["title"],
            "solution": chunk["solution"],
            "chunk_id": chunk["chunk_id"],
            "chunk_number": chunk["chunk_number"],
            "content": chunk["content"],
            "similarity_score": round(
                float(similarities[int(index)]), 4
            ),
        })

        if len(results) >= limit:
            break

    return results


# --------------------------------------------------
# 5. Local test
# --------------------------------------------------

if __name__ == "__main__":
    test_queries = [
        "Customers cannot complete payments",
        "Every request to the production API returns an error",
        "Users are not receiving password recovery emails",
        "The dashboard takes too long to load",
    ]

    for query in test_queries:
        print(f"\nQuery: {query}")

        for result in search_documents(query, limit=3):
            print(
                f"- {result['id']} | {result['title']} | "
                f"similarity={result['similarity_score']}"
            )
            print(f"  Matched passage: {result['content']}")
