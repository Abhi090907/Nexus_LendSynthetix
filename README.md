# LendSynthetix

LendSynthetix is an AI-assisted credit appraisal platform combining:
- a Next.js dashboard frontend,
- a FastAPI backend,
- multi-agent War Room decision synthesis,
- explainability, stress testing, and tamper-evident signed report generation.

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

## Signed PDF / Tamper Evidence

Signed reports include:
- deterministic SHA-256 canonical hashing of report payload,
- HMAC-SHA256 server signature,
- embedded verification block,
- QR code encoding integrity metadata.

If report JSON is modified, hash/signature verification fails.

