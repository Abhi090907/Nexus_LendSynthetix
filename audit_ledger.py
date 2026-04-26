import sqlite3


def init_ledger(db_path: str = "audit_ledger.db"):
    """Create audit_log table if not exists."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS audit_log (
                case_id TEXT PRIMARY KEY,
                borrower_name TEXT,
                timestamp_utc TEXT,
                verdict TEXT,
                risk_score REAL,
                json_hash TEXT,
                pdf_hash TEXT,
                pdf_path TEXT,
                json_path TEXT
            )
            """
        )
        conn.commit()


def record_case(db_path: str, report_meta: dict):
    """Insert one row per completed war room run."""
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO audit_log (
                case_id,
                borrower_name,
                timestamp_utc,
                verdict,
                risk_score,
                json_hash,
                pdf_hash,
                pdf_path,
                json_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_meta.get("case_id"),
                report_meta.get("borrower_name"),
                report_meta.get("timestamp_utc"),
                report_meta.get("verdict"),
                report_meta.get("risk_score"),
                report_meta.get("json_hash"),
                report_meta.get("pdf_hash"),
                report_meta.get("pdf_path"),
                report_meta.get("json_path"),
            ),
        )
        conn.commit()


def verify_document(db_path: str, case_id: str, current_json_hash: str) -> dict:
    """
    Look up case_id in ledger. Compare stored hash vs current hash.
    Returns: {
        "verified": bool,
        "stored_hash": str,
        "current_hash": str,
        "match": bool,
        "verdict_at_generation": str,
        "timestamp": str,
    }
    """
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT json_hash, verdict, timestamp_utc
            FROM audit_log
            WHERE case_id = ?
            """,
            (case_id,),
        ).fetchone()

    if row is None:
        return {
            "verified": False,
            "stored_hash": "",
            "current_hash": current_json_hash,
            "match": False,
            "verdict_at_generation": "",
            "timestamp": "",
        }

    stored_hash, verdict, timestamp = row
    match = stored_hash == current_json_hash
    return {
        "verified": True,
        "stored_hash": stored_hash,
        "current_hash": current_json_hash,
        "match": match,
        "verdict_at_generation": verdict,
        "timestamp": timestamp,
    }
