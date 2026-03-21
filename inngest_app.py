"""
Minimal ASGI app to serve Inngest functions.
"""

from typing import Any

try:
    import inngest
    import inngest.fast_api
except ImportError:  # pragma: no cover
    inngest = None

from fastapi import FastAPI

try:
    from pipeline import ingest_loan_pdf_fn
except ImportError:
    ingest_loan_pdf_fn = None


def create_app() -> Any:
    if inngest is None:
        raise RuntimeError(
            "Inngest is not installed. Install it with `pip install inngest`"
        )
    if ingest_loan_pdf_fn is None:
        raise RuntimeError(
            "Inngest functions failed to load from pipeline.py."
        )

    # Create client here with dev key — no external key needed
    client = inngest.Inngest(
        app_id="lendsynthetix-loan-war-room",
        signing_key="signkey-dev-0000000000000000000000000000000000000000000000000000000000000000",
        is_production=False,
    )

    app = FastAPI()
    inngest.fast_api.serve(app, client, [ingest_loan_pdf_fn])

    return app


# ASGI entrypoint
app = create_app()