"""Measures Footnote's answer quality on a fixed set of questions with known answers.

Run from the backend folder:
    uv run python -m eval.run_eval                   # full run (retrieval + answers)
    uv run python -m eval.run_eval --retrieval-only  # retrieval only: fast, no LLM calls

What it measures:
  Retrieval  hit rate: was a passage containing the evidence among the top-k results?
             MRR: how high was it ranked? (1.0 = always first, 0.5 = usually second...)
  Answers    correct: answerable questions whose answer contains every expected fact
             cited: correct answers that cite at least one source
             invalid citations: citations of a source number that wasn't provided
  Refusals   correct: unanswerable questions answered with "I couldn't find this..."
             false refusals: answerable questions the system wrongly refused

It runs against the real database, as a temporary user, and removes everything after.
"""

import argparse
import json
import re
import statistics
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.answering import NOT_FOUND, SYSTEM_PROMPT, build_prompt
from app.config import settings
from app.db import SessionLocal
from app.ingestion import ingest
from app.llm import get_llm
from app.models import User
from app.retrieval import RetrievedChunk, retrieve

EVAL_DIR = Path(__file__).parent
CORPUS_DIR = EVAL_DIR / "corpus"
RESULTS_DIR = EVAL_DIR / "results"
CITATION = re.compile(r"\[(\d+)\]")


@dataclass
class QuestionResult:
    id: str
    question: str
    answerable: bool
    top_score: float
    retrieval_rank: int | None = None   # 1-based rank of the first evidence passage
    answer: str | None = None
    correct: bool | None = None
    refused: bool | None = None
    cited: bool | None = None
    invalid_citations: list[int] = field(default_factory=list)
    seconds: float = 0.0


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def evidence_rank(chunks: list[RetrievedChunk], item: dict) -> int | None:
    """1-based rank of the first retrieved passage from the right document containing the evidence."""
    evidence = normalize(item["evidence"])
    for rank, chunk in enumerate(chunks, start=1):
        if chunk.filename == item["expected_document"] and evidence in normalize(chunk.content):
            return rank
    return None


def contains_fact(answer: str, fact: str | list[str]) -> bool:
    """A fact is one phrase, or a list of acceptable phrasings (any one counts)."""
    phrasings = [fact] if isinstance(fact, str) else fact
    return any(phrasing.lower() in answer.lower() for phrasing in phrasings)


def generate_answer(question: str, relevant: list[RetrievedChunk]) -> str:
    if not relevant:
        return NOT_FOUND
    return "".join(get_llm().stream(SYSTEM_PROMPT, build_prompt(question, relevant)))


def score_answer(result: QuestionResult, item: dict, answer: str, source_count: int) -> None:
    result.answer = answer
    result.refused = "couldn't find this" in answer.lower()
    numbers = [int(n) for n in CITATION.findall(answer)]
    result.invalid_citations = [n for n in numbers if n < 1 or n > source_count]
    result.cited = bool(numbers) and not result.invalid_citations
    if item["answerable"]:
        result.correct = not result.refused and all(contains_fact(answer, fact) for fact in item["must_include"])
    else:
        result.correct = result.refused


def suggest_threshold(results: list[QuestionResult]) -> tuple[float, int]:
    """The relevance threshold that best separates answerable from unanswerable questions."""
    scores = sorted({round(r.top_score, 3) for r in results})
    best = (settings.min_relevance, -1)
    for threshold in scores:
        separated = sum(
            (r.top_score >= threshold) == r.answerable for r in results
        )
        if separated > best[1]:
            best = (threshold, separated)
    return best


