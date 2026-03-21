"""
Relationship Manager (Sales) agent.

Goal: maximize loan approvals and highlight growth potential.
Focus: revenue growth, new contracts, market reputation, expansion opportunities.
"""

from typing import List, Union

from pydantic import BaseModel, Field

from .json_llm import invoke_json_llm


class SalesMemo(BaseModel):
    """Structured approval memo from the Relationship Manager."""

    recommendation: str = Field(description="APPROVE or REJECT or CONDITIONAL")
    summary: str = Field(description="One-paragraph executive summary of the deal.")

    revenue_growth_highlights: List[str] = Field(
        default_factory=list,
        description="Bullet points on revenue growth and trends.",
    )

    new_contracts_and_opportunities: List[str] = Field(
        default_factory=list,
        description="New contracts, pipeline, or expansion opportunities.",
    )

    market_reputation: str = Field(
        default="",
        description="Brief note on market position and reputation.",
    )

    risks_acknowledged: List[str] = Field(
        default_factory=list,
        description="Risks the sales side acknowledges (if any).",
    )

    evidence: List[str] = Field(
        default_factory=list,
        description="Quotes from the document context that support the reasoning.",
    )


SALES_JSON_SCHEMA = """{
  "recommendation": "APPROVE | REJECT | CONDITIONAL",
  "summary": "One-paragraph executive summary of the deal.",
  "revenue_growth_highlights": ["...", "..."],
  "new_contracts_and_opportunities": ["...", "..."],
  "market_reputation": "Brief note on market position and reputation.",
  "risks_acknowledged": ["..."],
  "evidence": ["exact quote from document supporting reasoning", "another quote..."]
}"""


def run_sales_agent(
    question: str,
    context: str,
    previous_arguments: str = "",
    financial_analysis: str = "",
    past_cases: Union[str, List[str]] = "",
) -> SalesMemo:
    """
    Produce a Relationship Manager approval memo from the loan context.
    """

    # -------- FIX: Normalize past_cases safely --------
    past_cases_text = ""

    if isinstance(past_cases, list):
        past_cases_text = "\n".join(str(x) for x in past_cases)
    elif isinstance(past_cases, str):
        past_cases_text = past_cases
    # --------------------------------------------------

    prompt = f"""You are a Relationship Manager (Sales) for a commercial bank. Your goal is to maximize loan approvals and highlight growth potential.

You must base your reasoning strictly on the provided context and financial analysis.
For every key claim, include supporting evidence from the document.

In the "evidence" array, list quotes or data points from the context
(e.g. "Revenue increased from $12.4M in 2022 to $16.9M in 2024",
"DSCR is estimated at 1.52"). Do not invent facts.

EVALUATION QUESTION:
{question}

DOCUMENT CONTEXT (from loan documents):
{context}
"""

    if past_cases_text.strip():
        prompt += f"""

Below are similar past loan decisions and their outcomes.
Use them as reference when forming your recommendation,
but prioritize the current financial evidence.

SIMILAR PAST CASES:
{past_cases_text}
"""

    if isinstance(financial_analysis, str) and financial_analysis.strip():
        prompt += f"""

FINANCIAL ANALYSIS (use for evidence and reasoning):
{financial_analysis}
"""

    if isinstance(previous_arguments, str) and previous_arguments.strip():
        prompt += f"""

PREVIOUS ARGUMENTS FROM OTHER DEPARTMENTS (for context only):
{previous_arguments}
"""

    prompt += f"""

You must return your response in valid JSON with this schema.
Use only the keys below. Use empty arrays or empty strings where no data.

The "evidence" array MUST contain direct quotes from the DOCUMENT CONTEXT
that support your summary and recommendation.

{SALES_JSON_SCHEMA}

Return nothing but the JSON object.
"""

    return invoke_json_llm(
        prompt=prompt,
        default_dict={
            "recommendation": "CONDITIONAL",
            "summary": "",
            "revenue_growth_highlights": [],
            "new_contracts_and_opportunities": [],
            "market_reputation": "",
            "risks_acknowledged": [],
            "evidence": [],
        },
        model_class=SalesMemo,
    )
