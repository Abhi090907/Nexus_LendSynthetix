"""
Sales Rebuttal agent: Relationship Manager responds to Risk's critique.
"""

from typing import List
from pydantic import BaseModel, Field

from .json_llm import invoke_json_llm


class SalesRebuttalMemo(BaseModel):
    """Structured rebuttal from Sales in response to Risk."""

    summary: str = Field(description="Brief summary of the rebuttal position.")

    response_to_risk: str = Field(
        description="Direct response to the Risk team's concerns; clarify or defend the business case."
    )

    recommendation: str = Field(
        description="APPROVE or REJECT or CONDITIONAL after considering Risk's critique."
    )

    evidence: List[str] = Field(
        default_factory=list,
        description="Quotes or data points from the document that support the response."
    )


REBUTTAL_JSON_SCHEMA = """{
  "summary": "Brief summary of the rebuttal position.",
  "response_to_risk": "Direct response to Risk's concerns; clarify or defend the business case.",
  "recommendation": "APPROVE | REJECT | CONDITIONAL",
  "evidence": ["quote or data point from context", "..."]
}"""


def run_sales_rebuttal(
    question: str,
    context: str,
    financial_analysis,
    sales_memo_text: str,
    risk_memo_text: str,
) -> SalesRebuttalMemo:
    """
    Sales responds to Risk's critique.
    """

    # ----------------------------------------------------
    # Normalize financial_analysis safely
    # ----------------------------------------------------
    financial_analysis_text = ""

    if isinstance(financial_analysis, dict):
        financial_analysis_text = str(financial_analysis)

    elif isinstance(financial_analysis, str):
        financial_analysis_text = financial_analysis

    # ----------------------------------------------------
    # Build Prompt
    # ----------------------------------------------------
    prompt = f"""You are the Relationship Manager (Sales) for a commercial bank.

The Risk team has raised concerns about the loan proposal. Respond to their critique.
Clarify or defend the business case if appropriate.

Base your response strictly on the provided context and financial analysis.
Cite evidence for key claims.

EVALUATION QUESTION:
{question}

DOCUMENT CONTEXT:
{context}
"""

    # ----------------------------------------------------
    # Financial Analysis Section
    # ----------------------------------------------------
    if financial_analysis_text.strip():
        prompt += f"""

FINANCIAL ANALYSIS:
{financial_analysis_text}
"""

    # ----------------------------------------------------
    # Sales vs Risk Debate
    # ----------------------------------------------------
    prompt += f"""

YOUR ORIGINAL SALES MEMO:
{sales_memo_text}

RISK TEAM'S CRITIQUE (respond to this):
{risk_memo_text}

You must return your response in valid JSON with this schema:

{REBUTTAL_JSON_SCHEMA}

The "evidence" array must contain quotes or data points from the DOCUMENT CONTEXT
that support your response.

Return nothing but the JSON object.
"""

    # ----------------------------------------------------
    # Call LLM
    # ----------------------------------------------------
    return invoke_json_llm(
        prompt=prompt,
        default_dict={
            "summary": "",
            "response_to_risk": "",
            "recommendation": "CONDITIONAL",
            "evidence": [],
        },
        model_class=SalesRebuttalMemo,
    )
