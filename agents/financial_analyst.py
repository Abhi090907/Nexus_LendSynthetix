"""
Financial Analysis Agent: extracts financial numbers and computes key credit metrics.
"""

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from .json_llm import invoke_json_llm


class FinancialAnalysisResult(BaseModel):
    """Structured output from the Financial Analyst."""

    financial_summary: str = Field(
        description="One-paragraph summary of the borrower's financial position and trends.",
    )
    metrics: Dict[str, str] = Field(
        default_factory=dict,
        description="Key credit metrics: revenue_growth, ebitda_margin, net_profit_margin, debt_trend, dscr, debt_to_ebitda.",
    )
    financial_risk_flags: List[str] = Field(
        default_factory=list,
        description="List of financial risk flags identified from the data.",
    )


FINANCIAL_JSON_SCHEMA = """{
  "financial_summary": "One-paragraph summary of financial position and trends.",
  "metrics": {
    "revenue_growth": "e.g. 20% YoY or N/A",
    "ebitda_margin": "e.g. 19.5% or N/A",
    "net_profit_margin": "e.g. 11.7% or N/A",
    "debt_trend": "e.g. Increasing from $3.8M to $4.9M or N/A",
    "dscr": "e.g. 1.52 or N/A",
    "debt_to_ebitda": "e.g. 1.5x or N/A"
  },
  "financial_risk_flags": ["risk 1", "risk 2"]
}"""


def run_financial_analyst(question: str, context: str) -> FinancialAnalysisResult:
    """
    Extract financial numbers from the retrieved context and compute key credit metrics.

    Returns structured JSON with financial_summary, metrics (revenue_growth, ebitda_margin,
    net_profit_margin, debt_trend, dscr, debt_to_ebitda), and financial_risk_flags.
    """
    prompt = f"""You are a Financial Analyst for a commercial bank. Extract financial numbers from the document context and compute key credit metrics.

You MUST base all numbers and metrics strictly on the provided document context. Do not invent figures. If a metric cannot be computed from the context, use "N/A".

Compute or extract:
- Revenue growth (year over year)
- EBITDA margin
- Net profit margin
- Total debt trend
- Debt Service Coverage Ratio (DSCR)
- Debt-to-EBITDA ratio

Identify any financial_risk_flags (e.g. declining margins, rising debt, low DSCR) that appear in the data.

EVALUATION QUESTION:
{question}

DOCUMENT CONTEXT:
{context}

You must return your response in valid JSON with this schema (use only the keys below; metrics must include the six keys shown):
{FINANCIAL_JSON_SCHEMA}

Return nothing but the JSON object."""

    return invoke_json_llm(
        prompt=prompt,
        default_dict={
            "financial_summary": "",
            "metrics": {
                "revenue_growth": "N/A",
                "ebitda_margin": "N/A",
                "net_profit_margin": "N/A",
                "debt_trend": "N/A",
                "dscr": "N/A",
                "debt_to_ebitda": "N/A",
            },
            "financial_risk_flags": [],
        },
        model_class=FinancialAnalysisResult,
    )
