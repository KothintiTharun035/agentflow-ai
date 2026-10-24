
"""
Embedding-based vector retrieval for AgentFlow AI.

Features:
- Knowledge-base documents
- Overlapping text chunks
- Local sentence-transformer embeddings
- Cosine-similarity retrieval
- One-time index construction and caching

This module performs retrieval, not LLM answer generation.
"""

from functools import lru_cache
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer


# --------------------------------------------------
# 1. Embedding configuration
# --------------------------------------------------

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

CHUNK_SIZE = 80
CHUNK_OVERLAP = 15


# --------------------------------------------------
# 2. Knowledge base
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
# 3. Split documents into overlapping chunks
# --------------------------------------------------

def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """
    Split text into word-based chunks with overlapping context.

    Short documents produce one chunk.
    Longer documents produce multiple overlapping chunks.
    """

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
        chunk_words = words[start : start + chunk_size]
        chunks.append(" ".join(chunk_words))

        if start + chunk_size >= len(words):
            break

        start += step

    return chunks


def build_document_chunks() -> list[dict[str, Any]]:
    """
    Convert each knowledge-base document into searchable chunks.
    """

    chunks = []

    for document in KNOWLEDGE_BASE:
        # Include the title so its subject is represented in the embedding.
        full_text = (
            f"Title: {document['title']}\n"
            f"Troubleshooting guidance: {document['solution']}"
        )

        document_chunks = chunk_text(full_text)

        for chunk_number, content in enumerate(document_chunks, start=1):
            chunks.append(
                {
                    "id": document["id"],
                    "title": document["title"],
                    "solution": document["solution"],
                    "chunk_id": (
                        f"{document['id']}-CHUNK-{chunk_number}"
                    ),
                    "chunk_number": chunk_number,
                    "content": content,
                }
            )

    return chunks


# --------------------------------------------------
# 4. Build and cache the embedding index
# --------------------------------------------------

@lru_cache(maxsize=1)
def load_vector_index():
    """
    Load the embedding model and build the index once per process.

    Embeddings are normalized, so their dot products equal cosine
    similarity.
    """

    chunks = build_document_chunks()

    if not chunks:
        raise ValueError("The knowledge base contains no searchable text.")

    print(f"Loading embedding model: {EMBEDDING_MODEL}")

    model = SentenceTransformer(EMBEDDING_MODEL)

    texts = [chunk["content"] for chunk in chunks]

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    embeddings = np.asarray(embeddings, dtype=np.float32)

    print(
        "Vector index ready: "
        f"{len(chunks)} chunks from {len(KNOWLEDGE_BASE)} documents."
    )

    return model, chunks, embeddings


# --------------------------------------------------
# 5. Semantic document retrieval
# --------------------------------------------------

def search_documents(
    query: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """
    Retrieve knowledge-base documents using semantic similarity.

    The query is embedded using the same model as the documents.
    Similarity is computed using cosine similarity.

    Returns one result per document, ranked by its best matching chunk.
    """

    if not isinstance(query, str) or not query.strip():
        return []

    if limit <= 0:
        return []

    model, chunks, embeddings = load_vector_index()

    query_embedding = model.encode(
        [query.strip()],
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    query_embedding = np.asarray(
        query_embedding,
        dtype=np.float32,
    )

    # Because both sides are normalized, the dot product is cosine similarity.
    similarities = embeddings @ query_embedding[0]

    # Highest similarity first.
    ranked_indices = np.argsort(-similarities)

    results = []
    seen_document_ids = set()

    for index in ranked_indices:
        chunk = chunks[int(index)]
        document_id = chunk["id"]

        # Keep the best matching chunk for each document.
        if document_id in seen_document_ids:
            continue

        seen_document_ids.add(document_id)

        score = float(similarities[int(index)])

        results.append(
            {
                "id": document_id,
                "title": chunk["title"],
                "solution": chunk["solution"],
                "chunk_id": chunk["chunk_id"],
                "chunk_number": chunk["chunk_number"],
                "content": chunk["content"],
                "similarity_score": round(score, 4),
            }
        )

        if len(results) >= limit:
            break

    return results


# --------------------------------------------------
# 6. Local test
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

        results = search_documents(query, limit=3)

        for result in results:
            print(
                f"- {result['id']} | {result['title']} | "
                f"similarity={result['similarity_score']}"
            )
            print(f"  Matched passage: {result['content']}")
