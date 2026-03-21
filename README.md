# lendsynthetix
AI-powered multi-agent credit underwriting engine — LangGraph debate pipeline with RAG, XGBoost risk scoring, and compliance veto for commercial loan evaluation.
# LendSynthetix — The Loan War Room

> AI-powered multi-agent credit underwriting engine — reduces commercial loan 
> approval time from weeks to minutes with a full audit trail.

Built for the **Engineering Hackathon Double Challenge 2026**  
Track: **Agentic Workflows & Automated Underwriting (BFSI)**

---

## What It Does

Commercial lending is bottlenecked by three teams with conflicting priorities:

| Team | Goal |
|---|---|
| Sales | Close the deal |
| Risk/Underwriting | Protect the bank's capital |
| Compliance | Ensure zero regulatory violations |

LendSynthetix creates a **Digital War Room** where AI agents simulate each role, 
debate the loan from opposing perspectives, and autonomously arrive at a structured 
credit decision — with a full JSON audit trail.

---

##  Pipeline Overview
```
PDF Upload → LlamaIndex Ingestion → Qdrant Vector DB
    ↓
RAG Context Retrieval (top-5 chunks)
    ↓
Financial Analyst Agent (DSCR, EBITDA, D/EBITDA)
    ↓
Sales Agent → Risk Agent → Sales Rebuttal Agent
    ↓
Compliance Agent (KYC / AML / VETO POWER)
    ↓
XGBoost Risk Scoring + Stress Testing
    ↓
Moderator Agent → APPROVE / REJECT / CONDITIONAL
    ↓
war_room_output.json → Dashboard UI
```

---

## The 6 Agents

| Agent | Role | Mandate |
|---|---|---|
| Financial Analyst | Extracts metrics from PDF | DSCR, EBITDA margin, revenue growth, debt trend |
| Relationship Manager | Sales Agent | Argues for approval with PDF-grounded evidence |
| Credit Underwriter | Risk Agent | Flags leverage, DSCR, cash flow volatility |
| Sales Rebuttal | Counter-argument | Point-by-point rebuttal of Risk objections |
| Compliance Officer | Auditor | KYC, AML, sanctions — has **VETO power** |
| Moderator | Committee Chair | Synthesizes all memos into final verdict |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Agent Orchestration | LangGraph |
| LLM Inference | Groq API (LLaMA 3.1 8B Instant) |
| RAG Pipeline | LlamaIndex Core |
| Vector Database | Qdrant (local file storage) |
| Embeddings | BAAI/bge-small-en-v1.5 (HuggingFace, local) |
| PDF Extraction | pdfplumber |
| Risk Scoring | XGBoost + Scikit-learn |
| Backend | Python + Flask |
| Frontend | HTML + Tailwind CSS + Vanilla JS |
| Config | Pydantic v2 + python-dotenv |

---

## Getting Started

### Prerequisites
- Python 3.11
- A free [Groq API key](https://console.groq.com)

### Setup
```bash
# 1. Clone the repo
git clone https://github.com/yourusername/LendSynthetix.git
cd LendSynthetix/src

# 2. Create virtual environment
py -3.11 -m venv venv

# Windows
venv\Scripts\activate

# Linux / Mac
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Groq API key to .env
# Open .env and set: LLM_API_KEY=your_groq_key_here
```

### Ingest a Loan PDF
```bash
python main.py --pdf loan_grade_a_vertex_technologies.pdf --collection loan_grade_a
python main.py --pdf loan_grade_b_crestline_retail.pdf --collection loan_grade_b
```

### Run the War Room
```bash
python war_room_test.py --collection loan_grade_a
# or
python war_room_test.py --collection loan_grade_b
```

### View the Dashboard
```bash
python -m http.server 8000
# Open: http://localhost:8000/war_room_ui.html
```

---

## Project Structure
```
src/
├── main.py                  # PDF ingestion entry point
├── war_room_test.py         # War room pipeline runner
├── war_room_graph.py        # LangGraph pipeline (10 nodes)
├── war_room_ui.html         # Frontend dashboard
├── war_room_output.json     # Pipeline output (auto-generated)
├── .env                     # Environment variables
├── requirements.txt         # Dependencies
├── credit_risk_model.pkl    # Pre-trained XGBoost model
├── agents/
│   ├── financial_analyst.py
│   ├── sales_agent.py
│   ├── risk_agent.py
│   ├── sales_rebuttal.py
│   ├── compliance_agent.py
│   └── moderator.py
├── pipeline.py
├── parser.py
├── chunker.py
├── embedder.py
├── qdrant_store.py
├── query_engine.py
├── risk_scoring.py
├── stress_testing.py
└── case_memory.py
```

---

## Sample Output
```json
{
  "final_decision": {
    "final_recommendation": "CONDITIONAL_APPROVAL",
    "reasoning": "DSCR of 1.52x is adequate but leaves thin headroom...",
    "conditions": [
      "Personal guarantees from promoters required",
      "Debt-to-EBITDA covenant must not exceed 3.8x",
      "Quarterly financial reporting to the bank"
    ]
  },
  "risk_score": {
    "risk_score": 72,
    "risk_level": "MODERATE",
    "predicted_grade": "B"
  }
}
```

---

## Key Features

- **Adversarial multi-agent debate** — agents argue against each other, not alongside
- **Sales Rebuttal agent** — unique point-by-point counter to every Risk objection
- **Compliance VETO power** — cannot approve non-compliant deals regardless of consensus
- **Case memory** — learns from past decisions via Qdrant semantic retrieval
- **Stress testing** — Revenue shock, rate shock, and recession scenario via XGBoost
- **Per-collection isolation** — each PDF gets its own Qdrant collection, zero data bleed
- **100% local** — Qdrant runs on disk, embeddings run locally, no paid cloud DB

---

## Common Errors

| Error | Fix |
|---|---|
| `ModuleNotFoundError: xgboost` | `pip install xgboost` |
| `ModuleNotFoundError: llama_index.embeddings.fastembed` | `pip install llama-index-embeddings-fastembed` |
| `'docker' is not recognized` | Docker is NOT needed — Qdrant runs locally via `./qdrant_db` |
| `war_room_output.json not found` | Run `war_room_test.py` first before opening the dashboard |
| Groq 429 rate limit | Wait 30-60 seconds — pipeline has automatic retry built in |

---

## License

MIT License — see LICENSE file for details.

---

*Engineering Hackathon Double Challenge 2026 | Project 2 | BFSI — Agentic Workflows & Automated Underwriting*
