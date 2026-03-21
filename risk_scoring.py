import pandas as pd
import xgboost as xgb
import joblib
import os
import re
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.utils.class_weight import compute_sample_weight
from collections import Counter
from typing import Any, Dict, List

MODEL_PATH = "credit_risk_model.pkl"
DATA_PATH = "credit_risk_dataset.csv"

# ─────────────────────────────────────────────
# Feature configuration
# ─────────────────────────────────────────────

FEATURE_COLUMNS = [
    "person_age",
    "person_income",
    "person_emp_length",
    "loan_amnt",
    "loan_int_rate",
    "loan_percent_income",
    "cb_person_default_on_file",
    "cb_person_cred_hist_length",
]

# ── Grade mappings ───────────────────────────

GRADE_LABELS = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E", 5: "F", 6: "G"}

GRADE_DSCR = {
    0: "1.80",
    1: "1.60",
    2: "1.35",
    3: "1.20",
    4: "0.95",
    5: "0.75",
    6: "0.55",
}

GRADE_REV_GROWTH = {
    0: "20%",
    1: "12%",
    2: "6%",
    3: "2%",
    4: "-5%",
    5: "-12%",
    6: "-20%",
}

GRADE_DEBT_TREND = {
    0: "stable",
    1: "stable",
    2: "stable",
    3: "increasing",
    4: "increasing",
    5: "rising sharply",
    6: "rising sharply",
}

# ─────────────────────────────────────────────
# Train Model
# ─────────────────────────────────────────────

def train_model() -> xgb.XGBClassifier:

    df = pd.read_csv(DATA_PATH)
    df = df.dropna().copy()

    df["cb_person_default_on_file"] = df["cb_person_default_on_file"].map(
        {"Y": 1, "N": 0}
    )

    rank_map = {"A":0,"B":1,"C":2,"D":3,"E":4,"F":5,"G":6}

    y = df["loan_grade"].map(rank_map)

    X = df[FEATURE_COLUMNS]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.3, random_state=42
    )

    print("Class distribution:", Counter(y_train))

    sample_weights = compute_sample_weight(
        class_weight="balanced",
        y=y_train
    )

    model = xgb.XGBClassifier(
        n_estimators=900,
        max_depth=5,
        learning_rate=0.08,
        subsample=0.7,
        eval_metric="mlogloss",
        random_state=42
    )

    model.fit(
        X_train,
        y_train,
        sample_weight=sample_weights,
        eval_set=[(X_test, y_test)],
        verbose=False
    )

    print(classification_report(y_test, model.predict(X_test)))

    joblib.dump(model, MODEL_PATH)

    return model


# ─────────────────────────────────────────────
# Load Model
# ─────────────────────────────────────────────

def load_model():

    if os.path.exists(MODEL_PATH):
        return joblib.load(MODEL_PATH)

    print("Training XGBoost credit risk model...")
    return train_model()


_MODEL = load_model()


# ─────────────────────────────────────────────
# Utility helpers
# ─────────────────────────────────────────────

def _parse_number(s: str):

    if not s or str(s).strip().upper() == "N/A":
        return None

    s = str(s).strip().replace(",", "")
    s = re.sub(r"[%xX]$", "", s)

    match = re.search(r"[-+]?\d+\.?\d*", s)

    return float(match.group()) if match else None


def _dscr_score(dscr_val):

    if dscr_val is None:
        return 0

    if dscr_val > 1.5:
        return 20

    if dscr_val >= 1.25:
        return 10

    return -20


def _revenue_growth_positive(metrics):

    rg = str((metrics or {}).get("revenue_growth") or "").upper()

    if "N/A" in rg:
        return False

    val = _parse_number(rg)

    if val is not None and val > 0:
        return True

    return any(w in rg for w in ("INCREAS","GROWTH","UP","POSITIVE"))


