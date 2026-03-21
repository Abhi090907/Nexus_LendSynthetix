from src.query_engine import query_loan_documents


def main() -> None:
    # Simple smoke test to validate that retrieval works end-to-end.
    question = "What is the borrower's revenue and EBITDA trend over the last three years?"
    context = query_loan_documents(question)

    print("Question:")
    print(question)
    print("\nRetrieved context:\n")
    print(context)


if __name__ == "__main__":
    main()

