import logging
from pathlib import Path
from typing import Optional

from llama_index.core import StorageContext, VectorStoreIndex

from chunker import chunk_documents_to_nodes
from config import get_collection_name
from embedder import get_embedding_model
from parser import parse_pdf_to_documents
from qdrant_store import get_qdrant_client, get_qdrant_vector_store

logger = logging.getLogger(__name__)


def ingest_pdf_pipeline(pdf_path: Path, collection_name: Optional[str] = None) -> None:
    """
    End-to-end ingestion pipeline:

    1. Parse PDF into page-level Documents.
    2. Chunk Documents into optimized TextNodes for financial analysis.
    3. Generate embeddings for nodes.
    4. Upsert nodes into a Qdrant collection via LlamaIndex.
    """
    resolved_collection = get_collection_name(collection_name)
    logger.info("Starting ingestion for '%s' into collection '%s'", pdf_path, resolved_collection)

    # 1) Parse the raw PDF into LlamaIndex Documents.
    documents = parse_pdf_to_documents(pdf_path)
    logger.info("Parsed %d document(s) from PDF", len(documents))

    # 2) Chunk into semantically meaningful nodes with rich metadata.
    nodes = chunk_documents_to_nodes(documents)
    logger.info("Created %d text nodes after chunking", len(nodes))

    if not nodes:
        logger.warning("No nodes were created from the PDF; skipping ingestion.")
        return

    # 3) Prepare embedding model and Qdrant vector store.
    embed_model = get_embedding_model()
    qdrant_client = get_qdrant_client()
    vector_store = get_qdrant_vector_store(
        client=qdrant_client,
        collection_name=resolved_collection,
    )

    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Trigger embedding + storage. LlamaIndex handles batching under the hood.
    index = VectorStoreIndex(
        nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )

    # Keeping the index object around (or persisting it) will make querying easier later.
    logger.info(
        "Finished ingesting %d nodes into Qdrant collection '%s'.",
        len(nodes),
        resolved_collection,
    )

    # Example of how you might use the index later (not executed here):
    # query_engine = index.as_query_engine()
    # response = query_engine.query("What is the borrower's EBITDA in 2024?")
    # print(response)


# --- Inngest Integration (event-driven ingestion) ---

try:
    import inngest
except ImportError:  # pragma: no cover - optional dependency at runtime
    inngest = None


if inngest is not None:
    inngest_client = inngest.Inngest(app_id="lendsynthetix-loan-war-room")

    @inngest_client.create_function(
        fn_id="ingest-loan-pdf",
        trigger=inngest.TriggerEvent(event="loan/pdf_uploaded"),
    )
    def ingest_loan_pdf_fn(ctx: inngest.Context, event: inngest.Event) -> dict:
        """
        Inngest function that ingests a PDF when a `loan/pdf_uploaded` event is received.

        Event shape (example):
        {
          "name": "loan/pdf_uploaded",
          "data": {
            "pdf_path": "./data/sample_loan.pdf",
            "collection_name": "loan_documents"
          }
        }
        """
        data = event.data or {}
        pdf_path_str = data.get("pdf_path")
        collection_override = data.get("collection_name")

        if not pdf_path_str:
            raise ValueError("Event data must include 'pdf_path'.")

        pdf_path = Path(pdf_path_str)
        ingest_pdf_pipeline(pdf_path=pdf_path, collection_name=collection_override)

        return {
            "status": "ok",
            "pdf_path": str(pdf_path),
            "collection_name": get_collection_name(collection_override),
        }