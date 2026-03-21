from typing import Dict, Any
import copy
import re

from risk_scoring import calculate_risk_score


def _parse_percent(value):
    """
    Converts strings like '12%' or '-5%' to float.
    """
    if value is None:
        return None

    value = str(value)

    match = re.search(r"-?\d+\.?\d*", value)
    if not match:
        return None

    return float(match.group())


def apply_stress_scenario(metrics: Dict[str, Any], scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply a stress scenario to borrower metrics.
    """

    stressed = copy.deepcopy(metrics)

    # Revenue shock
    if "revenue_growth_delta" in scenario:

        current = _parse_percent(stressed.get("revenue_growth", "0%")) or 0

        new_val = current + scenario["revenue_growth_delta"]

        stressed["revenue_growth"] = f"{new_val}%"

    # Interest rate shock
    if "interest_rate_delta" in scenario:

        rate = stressed.get("loan_int_rate")

        if rate is not None:
            stressed["loan_int_rate"] = rate + scenario["interest_rate_delta"]

    # Income shock
    if "income_multiplier" in scenario:

        income = stressed.get("person_income")

        if income is not None:
            stressed["person_income"] = income * scenario["income_multiplier"]

    return stressed


def run_stress_tests(
    financial_metrics: Dict[str, Any],
    risk_memo: Dict[str, Any],
    compliance_memo: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Runs multiple stress scenarios and recomputes risk scores.
    """

    scenarios = {
        "Base Case": {},

        "Revenue -20%": {
            "revenue_growth_delta": -20
        },

        "Revenue -40%": {
            "revenue_growth_delta": -40
        },

        "Interest Rate +3%": {
            "interest_rate_delta": 3
        },

        "Income -30%": {
            "income_multiplier": 0.7
        },

        "Recession Scenario": {
            "revenue_growth_delta": -30,
            "interest_rate_delta": 2,
            "income_multiplier": 0.8
        }
    }

    results = {}

    for name, scenario in scenarios.items():

        stressed_metrics = apply_stress_scenario(financial_metrics, scenario)

        result = calculate_risk_score(
            {"metrics": stressed_metrics},
            risk_memo,
            compliance_memo
        )

        results[name] = result

    return results