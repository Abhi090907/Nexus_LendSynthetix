"""
Credit Underwriter (Risk) agent.

Goal: protect bank capital.
Focus: DSCR, leverage ratio, cashflow volatility, collateral quality.
"""

from typing import List
from pydantic import BaseModel, Field

from .json_llm import invoke_json_llm


class RiskMemo(BaseModel):
    """Structured risk memo from the Credit Underwriter."""

    recommendation: str = Field(description="APPROVE or REJECT or CONDITIONAL")
    summary: str = Field(description="One-paragraph risk assessment summary.")

    dscr_analysis: str = Field(
        default="",
        description="Debt service coverage ratio and sustainability.",
    )

    leverage_analysis: str = Field(
        default="",
        description="Leverage ratio and debt levels.",
    )

    cashflow_volatility_concerns: List[str] = Field(
        default_factory=list,
        description="Cashflow volatility or liquidity concerns.",
    )

    collateral_quality: str = Field(
        default="",
        description="Assessment of collateral quality and recovery.",
    )

    other_risks: List[str] = Field(
        default_factory=list,
        description="Other material financial risks.",
    )

    evidence: List[str] = Field(
        default_factory=list,
        description="Quotes from the document context that support the reasoning.",
    )


RISK_JSON_SCHEMA = """{
  "recommendation": "APPROVE | REJECT | CONDITIONAL",
  "summary": "One-paragraph risk assessment summary.",
  "dscr_analysis": "Debt service coverage ratio and sustainability.",
  "leverage_analysis": "Leverage ratio and debt levels.",
  "cashflow_volatility_concerns": ["...", "..."],
  "collateral_quality": "Assessment of collateral quality and recovery.",
  "other_risks": ["..."],
  "evidence": ["exact quote from document supporting reasoning", "another quote..."]
}"""


def run_risk_agent(
    question: str,
    context: str,
    previous_arguments: str = "",
    financial_analysis: str = "",
    past_cases="",
) -> RiskMemo:
    """
    Produce a Credit Underwriter risk memo from the loan context.
    """

    # ----------------------------------------------------
    # Normalize past_cases safely (list → string)
    # ----------------------------------------------------
    past_cases_text = ""

    if isinstance(past_cases, list):
        past_cases_text = "\n".join(str(x) for x in past_cases)

    elif isinstance(past_cases, str):
        past_cases_text = past_cases

    # ----------------------------------------------------
    # Build Prompt
    # ----------------------------------------------------
    prompt = f"""You are a Credit Underwriter (Risk) for a commercial bank. Your goal is to protect bank capital.

You must base your reasoning strictly on the provided context and financial analysis.
For every key claim, include supporting evidence from the document.

In the "evidence" array, list quotes or data points from the context (e.g. "DSCR is estimated at 1.52", "Total debt increased from $3.8M to $4.9M"). Do not invent facts.

Review the Sales memo. Identify any financial or credit risks they overlooked.
Focus on DSCR, leverage, cashflow volatility, and collateral quality.

You may disagree with Sales if the evidence supports it.

EVALUATION QUESTION:
{question}

DOCUMENT CONTEXT:
{context}
"""

    # ----------------------------------------------------
    # Past cases
    # ----------------------------------------------------
    if past_cases_text.strip():
        prompt += f"""

Below are similar past loan decisions and their outcomes.
Use them as reference when forming your risk view,
but prioritize the current financial evidence.

SIMILAR PAST CASES:
{past_cases_text}
"""

    # ----------------------------------------------------
    # Financial analysis
    # ----------------------------------------------------
    if isinstance(financial_analysis, str) and financial_analysis.strip():
        prompt += f"""

FINANCIAL ANALYSIS (use for evidence and reasoning):
{financial_analysis}
"""

    # ----------------------------------------------------
    # Sales memo arguments
    # ----------------------------------------------------
    if isinstance(previous_arguments, str) and previous_arguments.strip():
        prompt += f"""

RELATIONSHIP MANAGER (SALES) MEMO — review and identify risks they may have overlooked:
{previous_arguments}
"""

    # ----------------------------------------------------
    # JSON instructions
    # ----------------------------------------------------
    prompt += f"""

You must return your response in valid JSON with this schema.
Use only the keys below.

The "evidence" array MUST contain direct quotes from the DOCUMENT CONTEXT
that support your summary and risk analysis.

Do NOT invent facts.

{RISK_JSON_SCHEMA}

Return nothing but the JSON object.
"""

    # ----------------------------------------------------
    # Call LLM
    # ----------------------------------------------------
    return invoke_json_llm(
        prompt=prompt,
        default_dict={
            "recommendation": "CONDITIONAL",
            "summary": "",
            "dscr_analysis": "",
            "leverage_analysis": "",
            "cashflow_volatility_concerns": [],
            "collateral_quality": "",
            "other_risks": [],
            "evidence": [],
        },
        model_class=RiskMemo,
    )
