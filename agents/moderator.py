"""
Moderator node: synthesizes Sales, Risk, and Compliance memos into final decision.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from .json_llm import invoke_json_llm


class ModeratorDecision(BaseModel):
    """Final decision from the Moderator (credit committee chair)."""

    final_recommendation: str = Field(
        description="One of: APPROVE, REJECT, CONDITIONAL_APPROVAL.",
    )
    reasoning: str = Field(
        description="Synthesis of all three memos and rationale for the decision.",
    )
    conditions: List[str] = Field(
        default_factory=list,
        description="Conditions to be met if final_recommendation is CONDITIONAL_APPROVAL.",
    )


MODERATOR_JSON_SCHEMA = """{
  "final_recommendation": "APPROVE | REJECT | CONDITIONAL_APPROVAL",
  "reasoning": "Synthesis of Sales, Risk, and Compliance views and rationale for the decision.",
  "conditions": ["condition 1", "condition 2"]
}"""


def run_moderator(
    question: str,
    context: str,
    sales_memo_text: str,
    risk_memo_text: str,
    compliance_memo_text: str,
    financial_analysis: Optional[dict] = None,
    sales_rebuttal_text: str = "",
    past_cases: str = "",
    market_intelligence: dict = None,
    risk_score: dict = None,
) -> ModeratorDecision:
    """
    Analyze the debate between Sales, Risk, and Compliance and produce the final decision.
    """
    fa_block = ""
    if financial_analysis:
        fa_block = "\nFINANCIAL ANALYSIS (for reference):\n" + str(financial_analysis)

    mi_block = ""
    if market_intelligence and isinstance(market_intelligence, dict):
        import json
        mi_str = json.dumps(market_intelligence, indent=2)
        mi_block = f"""
MARKET & GEOPOLITICAL CONTEXT:
{mi_str}
Consider market signals alongside the financial analysis in your final reasoning.
"""

    rebuttal_block = ""
    if (sales_rebuttal_text or "").strip():
        rebuttal_block = f"""

SALES REBUTTAL (Response to Risk):
{sales_rebuttal_text.strip()}
"""

    past_block = ""
    if (past_cases or "").strip():
        past_block = f"""

Below are similar past loan decisions and their outcomes. Use them as reference when forming your final decision, but prioritize the current debate and financial evidence.

SIMILAR PAST CASES:
{past_cases.strip()}
"""

    prompt = f"""You are the Moderator (credit committee chair) of a bank loan committee. Synthesize the debate below and make the final decision. Base your reasoning strictly on the provided context and memos; for key points, rely on evidence cited in the memos.

EVALUATION QUESTION:
{question}

DOCUMENT CONTEXT (for reference):
{context[:3000]}
{fa_block}
{past_block}

RELATIONSHIP MANAGER (SALES) INITIAL MEMO:
{sales_memo_text}

CREDIT UNDERWRITER (RISK) MEMO:
{risk_memo_text}
{rebuttal_block}
{mi_block}

COMPLIANCE OFFICER MEMO:
{compliance_memo_text}


Produce a final decision that weighs all three perspectives. Use APPROVE, REJECT, or CONDITIONAL_APPROVAL for final_recommendation. If CONDITIONAL_APPROVAL, list specific conditions in the "conditions" array.

"""

    if risk_score and "shap_explanation" in risk_score:
        shap_explanation = risk_score["shap_explanation"]
        prompt += f"\nThe top drivers of the risk score are: {shap_explanation}. Reference these in your reasoning when explaining the credit decision.\n"

    prompt += f"""
You must return your response in valid JSON with this schema (use only the keys below):
{MODERATOR_JSON_SCHEMA}

Return nothing but the JSON object."""

    return invoke_json_llm(
        prompt=prompt,
        default_dict={
            "final_recommendation": "CONDITIONAL_APPROVAL",
            "reasoning": "",
            "conditions": [],
        },
        model_class=ModeratorDecision,
    )
