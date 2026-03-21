from typing import Any

from llama_index.embeddings.fastembed import FastEmbedEmbedding

from config import get_settings


def get_embedding_model() -> Any:
    """
    Configure and return the embedding model.

    Uses FastEmbed (ONNX-based) instead of HuggingFace to avoid
    torch DLL issues on Windows. Same model, no torch dependency.
    """
    settings = get_settings()

    embed_model = FastEmbedEmbedding(
        model_name=settings.embedding_model_name,
    )
    return embed_model