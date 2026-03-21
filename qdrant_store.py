import logging
from typing import Optional

from qdrant_client import QdrantClient  # ← add this line
from qdrant_client.http import models as qmodels

from llama_index.vector_stores.qdrant import QdrantVectorStore

logger = logging.getLogger(__name__)

# rest of your code unchanged...


# Local path used by both ingestion pipeline and query engine so they share the same DB.
QDRANT_LOCAL_PATH = "./qdrant_db"


def get_qdrant_client() -> QdrantClient:
    """
    Create a QdrantClient using local file storage.

    Both the ingestion pipeline and the query engine use this same client
    configuration, so they connect to the same collection (e.g. "loan_documents")
    at the same path (QDRANT_LOCAL_PATH).
    """
    client = QdrantClient(path=QDRANT_LOCAL_PATH)
    return client


def ensure_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int,
    distance: qmodels.Distance = qmodels.Distance.COSINE,
) -> None:
    """
    Create the collection if it does not exist.

    If the collection exists, we trust its configuration and avoid destructive
    operations like recreation, which could wipe prior data.
    """
    collections = client.get_collections().collections
    existing = {c.name for c in collections}

    if collection_name in existing:
        logger.info("Using existing Qdrant collection: %s", collection_name)
        return

    logger.info(
        "Creating Qdrant collection '%s' with vector size %d and distance %s",
        collection_name,
        vector_size,
        distance,
    )
    client.create_collection(
        collection_name=collection_name,
        vectors_config=qmodels.VectorParams(size=vector_size, distance=distance),
    )


def get_qdrant_vector_store(
    client: Optional[QdrantClient],
    collection_name: str,
) -> QdrantVectorStore:
    """
    Wrap Qdrant client into a LlamaIndex QdrantVectorStore.

    The embedding model defines the actual vector dimensionality; we only ensure
    that the collection exists with a compatible configuration.
    """
    if client is None:
        client = get_qdrant_client()

    # The vector size will be validated implicitly when you insert vectors.
    # We don't enforce it here since LlamaIndex handles it during index creation.
    vector_store = QdrantVectorStore(
        client=client,
        collection_name=collection_name,
    )
    return vector_store