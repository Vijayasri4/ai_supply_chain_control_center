"""
Contract Retrieval Agent (RAG pipeline).

Chunks a vendor contract into clause-sized pieces, embeds them, and
stores them in a ChromaDB collection so the AI assistant retrieves
only the clauses relevant to a specific question instead of stuffing
(and truncating) the entire contract into every prompt.

Uses ChromaDB's bundled default embedding model (all-MiniLM-L6-v2,
runs locally on your machine, no API key needed). The very first
question after uploading a contract triggers a one-off download of
that model (a few tens of MB), so it'll be a little slower than every
question after it.
"""

from __future__ import annotations

import re

import chromadb


def chunk_contract(text: str, max_chunk_chars: int = 800) -> list[str]:
    """Split contract text into clause-sized chunks.

    Splits on common clause boundaries first (numbered clauses like
    "1.", "2.1", or headings like "Section 3", "Clause 4:", "ARTICLE 5").
    If no such markers are found, falls back to splitting on blank
    lines. Any piece still too long is hard-split so no single chunk
    overwhelms the embedding model or the prompt.
    """
    clause_pattern = re.compile(
        r"(?=\n\s*(?:\d+(?:\.\d+)*\.?\s|Section\s+\d+|Clause\s+\d+|ARTICLE\s+\d+)\b)",
        re.IGNORECASE,
    )
    rough_chunks = [c.strip() for c in clause_pattern.split(text) if c.strip()]

    if len(rough_chunks) <= 1:
        rough_chunks = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]

    chunks: list[str] = []
    for piece in rough_chunks:
        if len(piece) <= max_chunk_chars:
            chunks.append(piece)
        else:
            start = 0
            while start < len(piece):
                chunks.append(piece[start:start + max_chunk_chars])
                start += max_chunk_chars

    return chunks or [text[:max_chunk_chars]]


def build_contract_index(chunks: list[str], collection_name: str = "vendor_contract"):
    """Embed the given chunks and store them in a fresh in-memory
    ChromaDB collection so re-uploading a contract doesn't mix clauses
    from two different documents together.

    Returns the collection, meant to be kept in st.session_state for
    the rest of the session (rebuilding it on every rerun would
    re-embed the whole contract on every interaction).
    """
    client = chromadb.Client()
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass  # collection didn't exist yet - nothing to delete

    collection = client.create_collection(name=collection_name)
    collection.add(
        documents=chunks,
        ids=[f"clause_{i}" for i in range(len(chunks))],
    )
    return collection


def retrieve_relevant_clauses(collection, question: str, top_k: int = 4) -> list[str]:
    """Retrieve the clauses most relevant to the given question."""
    results = collection.query(query_texts=[question], n_results=top_k)
    return results["documents"][0] if results["documents"] else []