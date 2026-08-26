"""Command-line entry point.

    uv run python -m heat_rag ingest          # build the vector index (run once)
    uv run python -m heat_rag ask "..."       # retrieve raw passages + citations
    uv run python -m heat_rag answer "..."    # grounded, cite-only synthesized answer
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="heat_rag", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ingest", help="Extract, chunk, embed and index the textbook.")

    ask = sub.add_parser("ask", help="Retrieve textbook passages for a question.")
    ask.add_argument("question", help="What to look up, e.g. 'fin heat transfer'.")
    ask.add_argument("-k", type=int, default=5, help="Number of passages (default 5).")

    answer_p = sub.add_parser(
        "answer", help="Compose a grounded, cite-only answer from retrieved passages."
    )
    answer_p.add_argument("question", help="The question to answer from the book.")
    answer_p.add_argument("-k", type=int, default=6, help="Passages to ground on (default 6).")

    args = parser.parse_args(argv)

    if args.command == "ingest":
        from .ingest import ingest

        ingest()
        return 0

    if args.command == "ask":
        from .search import format_hits, search

        hits = search(args.question, k=args.k)
        print(format_hits(args.question, hits))
        return 0

    if args.command == "answer":
        from .answer import answer, format_answer

        text, hits = answer(args.question, k=args.k)
        print(format_answer(text, hits))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
