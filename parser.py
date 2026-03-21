from pathlib import Path
from typing import List

from llama_index.core import Document
from llama_index.readers.file import PDFReader


def parse_pdf_to_documents(pdf_path: Path) -> List[Document]:
    """
    Parse a commercial loan PDF into LlamaIndex Documents.

    Each page becomes a Document with useful metadata such as page label and file name.
    This keeps page boundaries intact for downstream chunking and metadata tagging.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at: {pdf_path}")

    reader = PDFReader()
    # LlamaIndex's PDFReader already attaches page-level metadata.
    docs = reader.load_data(file=pdf_path)

    # Normalize and enrich metadata that will be useful for the war-room context.
    normalized_docs: List[Document] = []
    for doc in docs:
        metadata = dict(doc.metadata or {})
        metadata.setdefault("file_name", pdf_path.name)
        metadata.setdefault("source_path", str(pdf_path.resolve()))

        # Standardize page number metadata key for easier querying.
        if "page_label" in metadata:
            metadata["page_number"] = metadata["page_label"]

        normalized_docs.append(Document(text=doc.text, metadata=metadata))

    return normalized_docs