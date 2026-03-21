"""
LangGraph multi-agent debate: Loan War Room (credit committee simulation)

Flow

START
 → retrieve_context
 → financial_analysis_node
 → case_memory_node
 → sales_node
 → risk_node
 → sales_rebuttal_node
 → compliance_node
 → risk_scoring_node
 → stress_testing_node
 → (if compliance veto) → store_case_node → END
 → (else) → moderator_node
 → store_case_node
 → END
"""

from typing import List, Literal, Optional, TypedDict

from langgraph.graph import END, StateGraph

from query_engine import query_loan_documents
from risk_scoring import calculate_risk_score
from case_memory import retrieve_similar_cases, store_case_memory

from agents.financial_analyst import run_financial_analyst
from agents.sales_agent import run_sales_agent
from agents.risk_agent import run_risk_agent
from agents.sales_rebuttal import run_sales_rebuttal
from agents.compliance_agent import run_compliance_agent
from agents.moderator import run_moderator

from stress_testing import run_stress_tests


class WarRoomState(TypedDict, total=False):

    question: str
    context: str

    financial_analysis: dict
    past_cases: List[dict]

    sales_memo: dict
    risk_memo: dict
    sales_rebuttal: dict

    debate_round: int

    compliance_memo: dict
    compliance_blocks: bool

    risk_score: dict
    stress_test_results: dict

    final_decision: dict


# ------------------------------------------------
# Context Retrieval
# ------------------------------------------------

def retrieve_context(state: WarRoomState) -> dict:

    context = query_loan_documents(state["question"])

    return {"context": context}


# ------------------------------------------------
# Financial Analysis
# ------------------------------------------------

def financial_analysis_node(state: WarRoomState) -> dict:

    result = run_financial_analyst(
        question=state["question"],
        context=state["context"],
    )

    return {"financial_analysis": result.model_dump()}


# ------------------------------------------------
# Case Memory Retrieval
# ------------------------------------------------

def case_memory_node(state: WarRoomState) -> dict:

    cases = retrieve_similar_cases(
        state["question"],
        top_k=3
    )

    return {"past_cases": cases}


# ------------------------------------------------
# Sales Agent
# ------------------------------------------------

def sales_node(state: WarRoomState) -> dict:

    memo = run_sales_agent(
        question=state["question"],
        context=state["context"],
        previous_arguments="",
        financial_analysis=state.get("financial_analysis"),
        past_cases=state.get("past_cases"),
    )

    return {
        "sales_memo": memo.model_dump(),
        "debate_round": 0
    }


# ------------------------------------------------
# Risk Agent
# ------------------------------------------------

def risk_node(state: WarRoomState) -> dict:

    memo = run_risk_agent(
        question=state["question"],
        context=state["context"],
        previous_arguments=_format_memo(state.get("sales_memo")),
        financial_analysis=state.get("financial_analysis"),
        past_cases=state.get("past_cases"),
    )

    return {"risk_memo": memo.model_dump()}


# ------------------------------------------------
# Sales Rebuttal
# ------------------------------------------------

def sales_rebuttal_node(state: WarRoomState) -> dict:

    rebuttal = run_sales_rebuttal(
        question=state["question"],
        context=state["context"],
        financial_analysis=state.get("financial_analysis"),
        sales_memo_text=_format_memo(state.get("sales_memo")),
        risk_memo_text=_format_memo(state.get("risk_memo")),
    )

    return {"sales_rebuttal": rebuttal.model_dump()}


# ------------------------------------------------
# Compliance Review
# ------------------------------------------------

def compliance_node(state: WarRoomState) -> dict:

    memo = run_compliance_agent(
        question=state["question"],
        context=state["context"],
        previous_arguments=_format_memo(state.get("risk_memo")),
        financial_analysis=state.get("financial_analysis"),
    )

    blocking = len(memo.blocking_issues) > 0

    final_decision = None

    if blocking:
        final_decision = {
            "final_recommendation": "REJECT",
            "reasoning": "Compliance veto: " + "; ".join(memo.blocking_issues),
            "conditions": [],
        }

    return {
        "compliance_memo": memo.model_dump(),
        "compliance_blocks": blocking,
        "final_decision": final_decision,
    }


# ------------------------------------------------
# Risk Scoring
# ------------------------------------------------

def risk_scoring_node(state: WarRoomState) -> dict:

    score = calculate_risk_score(
        financial_analysis=state.get("financial_analysis") or {},
        risk_memo=state.get("risk_memo") or {},
        compliance_memo=state.get("compliance_memo") or {},
    )

    return {"risk_score": score}