def percent(part: int, whole: int) -> str:
    return f"{part}/{whole} ({part / whole:.0%})" if whole else "n/a"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--retrieval-only", action="store_true", help="skip answer generation (no LLM calls)")
    parser.add_argument("--top-k", type=int, default=settings.answer_top_k)
    parser.add_argument("--min-relevance", type=float, default=settings.min_relevance)
    args = parser.parse_args()

    dataset = json.loads((EVAL_DIR / "dataset.json").read_text())
    session = SessionLocal()
    user = User(email=f"eval-{uuid.uuid4()}@footnote.local", password_hash="!")  # "!" can never match a password
    session.add(user)
    session.commit()

    try:
        print(f"Ingesting {len(list(CORPUS_DIR.glob('*.md')))} documents...")
        for path in sorted(CORPUS_DIR.glob("*.md")):
            ingest(session, user.id, path.name, "text/markdown", path.read_bytes(), "text")

        results: list[QuestionResult] = []
        for item in dataset:
            started = time.perf_counter()
            chunks = retrieve(session, item["question"], args.top_k, user.id)
            relevant = [c for c in chunks if c.score >= args.min_relevance]
            result = QuestionResult(
                id=item["id"],
                question=item["question"],
                answerable=item["answerable"],
                top_score=chunks[0].score if chunks else 0.0,
            )
            if item["answerable"]:
                result.retrieval_rank = evidence_rank(chunks, item)
            if not args.retrieval_only:
                score_answer(result, item, generate_answer(item["question"], relevant), len(relevant))
            result.seconds = round(time.perf_counter() - started, 2)
            results.append(result)
            print(f"  {item['id']:<20} {'ok' if result.correct in (True, None) else 'MISS'}")
    finally:
        session.delete(user)  # cascades to the eval documents and chunks
        session.commit()
        session.close()

    report = build_report(results, args)
    print("\n" + report)

    RESULTS_DIR.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    (RESULTS_DIR / f"{stamp}.json").write_text(json.dumps([asdict(r) for r in results], indent=2))
    (RESULTS_DIR / "latest.md").write_text(report + "\n")
    print(f"\nSaved eval/results/{stamp}.json and eval/results/latest.md")


def build_report(results: list[QuestionResult], args: argparse.Namespace) -> str:
    answerable = [r for r in results if r.answerable]
    unanswerable = [r for r in results if not r.answerable]
    hits = [r for r in answerable if r.retrieval_rank is not None]
    mrr = sum(1 / r.retrieval_rank for r in hits) / len(answerable) if answerable else 0.0

    model = "retrieval only" if args.retrieval_only else f"{settings.llm_provider} / {settings.llm_model or 'default model'}"
    lines = [
        "# Footnote evaluation",
        "",
        f"{len(answerable)} answerable and {len(unanswerable)} unanswerable questions. "
        f"Model: {model}. top_k={args.top_k}, min_relevance={args.min_relevance}.",
        "",
        "| Metric | Result |",
        "|---|---|",
        f"| Retrieval hit rate (evidence in top {args.top_k}) | {percent(len(hits), len(answerable))} |",
        f"| Retrieval MRR | {mrr:.2f} |",
    ]

    if not args.retrieval_only:
        correct = [r for r in answerable if r.correct]
        cited = [r for r in correct if r.cited]
        false_refusals = [r for r in answerable if r.refused]
        correct_refusals = [r for r in unanswerable if r.correct]
        invalid = sum(len(r.invalid_citations) for r in results)
        latency = statistics.median(r.seconds for r in results)
        lines += [
            f"| Correct answers | {percent(len(correct), len(answerable))} |",
            f"| Correct answers with valid citations | {percent(len(cited), len(correct))} |",
            f"| Correct refusals (unanswerable) | {percent(len(correct_refusals), len(unanswerable))} |",
            f"| False refusals (answerable) | {percent(len(false_refusals), len(answerable))} |",
            f"| Invalid citations | {invalid} |",
            f"| Median seconds per question | {latency:.1f} |",
        ]

    answerable_scores = [r.top_score for r in answerable]
    unanswerable_scores = [r.top_score for r in unanswerable]
    threshold, separated = suggest_threshold(results)
    lines += [
        "",
        "Top-1 relevance scores: "
        f"answerable min {min(answerable_scores):.3f} / median {statistics.median(answerable_scores):.3f}; "
        f"unanswerable max {max(unanswerable_scores):.3f} / median {statistics.median(unanswerable_scores):.3f}.",
        f"Best separating threshold: {threshold:.3f} ({separated}/{len(results)} questions on the right side).",
    ]

    misses = [r for r in results if r.correct is False or (r.answerable and r.retrieval_rank is None)]
    if misses:
        lines += ["", "Misses:"]
        for r in misses:
            reason = "retrieval missed the evidence" if r.answerable and r.retrieval_rank is None else (
                "wrongly refused" if r.refused else "missing expected facts" if r.answerable else "answered instead of refusing"
            )
            lines.append(f"- {r.id}: {reason}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()