def _debt_increasing_rapidly(metrics, risk_memo):

    debt_trend = str((metrics or {}).get("debt_trend") or "").upper()

    if any(w in debt_trend for w in ("INCREAS","RISING","UP","GROW")):
        return True

    risk_text = str(risk_memo or {}).upper()

    return "DEBT" in risk_text and ("INCREAS" in risk_text or "LEVERAGE" in risk_text)


# ─────────────────────────────────────────────
# Risk Score Calculation
# ─────────────────────────────────────────────

def calculate_risk_score(
    financial_analysis: Dict[str, Any],
    risk_memo: Dict[str, Any],
    compliance_memo: Dict[str, Any],
) -> Dict[str, Any]:

    drivers: List[str] = []

    metrics = (financial_analysis or {}).get("metrics") or {}

    # normalize categorical default flag
    cb_default = metrics.get("cb_person_default_on_file", 0)

    if isinstance(cb_default, str):
        cb_default = 1 if cb_default.upper() == "Y" else 0

    feature_dict = {
        "person_age": metrics.get("person_age", 30),
        "person_income": metrics.get("person_income", 50000),
        "person_emp_length": metrics.get("person_emp_length", 5),
        "loan_amnt": metrics.get("loan_amnt", 10000),
        "loan_int_rate": metrics.get("loan_int_rate", 10),
        "loan_percent_income": metrics.get("loan_percent_income", 0.2),
        "cb_person_default_on_file": cb_default,
        "cb_person_cred_hist_length": metrics.get(
            "cb_person_cred_hist_length", 5
        ),
    }

    features = pd.DataFrame([feature_dict])[FEATURE_COLUMNS]


    # ── ML Prediction ──

    predicted_grade = int(_MODEL.predict(features)[0])

    grade_label = GRADE_LABELS[predicted_grade]

    drivers.append(f"ML model predicted loan grade: {grade_label}")

    metrics.setdefault("dscr", GRADE_DSCR[predicted_grade])
    metrics.setdefault("revenue_growth", GRADE_REV_GROWTH[predicted_grade])
    metrics.setdefault("debt_trend", GRADE_DEBT_TREND[predicted_grade])

    blocking = (compliance_memo or {}).get("blocking_issues") or []

    if predicted_grade >= 5:
        blocking.append("Loan grade below acceptable threshold (F/G)")

    has_blocking = len(blocking) > 0

    score = 50

    if has_blocking:
        score -= 50
        drivers.append("Compliance blocking issues (-50)")

    dscr_val = _parse_number(metrics["dscr"])

    dscr_delta = _dscr_score(dscr_val)

    score += dscr_delta

    if dscr_val is not None:

        if dscr_delta == 20:
            drivers.append(f"DSCR {dscr_val} > 1.5 (+20)")

        elif dscr_delta == 10:
            drivers.append(f"DSCR {dscr_val} between 1.25-1.5 (+10)")

        else:
            drivers.append(f"DSCR {dscr_val} < 1.25 (-20)")

    if _revenue_growth_positive(metrics):

        score += 10
        drivers.append("Revenue growth positive (+10)")

    if _debt_increasing_rapidly(metrics, risk_memo):

        score -= 10
        drivers.append("Debt increasing (-10)")

    score = max(0, min(100, score))

    risk_level = (
        "LOW" if score >= 70
        else "MEDIUM" if score >= 40
        else "HIGH"
    )

    return {
        "risk_score": score,
        "risk_level": risk_level,
        "predicted_grade": grade_label,
        "key_drivers": drivers
    }


# ─────────────────────────────────────────────
# Example Run
# ─────────────────────────────────────────────

if __name__ == "__main__":

    result = calculate_risk_score(
        financial_analysis={
            "metrics": {
                "person_age": 35,
                "person_income": 60000,
                "person_emp_length": 7,
                "loan_amnt": 15000,
                "loan_int_rate": 12.5,
                "loan_percent_income": 0.25,
                "cb_person_default_on_file": "N",
                "cb_person_cred_hist_length": 8
            }
        },
        risk_memo={},
        compliance_memo={"blocking_issues":[]}
    )

    print(result)
