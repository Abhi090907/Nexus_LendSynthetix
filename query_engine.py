from typing import List

from llama_index.core import StorageContext, VectorStoreIndex

from config import get_collection_name
from embedder import get_embedding_model
from qdrant_store import get_qdrant_client, get_qdrant_vector_store


def _format_nodes_as_context(nodes) -> str:
    """
    Turn retrieved nodes into a readable text context string.

    Each chunk is prefixed with lightweight metadata to help downstream
    agents (Sales, Risk, Compliance) understand provenance.
    """
    parts: List[str] = []
    for node in nodes:
        meta = node.metadata or {}
        page = meta.get("page_number", "?")
        section = meta.get("section_hint", "").strip()
        source_file = meta.get("source_file", "Unknown")
        
        header = f"[Source: {source_file}] [page {page}]"
        if section:
            header = f"{header} {section}"

        parts.append(f"{header}\n{node.get_content()}")

    return "\n\n---\n\n".join(parts)


def query_loan_documents(question: str) -> str:
    """
    Retrieve the top-k relevant chunks from the existing Qdrant collection.

    This function:
    - connects to the existing "loan_documents" Qdrant collection
    - uses the same local HuggingFace embedding model (BAAI/bge-small-en-v1.5)
    - constructs a LlamaIndex VectorStoreIndex over that collection
    - performs pure vector retrieval (no LLMs) to get the top 5 chunks
    - returns the concatenated text context
    """
    if not question or not question.strip():
        raise ValueError("Question must be a non-empty string.")

    collection_name = get_collection_name(None)  # defaults to "loan_documents"

    # Reuse the same embedding model configuration as the ingestion pipeline.
    embed_model = get_embedding_model()

    # Connect to Qdrant and wrap it as a LlamaIndex vector store.
    qdrant_client = get_qdrant_client()
    vector_store = get_qdrant_vector_store(
        client=qdrant_client,
        collection_name=collection_name,
    )

    # Build an index over the existing collection. This does NOT re-ingest data;
    # it just attaches LlamaIndex abstractions over the existing vectors.
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
        embed_model=embed_model,
    )

    # Use the index purely as a retriever to avoid any LLM calls. This will
    # compute the embedding for the question using the same HF model and run
    # a similarity search in Qdrant.
    retriever = index.as_retriever(similarity_top_k=5)
    nodes = retriever.retrieve(question)

    if not nodes:
        return "No relevant context found in loan_documents."

    return _format_nodes_as_context(nodes)

