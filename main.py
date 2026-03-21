import argparse
import logging
from pathlib import Path

from pipeline import ingest_pdf_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest a commercial loan PDF into Qdrant."
    )
    parser.add_argument(
        "--pdf",
        required=True,
        type=str,
        help="Path to the PDF to ingest (e.g., ./data/loan_grade_a_vertex_technologies.pdf).",
    )
    parser.add_argument(
        "--collection",
        required=False,
        type=str,
        help="Optional Qdrant collection name (overrides env).",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    args = parse_args()
    pdf_path = Path(args.pdf)

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at: {pdf_path}")

    ingest_pdf_pipeline(pdf_path=pdf_path, collection_name=args.collection)


if __name__ == "__main__":
    main()