"""
Compliance Officer (Auditor) agent.

Goal: ensure regulatory compliance. Has veto power: if it rejects, the workflow stops.
Focus: KYC, AML, sanctions, documentation completeness.
"""

from typing import List, Union

from pydantic import BaseModel, Field

from .json_llm import invoke_json_llm


class ComplianceMemo(BaseModel):
    """Structured compliance memo from the Compliance Officer."""

    recommendation: str = Field(description="APPROVE or REJECT (veto power).")
    summary: str = Field(description="One-paragraph compliance assessment.")
    blocking_issues: List[str] = Field(
        default_factory=list,
        description="Issues that require immediate REJECT (KYC, AML, sanctions, missing docs). Empty means no veto.",
    )
    kyc_notes: str = Field(default="", description="KYC completeness and findings.")
    aml_sanctions_notes: str = Field(
        default="",
        description="AML and sanctions screening notes.",
    )
    documentation_completeness: List[str] = Field(
        default_factory=list,
        description="Documentation gaps or completeness items.",
    )
    non_blocking_conditions: List[str] = Field(
        default_factory=list,
        description="Conditions that do not block approval but should be noted.",
    )
    evidence: List[str] = Field(
        default_factory=list,
        description="Quotes from the document context that support the reasoning.",
    )


COMPLIANCE_JSON_SCHEMA = """{
  "recommendation": "APPROVE | REJECT",
  "summary": "One-paragraph compliance assessment.",
  "blocking_issues": ["Only list issues that require immediate REJECT; leave empty [] if none"],
  "kyc_notes": "KYC completeness and findings.",
  "aml_sanctions_notes": "AML and sanctions screening notes.",
  "documentation_completeness": ["...", "..."],
  "non_blocking_conditions": ["..."],
  "evidence": ["exact quote from document supporting reasoning", "another quote..."]
}"""


def run_compliance_agent(
    question: str,
    context: str,
    previous_arguments: str = "",
    financial_analysis: Union[str, dict] = "",  # ← accepts both str and dict
) -> ComplianceMemo:
    """
    Produce a Compliance Officer memo. If blocking_issues is non-empty, the deal is REJECTED (veto).
    """
    prompt = f"""You are a Compliance Officer (Auditor) for a commercial bank. Your goal is to ensure regulatory compliance. You have VETO power: if you find blocking issues (KYC failures, AML/sanctions concerns, critical missing documentation), you must REJECT.

You must base your reasoning strictly on the provided context and financial analysis.
For every key claim, include supporting evidence from the document.
In the "evidence" array, list quotes or data points from the context. Only list a "blocking_issue" if the document explicitly states or clearly implies it; do not reject for missing information that the document does not claim to provide.

Review the full debate between Sales and Risk (including Sales's rebuttal). Ensure the loan meets AML, KYC, and regulatory standards regardless of the commercial arguments. Focus on: KYC, AML, sanctions, documentation completeness.

EVALUATION QUESTION:
{question}

DOCUMENT CONTEXT:
{context}
"""
    # ← fixed: handles both str and dict
    if financial_analysis:
        fa_text = financial_analysis if isinstance(financial_analysis, str) else str(financial_analysis)
        prompt += f"""

FINANCIAL ANALYSIS (for context):
{fa_text.strip()}
"""
    if previous_arguments.strip():
        prompt += f"""

FULL DEBATE (Sales memo, Risk memo, Sales rebuttal) — review for regulatory, AML, KYC, and documentation issues:
{previous_arguments}
"""

    prompt += f"""

You must return your response in valid JSON with this schema (use only the keys below; use empty arrays or empty strings where no data).
The "evidence" array MUST contain direct quotes from the DOCUMENT CONTEXT above that support your summary and any blocking_issues—do not list issues that lack a matching quote in the context.
{COMPLIANCE_JSON_SCHEMA}

Return nothing but the JSON object."""

    return invoke_json_llm(
        prompt=prompt,
        default_dict={
            "recommendation": "APPROVE",
            "summary": "",
            "blocking_issues": [],
            "kyc_notes": "",
            "aml_sanctions_notes": "",
            "documentation_completeness": [],
            "non_blocking_conditions": [],
            "evidence": [],
        },
        model_class=ComplianceMemo,
    )