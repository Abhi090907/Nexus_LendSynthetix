# LendSynthetix — AI-Powered Loan War Room

LendSynthetix is a decision intelligence platform for credit risk assessment that combines machine learning, explainable AI, and multi-agent reasoning to support financial institutions in making faster, more transparent, and data-driven lending decisions.

The platform integrates document ingestion, predictive risk scoring, explainability, stress testing, and tamper-evident reporting into a unified “Loan War Room” interface.

---

## Overview

LendSynthetix addresses key challenges in modern lending:

- Slow and manual loan processing workflows  
- Lack of transparency in AI-driven decisions  
- Fragmented data sources and poor institutional memory  
- Limited ability to simulate risk under changing conditions  

The system enables real-time loan analysis, explanation, and scenario testing, while preserving auditability through signed reports.

---

## Core Capabilities

### Document Intelligence
- Upload and process loan-related PDFs  
- Extract, chunk, and embed content into a vector database  
- Enable semantic retrieval and institutional memory  

### Credit Risk Analysis
- Machine learning-based risk scoring using structured applicant data  
- Instant loan approval or rejection predictions  

### Explainability
- SHAP-based feature attribution for model decisions  
- Clear identification of factors increasing or reducing risk  

### Multi-Agent Loan War Room
- Coordinated decision-making using multiple agents:
  - Risk analysis  
  - Sales optimization  
  - Compliance validation  
  - Market intelligence  
  - Sentiment analysis  

### Stress Testing
- Simulate adverse financial scenarios:
  - Income reduction  
  - Interest rate changes  
  - Economic downturns  
- Evaluate impact on loan risk in real time  

### Market Intelligence
- Integrates external signals such as:
  - Stock market trends  
  - Macroeconomic indicators  
  - Geopolitical factors  

### Conversational Interface
- Voice and text-based interaction using speech recognition and LLMs  
- Enables natural querying of loan decisions  

### Tamper-Evident Reporting
- Generates signed PDF reports with:
  - SHA-256 hashing  
  - HMAC-based signatures  
  - Embedded verification metadata  
- Ensures integrity and auditability of decisions  

---

## Project Structure

```text
.
|-- app/                          # Next.js app router pages
|-- components/                   # React UI components
|-- public/dashboard/             # Dashboard static assets + JS modules
|-- src/                          # Python backend + ML + graph pipeline
|   |-- api.py                    # FastAPI entrypoint (port 8000)
|   |-- war_room_graph.py         # Multi-agent flow orchestration
|   |-- report_signing.py         # Hash + HMAC signing
|   |-- report_generator.py       # Signed PDF generation
|   `-- requirements.txt          # Python dependencies
|-- package.json                  # Frontend dependencies/scripts
`-- .gitignore
```

## Prerequisites

- Node.js 18+ and npm
- Python 3.10+ (recommended)
- Qdrant (local or remote)

## Local Setup

### 1) Frontend

```bash
npm install
npm run dev
```

Frontend runs at `http://localhost:3000`.

### 2) Backend

From the `src` directory:

```bash
python -m venv venv
# Windows PowerShell:
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python api.py
```

Backend runs at `http://localhost:8000`.

## Environment Variables

Create `src/.env` (or update it) with at least:

```env
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=loan_documents
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.1
LLM_API_KEY=

# Generate securely:
# python -c "import secrets; print(secrets.token_hex(32))"
REPORT_SIGNING_KEY=replace_with_64_hex_chars
```

## Key Backend Endpoints

- `POST /upload-pdf` - ingest PDFs into vector store
- `POST /explain-loan` - risk score + explainability
- `POST /run-war-room` - execute multi-agent credit committee
- `GET /download-report?collection=<name>` - download signed PDF report

---

## API Endpoints
- POST /upload-pdf
  Ingest and index loan-related documents into the vector database
- POST /explain-loan
  Generate risk score and explainability output
- POST /run-war-room
  Execute multi-agent decision workflow
- GET /download-report?collection=<name>
  Download signed PDF report

---
  
## Security and Integrity
Generated reports include:

- Deterministic SHA-256 hashing of report data
- HMAC-SHA256 digital signatures
- Embedded verification blocks
- QR code with integrity metadata

Any modification to the report invalidates the signature, ensuring trust and auditability.

---

## Use Cases
- Banking and NBFC loan underwriting
- Credit risk assessment platforms
- Regulatory compliance and audit workflows
- Financial decision support systems
- Future Enhancements
- Automated company and ticker extraction from documents
- Real-time financial data integration
- Advanced fraud detection using cross-document similarity
- Enhanced scenario simulation and forecasting

--- 

## License

This project is intended for educational and experimental purposes. Licensing can be adapted based on deployment requirements.

---

