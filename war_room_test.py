"""
Test script for the LendSynthetix War Room (AI credit underwriting engine).

Run from project root:
python war_room_test.py

Prints:

* Retrieved Context
* Financial Analysis
* Sales Memo
* Risk Memo
* Sales Rebuttal
* Compliance Memo
* Risk Score
* Stress Test Results
* Final Decision
"""

import json
import logging
import os

from war_room_graph import run_war_room


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def main() -> None:

    question = (
        "Should we approve this commercial loan? "
        "Summarize the key risks and opportunities and recommend "
        "APPROVE, REJECT, or CONDITIONAL APPROVAL."
    )

    print("=" * 60)
    print("LendSynthetix – Loan War Room")
    print("=" * 60)

    print("\nEvaluation question:", question)
    print()

    result = run_war_room(question)

    # ------------------------------------------------
    # Retrieved Context
    # ------------------------------------------------

    print("-" * 60)
    print("RETRIEVED CONTEXT (excerpt)")
    print("-" * 60)

    context = result.get("context") or ""

    print(context[:1500] + ("..." if len(context) > 1500 else ""))
    print()

    # ------------------------------------------------
    # Financial Analysis
    # ------------------------------------------------

    print("-" * 60)
    print("FINANCIAL ANALYSIS")
    print("-" * 60)

    fa = result.get("financial_analysis") or {}
    print(json.dumps(fa, indent=2))
    print()

    # ------------------------------------------------
    # Sales Memo
    # ------------------------------------------------

    print("-" * 60)
    print("SALES MEMO")
    print("-" * 60)

    sales = result.get("sales_memo") or {}
    print(json.dumps(sales, indent=2))
    print()

    # ------------------------------------------------
    # Risk Memo
    # ------------------------------------------------

    print("-" * 60)
    print("RISK MEMO")
    print("-" * 60)

    risk = result.get("risk_memo") or {}
    print(json.dumps(risk, indent=2))
    print()

    # ------------------------------------------------
    # Sales Rebuttal
    # ------------------------------------------------

    print("-" * 60)
    print("SALES REBUTTAL")
    print("-" * 60)

    rebuttal = result.get("sales_rebuttal") or {}
    print(json.dumps(rebuttal, indent=2))
    print()

    # ------------------------------------------------
    # Compliance Memo
    # ------------------------------------------------

    print("-" * 60)
    print("COMPLIANCE MEMO")
    print("-" * 60)

    compliance = result.get("compliance_memo") or {}
    print(json.dumps(compliance, indent=2))
    print()

    # ------------------------------------------------
    # Risk Score
    # ------------------------------------------------

    print("-" * 60)
    print("RISK SCORE")
    print("-" * 60)

    rs = result.get("risk_score") or {}

    score = rs.get("risk_score", "N/A")
    level = rs.get("risk_level", "N/A")

    print(f"RISK SCORE: {score} ({level})")

    for driver in rs.get("key_drivers") or []:
        print(f"  • {driver}")

    print()

    # ------------------------------------------------
    # Stress Testing Results
    # ------------------------------------------------

    print("-" * 60)
    print("STRESS TEST RESULTS")
    print("-" * 60)

    stress_results = result.get("stress_test_results") or {}

    if not stress_results:
        print("No stress test results available.\n")
    else:
        for scenario, data in stress_results.items():
            score = data.get("risk_score", "N/A")
            level = data.get("risk_level", "N/A")
            print(f"{scenario} → Score {score} ({level})")

    print()

    # ------------------------------------------------
    # Final Decision
    # ------------------------------------------------

    print("-" * 60)
    print("FINAL DECISION")
    print("-" * 60)

    final = result.get("final_decision") or {}

    print(f"FINAL RECOMMENDATION: {final.get('final_recommendation', 'N/A')}")

    print(f"\nReasoning:\n{final.get('reasoning', 'N/A')}")

    conditions = final.get("conditions") or []

    if conditions:
        print("\nConditions:")
        for c in conditions:
            print(f"  • {c}")

    print()
    print("=" * 60)

    # ------------------------------------------------
    # Save output as JSON for the UI
    # ------------------------------------------------

    output = {
        "question":           question,
        "financial_analysis": result.get("financial_analysis") or {},
        "sales_memo":         result.get("sales_memo")         or {},
        "risk_memo":          result.get("risk_memo")          or {},
        "sales_rebuttal":     result.get("sales_rebuttal")     or {},
        "compliance_memo":    result.get("compliance_memo")    or {},
        "risk_score":         result.get("risk_score")         or {},
        "stress_test_results":result.get("stress_test_results")or {},
        "final_decision":     result.get("final_decision")     or {},
    }

    # Save next to the HTML file so the browser can fetch it
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "war_room_output.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\nUI data saved → {out_path}")
    print("Open war_room_ui.html in your browser (served via http-server or python -m http.server).")


if __name__ == "__main__":
    main()
