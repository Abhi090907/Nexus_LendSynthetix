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
        description="Key credit metrics: revenue_growth, ebitda_margin, net_profit_margin, debt_trend, dscr, debt_to_ebitda, plus components for Altman Z-Score.",
    )
    financial_risk_flags: List[str] = Field(
        default_factory=list,
        description="List of financial risk flags identified from the data.",
    )
    altman_z: Dict[str, Any] = Field(
        default_factory=dict,
        description="Altman Z-Score calculation results.",
    )


FINANCIAL_JSON_SCHEMA = """{
  "financial_summary": "One-paragraph summary of financial position and trends.",
  "metrics": {
    "revenue_growth": "e.g. 20% YoY or N/A",
    "ebitda_margin": "e.g. 19.5% or N/A",
    "net_profit_margin": "e.g. 11.7% or N/A",
    "debt_trend": "e.g. Increasing from $3.8M to $4.9M or N/A",
    "dscr": "e.g. 1.52 or N/A",
    "debt_to_ebitda": "e.g. 1.5x or N/A",
    "working_capital": "plain number only, e.g. 1200000 or N/A",
    "total_assets": "plain number only, e.g. 10000000 or N/A",
    "retained_earnings": "plain number only, e.g. 2500000 or N/A",
    "ebit": "plain number only, e.g. 1500000 or N/A",
    "market_cap_or_book_equity": "plain number only, e.g. 4000000 or N/A",
    "total_liabilities": "plain number only, e.g. 6000000 or N/A",
    "revenue": "plain number only, e.g. 15000000 or N/A"
  },
  "financial_risk_flags": ["risk 1", "risk 2"]
}"""


def calculate_altman_z(metrics: Dict[str, str]) -> Dict[str, Any]:
    def parse_num(v: Any) -> float:
        if v == "N/A" or not v:
            return None
        try:
            import re
            cleaned = re.sub(r'[^\d\.-]', '', str(v))
            if not cleaned:
                return None
            return float(cleaned)
        except ValueError:
            return None

    wc = parse_num(metrics.get("working_capital", "N/A"))
    ta = parse_num(metrics.get("total_assets", "N/A"))
    re = parse_num(metrics.get("retained_earnings", "N/A"))
    ebit = parse_num(metrics.get("ebit", "N/A"))
    eq = parse_num(metrics.get("market_cap_or_book_equity", "N/A"))
    tl = parse_num(metrics.get("total_liabilities", "N/A"))
    rev = parse_num(metrics.get("revenue", "N/A"))

    if ta is None or ta == 0:
        return {"z_score": None, "z_zone": "UNKNOWN", "z_interpretation": "Total Assets missing or zero."}

    if None in [wc, re, ebit, eq, tl, rev]:
        return {"z_score": None, "z_zone": "UNKNOWN", "z_interpretation": "Missing data for Z-score."}

    x1 = wc / ta
    x2 = re / ta
    x3 = ebit / ta
    x4 = float('inf') if tl == 0 else eq / tl
    if x4 == float('inf'):
        x4 = eq
    x5 = rev / ta

    z_score = 0.717 * x1 + 0.847 * x2 + 3.107 * x3 + 0.420 * x4 + 0.998 * x5

    if z_score > 2.9:
        z_zone = "SAFE"
    elif z_score >= 1.23:
        z_zone = "GREY"
    else:
        z_zone = "DISTRESS"
        
    return {
        "z_score": round(z_score, 3),
        "z_zone": z_zone,
        "z_interpretation": f"Score {z_score:.2f} falls in {z_zone} zone."
    }


def run_financial_analyst(question: str, context: str) -> FinancialAnalysisResult:
    """
    Extract financial numbers from the retrieved context and compute key credit metrics.

    Returns structured JSON with financial_summary, metrics, altman_z calculation, and risk flags.
    """
    prompt = f"""You are a Financial Analyst for a commercial bank. Extract financial numbers from the document context and compute key credit metrics.

You MUST base all numbers and metrics strictly on the provided document context. Do not invent figures. If a metric cannot be computed from the context, use "N/A".

Multiple source documents are provided. When citing a figure, note which source document it came from. If the same metric appears in multiple documents, use the most recent one and flag any discrepancies.

Compute or extract (instruct the LLM to extract or estimate these from context, use "N/A" if not found):
- Revenue growth (year over year)
- EBITDA margin
- Net profit margin
- Total debt trend
- Debt Service Coverage Ratio (DSCR)
- Debt-to-EBITDA ratio
- Working capital
- Total assets
- Retained earnings
- EBIT
- Market cap or book value of equity
- Total liabilities
- Revenue

IMPORTANT: For working_capital, total_assets, retained_earnings, ebit, market_cap_or_book_equity, total_liabilities, and revenue, you MUST output strictly plain numbers (e.g., 1200000, not $1.2M) or 'N/A' if unknown.

Identify any financial_risk_flags (e.g. declining margins, rising debt, low DSCR) that appear in the data.

EVALUATION QUESTION:
{question}

DOCUMENT CONTEXT:
{context}

You must return your response in valid JSON with this schema (use only the keys below):
{FINANCIAL_JSON_SCHEMA}

Return nothing but the JSON object."""

    result = invoke_json_llm(
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
                "working_capital": "N/A",
                "total_assets": "N/A",
                "retained_earnings": "N/A",
                "ebit": "N/A",
                "market_cap_or_book_equity": "N/A",
                "total_liabilities": "N/A",
                "revenue": "N/A",
            },
            "financial_risk_flags": [],
        },
        model_class=FinancialAnalysisResult,
    )

    result.altman_z = calculate_altman_z(result.metrics)
    return result