# ------------------------------------------------
# Stress Testing Engine
# ------------------------------------------------

def stress_testing_node(state: WarRoomState) -> dict:

    stress_results = run_stress_tests(
        financial_metrics=state.get("financial_analysis"),  # ← renamed from financial_analysis
        risk_memo=state.get("risk_memo"),
        compliance_memo=state.get("compliance_memo"),
    )

    return {"stress_test_results": stress_results}


# ------------------------------------------------
# Moderator Decision
# ------------------------------------------------

def moderator_node(state: WarRoomState) -> dict:

    # Convert past_cases list to string for moderator
    past_cases = state.get("past_cases") or []
    past_cases_text = "\n".join(str(c) for c in past_cases) if past_cases else ""

    decision = run_moderator(
        question=state["question"],
        context=state["context"],
        sales_memo_text=_format_memo(state.get("sales_memo")),
        risk_memo_text=_format_memo(state.get("risk_memo")),
        compliance_memo_text=_format_memo(state.get("compliance_memo")),
        financial_analysis=state.get("financial_analysis"),
        sales_rebuttal_text=_format_memo(state.get("sales_rebuttal")),
        past_cases=past_cases_text,   # ← converted to string
        # removed: risk_score and stress_tests (not in signature)
    )

    return {
        "final_decision": {
            "final_recommendation": decision.final_recommendation,
            "reasoning": decision.reasoning,
            "conditions": decision.conditions or [],
        }
    }


# ------------------------------------------------
# Store Case Memory
# ------------------------------------------------

def store_case_node(state: WarRoomState) -> dict:

    store_case_memory(
        question=state["question"],
        financial_analysis=state.get("financial_analysis") or {},
        risk_score=state.get("risk_score") or {},
        final_decision=state.get("final_decision") or {},
    )

    return {}


# ------------------------------------------------
# Memo Formatter
# ------------------------------------------------

def _format_memo(memo: Optional[dict]) -> str:

    if not memo:
        return ""

    parts = []

    for k, v in memo.items():

        if isinstance(v, list):
            v = "; ".join(str(x) for x in v)

        parts.append(f"{k}: {v}")

    return "\n".join(parts)


# ------------------------------------------------
# Routing Logic
# ------------------------------------------------

def route_after_stress_tests(
    state: WarRoomState
) -> Literal["moderator_node", "store_case_node"]:

    if state.get("compliance_blocks"):
        return "store_case_node"

    return "moderator_node"


# ------------------------------------------------
# Graph Builder
# ------------------------------------------------

def build_war_room_graph():

    builder = StateGraph(WarRoomState)

    builder.add_node("retrieve_context", retrieve_context)
    builder.add_node("financial_analysis_node", financial_analysis_node)
    builder.add_node("case_memory_node", case_memory_node)

    builder.add_node("sales_node", sales_node)
    builder.add_node("risk_node", risk_node)
    builder.add_node("sales_rebuttal_node", sales_rebuttal_node)

    builder.add_node("compliance_node", compliance_node)

    builder.add_node("risk_scoring_node", risk_scoring_node)
    builder.add_node("stress_testing_node", stress_testing_node)

    builder.add_node("moderator_node", moderator_node)
    builder.add_node("store_case_node", store_case_node)

    builder.set_entry_point("retrieve_context")

    builder.add_edge("retrieve_context", "financial_analysis_node")
    builder.add_edge("financial_analysis_node", "case_memory_node")

    builder.add_edge("case_memory_node", "sales_node")
    builder.add_edge("sales_node", "risk_node")
    builder.add_edge("risk_node", "sales_rebuttal_node")

    builder.add_edge("sales_rebuttal_node", "compliance_node")

    builder.add_edge("compliance_node", "risk_scoring_node")
    builder.add_edge("risk_scoring_node", "stress_testing_node")

    builder.add_conditional_edges(
        "stress_testing_node",
        route_after_stress_tests,
        {
            "moderator_node": "moderator_node",
            "store_case_node": "store_case_node",
        },
    )

    builder.add_edge("moderator_node", "store_case_node")

    builder.add_edge("store_case_node", END)

    return builder.compile()


# ------------------------------------------------
# Runner
# ------------------------------------------------

def run_war_room(question: str) -> WarRoomState:

    graph = build_war_room_graph()

    initial_state: WarRoomState = {
        "question": question,
        "debate_round": 0,
    }

    return graph.invoke(initial_state)



