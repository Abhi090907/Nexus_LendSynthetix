import re
from typing import List

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document, TextNode


def _looks_like_table(block: str) -> bool:
    """
    Heuristic to flag table-like text blocks.

    Financial tables usually have:
    - A high ratio of digits.
    - Delimiters like tabs or pipes.
    - Compact lines with repeated spacing.
    """
    text = block.strip()
    if not text:
        return False

    digit_count = sum(ch.isdigit() for ch in text)
    digit_ratio = digit_count / max(len(text), 1)

    has_table_delimiters = "\t" in text or "|" in text
    has_many_spaces = "  " in text

    return digit_ratio > 0.25 or has_table_delimiters or has_many_spaces


_FINANCIAL_CATEGORY_PATTERNS = [
    ("income_statement", r"(?i)\b(revenue|sales|turnover|ebitda|cogs|gross profit)\b"),
    ("balance_sheet", r"(?i)\b(assets|liabilities|equity|share capital|retained earnings)\b"),
    ("cash_flow", r"(?i)\b(cash flow|operating activities|investing activities|financing activities)\b"),
    ("loan_terms", r"(?i)\b(interest rate|tenor|maturity|covenant|security|collateral)\b"),
    ("company_profile", r"(?i)\b(company overview|about us|management team|business model)\b"),
]


def infer_financial_category(text: str) -> str:
    """
    Rough categorization of a block of financial text.

    This is intentionally simple and keyword-based so you can inspect and tune it
    as you see more documents.
    """
    for label, pattern in _FINANCIAL_CATEGORY_PATTERNS:
        if re.search(pattern, text):
            return label
    return "other"


def chunk_documents_to_nodes(documents: List[Document]) -> List[TextNode]:
    """
    Convert page-level Documents into semantically coherent TextNodes.

    - Uses larger chunks for narrative sections.
    - Uses smaller chunks for table-like sections.
    - Attaches page number, section hint, and financial category metadata.
    """
    narrative_splitter = SentenceSplitter(chunk_size=512, chunk_overlap=100)
    table_splitter = SentenceSplitter(chunk_size=256, chunk_overlap=50)

    nodes: List[TextNode] = []

    for doc in documents:
        base_meta = dict(doc.metadata or {})
        page_number = base_meta.get("page_number")
        file_name = base_meta.get("file_name")

        # Break page text into coarse blocks before applying sentence-based splitting.
        raw_blocks = [b.strip() for b in doc.text.split("\n\n") if b.strip()]

        for block in raw_blocks:
            is_table = _looks_like_table(block)
            splitter = table_splitter if is_table else narrative_splitter

            # Wrap block into a temporary Document so the splitter keeps metadata.
            temp_doc = Document(text=block, metadata=base_meta)
            block_nodes = splitter.get_nodes_from_documents([temp_doc])

            for node in block_nodes:
                # Short description of the block for quick filtering in queries.
                first_line = block.splitlines()[0].strip() if block.splitlines() else ""

                node.metadata.setdefault("page_number", page_number)
                node.metadata.setdefault("file_name", file_name)
                node.metadata.setdefault("section_hint", first_line[:120])
                node.metadata.setdefault("is_table_like", is_table)
                node.metadata.setdefault("financial_category", infer_financial_category(block))

                nodes.append(node)

    return nodes