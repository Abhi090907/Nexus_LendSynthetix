"""
Case Memory: store and retrieve past loan decisions for learning and reference.

Uses the same embedding model as document search; stores cases in Qdrant collection "loan_case_memory".
Embedding for storage: question + financial_summary. Retrieval: embed question, return top_k similar cases.
"""

import logging
import uuid
from typing import Any, Dict, List

from qdrant_client.http import models as qmodels

from embedder import get_embedding_model
from qdrant_store import get_qdrant_client, ensure_collection

logger = logging.getLogger(__name__)

CASE_MEMORY_COLLECTION = "loan_case_memory"

# BGE-small-en-v1.5 dimension; same embedder as document search
DEFAULT_VECTOR_SIZE = 384


def _get_embedding(text: str) -> List[float]:
    """Get embedding vector for text using the project's embedding model."""
    model = get_embedding_model()
    # LlamaIndex HuggingFaceEmbedding: get_query_embedding returns List[float]
    return model.get_query_embedding(text)


def _build_case_payload(
    question: str,
    financial_analysis: Dict[str, Any],
    risk_score: Dict[str, Any],
    final_decision: Dict[str, Any],
) -> Dict[str, Any]:
    """Build the case dict to store (and use as Qdrant payload)."""
    fa = financial_analysis or {}
    rs = risk_score or {}
    fd = final_decision or {}
    return {
        "question": question,
        "financial_summary": fa.get("financial_summary", ""),
        "risk_score": rs.get("risk_score"),
        "risk_level": rs.get("risk_level", ""),
        "final_recommendation": fd.get("final_recommendation", ""),
        "reasoning": fd.get("reasoning", ""),
        "conditions": fd.get("conditions") or [],
    }


def store_case_memory(
    question: str,
    financial_analysis: Dict[str, Any],
    risk_score: Dict[str, Any],
    final_decision: Dict[str, Any],
) -> None:
    """
    Store a completed loan evaluation as a case in Qdrant collection "loan_case_memory".

    Embeds question + financial_summary for similarity search. Uses the same embedding
    model as document retrieval.
    """
    client = get_qdrant_client()
    ensure_collection(
        client,
        collection_name=CASE_MEMORY_COLLECTION,
        vector_size=DEFAULT_VECTOR_SIZE,
        distance=qmodels.Distance.COSINE,
    )

    payload = _build_case_payload(question, financial_analysis, risk_score, final_decision)
    financial_summary = payload.get("financial_summary") or ""
    text_to_embed = f"{question}\n{financial_summary}".strip()
    vector = _get_embedding(text_to_embed)

    point_id = str(uuid.uuid4())
    client.upsert(
        collection_name=CASE_MEMORY_COLLECTION,
        points=[
            qmodels.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        ],
    )
    logger.info("Stored case memory: %s", point_id)


def retrieve_similar_cases(question: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieve top_k past cases most similar to the given question.

    Uses the same embedding model; returns list of case payloads (question,
    financial_summary, risk_score, risk_level, final_recommendation, reasoning, conditions).
    """
    client = get_qdrant_client()
    try:
        collections = client.get_collections().collections
        if not any(c.name == CASE_MEMORY_COLLECTION for c in collections):
            return []
    except Exception:
        return []

    vector = _get_embedding(question)
    results = client.query_points(
    collection_name=CASE_MEMORY_COLLECTION,
    query=vector,
    limit=top_k,
    ).points

    return [hit.payload for hit in results if hit.payload is not None]

def format_cases_for_prompt(cases: List[Dict[str, Any]]) -> str:
    """Format retrieved cases for agent prompts."""
    
    if not cases:  # pragma: no cover
        return ""

    lines = ["PAST LOAN CASES:\n"]

    for i, c in enumerate(cases, 1):
        lines.append(
            f"""
Case {i}
Question: {c.get("question")}
Risk Score: {c.get("risk_score")}
Risk Level: {c.get("risk_level")}
Decision: {c.get("final_recommendation")}
Reasoning: {c.get("reasoning")}
"""
        )

    return "\n".join(lines)
