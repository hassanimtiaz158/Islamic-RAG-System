# scripts/evaluate_rag.py
"""
RAG Evaluation Framework for Al-Ilm Islamic Knowledge System.

Measures:
1. Faithfulness — Are claims supported by retrieved context?
2. Context Precision — Are retrieved docs relevant?
3. Context Recall — Are relevant docs retrieved?
4. Answer Relevance — Does the answer address the question?
5. Citation Correctness — Are citations valid and correctly formatted?
6. Hallucination Rate — % of unsupported claims

Usage:
    python scripts/evaluate_rag.py
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.core.islamic_vectorDB import IslamicVectorStore
from src.utils.citation_engine import extract_citations, verify_answer_grounding, check_islamic_safety


# ═══════════════════════════════════════════════
# EVALUATION TEST SET
# ═══════════════════════════════════════════════
@dataclass
class TestQuery:
    query: str
    expected_sources: List[str]       # e.g., ["quran", "hadith_bukhari"]
    expected_citation_patterns: List[str]  # regex patterns that should be in citations
    should_have_citations: bool = True
    description: str = ""


EVAL_QUERIES: List[TestQuery] = [
    TestQuery(
        query="What does Islam say about patience (Sabr)?",
        expected_sources=["quran", "hadith_bukhari"],
        expected_citation_patterns=[r"\[Quran", r"\[Bukhari"],
        description="Basic question on patience — should return Quran + Bukhari citations",
    ),
    TestQuery(
        query="What is the importance of honoring parents in Islam?",
        expected_sources=["quran"],
        expected_citation_patterns=[r"\[Quran", r"\[Quran\s+Al-Isra"],
        description="Parent honor — should cite Quran Al-Isra verses",
    ),
    TestQuery(
        query="Who receives Zakat according to the Quran?",
        expected_sources=["quran"],
        expected_citation_patterns=[r"\[Quran", r"\[Quran\s+At-Tawbah"],
        description="Zakat recipients — should cite At-Tawbah 9:60",
    ),
    TestQuery(
        query="What did the Prophet ﷺ say about charity?",
        expected_sources=["hadith_bukhari", "hadith_muslim"],
        expected_citation_patterns=[r"\[Bukhari|\[Muslim"],
        description="Charity hadith — should cite hadith collections",
    ),
    TestQuery(
        query="What are the five pillars of Islam?",
        expected_sources=["hadith_bukhari", "hadith_muslim"],
        expected_citation_patterns=[r"\[Bukhari|\[Muslim"],
        description="Five pillars — should cite hadith about pillars",
    ),
    TestQuery(
        query="What is the Islamic ruling on eating pork?",
        expected_sources=["quran"],
        expected_citation_patterns=[r"\[Quran"],
        description="Pork prohibition — should cite relevant Quranic verse",
    ),
]

# ═══════════════════════════════════════════════
# METRICS
# ═══════════════════════════════════════════════
@dataclass
class RetrievalMetrics:
    precision: float = 0.0      # relevant docs / total retrieved
    recall: float = 0.0         # relevant docs / total relevant (approximated)
    diversity: float = 0.0      # unique sources / total retrieved
    num_results: int = 0


@dataclass
class GenerationMetrics:
    citation_validity: float = 0.0   # % of citations correctly formatted
    citation_coverage: float = 0.0   # % of claims with citations
    faithfulness: float = 0.0        # grounding score
    safety_flags: List[str] = field(default_factory=list)


@dataclass
class EvaluationResult:
    query: str
    retrieval_metrics: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    generation_metrics: GenerationMetrics = field(default_factory=GenerationMetrics)
    latency_ms: float = 0.0
    error: str = ""
    has_generation: bool = False   # False in retrieval-only mode (no graph)


# ═══════════════════════════════════════════════
# EVALUATOR
# ═══════════════════════════════════════════════
class RAGEvaluator:
    """Evaluates the RAG pipeline against test queries."""

    def __init__(self, vector_store: IslamicVectorStore):
        self.vector_store = vector_store
        self.results: List[EvaluationResult] = []

    def evaluate_retrieval(
        self,
        query: str,
        expected_sources: List[str],
        top_k: int = 5,
    ) -> RetrievalMetrics:
        """Evaluate retrieval quality for a query."""
        metrics = RetrievalMetrics()

        all_retrieved = {}
        for col in expected_sources:
            try:
                results = self.vector_store.retrieve_with_scores(col, query=query, k=top_k)
                all_retrieved[col] = results
            except Exception:
                all_retrieved[col] = []

        total_docs = sum(len(docs) for docs in all_retrieved.values())
        metrics.num_results = total_docs

        # Collections that actually returned at least one document
        counts = {col: len(docs) for col, docs in all_retrieved.items() if docs}
        non_empty = len(counts)

        # Recall: fraction of expected sources that returned at least one doc
        metrics.recall = non_empty / max(len(expected_sources), 1)

        # Diversity: how spread the retrieved docs are across collections.
        # 1.0 = evenly distributed, 0.0 = everything came from a single collection.
        if total_docs == 0:
            metrics.diversity = 0.0
        else:
            max_share = max(counts.values()) / total_docs
            metrics.diversity = 1.0 - max_share

        # Precision: fraction of retrieved docs that are *highly* relevant.
        # (retrieve_with_scores already filters out docs below the 0.3 floor,
        # so a 0.3 cutoff would always be 1.0 — use a stricter 0.5 bar instead.)
        highly_relevant = sum(
            1 for docs in all_retrieved.values()
            for _, score in docs if score >= 0.5
        )
        metrics.precision = highly_relevant / max(total_docs, 1)

        return metrics

    def evaluate_generation(
        self,
        response: str,
        context: str,
        expected_patterns: List[str],
    ) -> GenerationMetrics:
        """Evaluate generation quality for a response."""
        metrics = GenerationMetrics()

        citations = extract_citations(response)

        # Citation validity: do citations match expected patterns?
        if expected_patterns:
            import re
            matched = sum(
                1 for pattern in expected_patterns
                if any(re.search(pattern, c["raw"]) for c in citations)
            )
            metrics.citation_validity = matched / len(expected_patterns)

        # Faithfulness: grounding check (confidence already reflects grounding,
        # so do not penalise a second time when not grounded)
        is_grounded, _, confidence = verify_answer_grounding(response, context, citations)
        metrics.faithfulness = confidence

        # Citation coverage: ratio of sentences with citations
        sentences = response.split(".")
        cited_sentences = sum(
            1 for s in sentences
            if any(c["raw"] in s for c in citations)
        )
        metrics.citation_coverage = cited_sentences / max(len(sentences), 1)

        # Safety flags
        metrics.safety_flags = check_islamic_safety(response, citations)

        return metrics

    def run_evaluation(self) -> Dict:
        """Run full evaluation on all test queries."""
        print("\n" + "=" * 70)
        print("🧪 AL-ILM RAG EVALUATION FRAMEWORK")
        print("=" * 70)

        eval_graph = None
        try:
            from src.agents.islamic_graph import build_islamic_graph
            eval_graph = build_islamic_graph(self.vector_store)
        except Exception as e:
            print(f"⚠ Could not load full graph: {e}")
            print("   Running retrieval-only evaluation...")

        for i, test in enumerate(EVAL_QUERIES, 1):
            print(f"\n[{i}/{len(EVAL_QUERIES)}] {test.description}")
            print(f"  Query: {test.query}")

            result = EvaluationResult(query=test.query)

            try:
                if eval_graph is not None:
                    # Full pipeline evaluation
                    start = time.time()
                    graph_result = eval_graph.invoke({
                        "query": test.query,
                        "language": "en",
                        "retrieved_docs": {},
                        "routing": test.expected_sources,
                        "iteration": 0,
                    })
                    result.latency_ms = (time.time() - start) * 1000

                    response = graph_result.get("response", "")
                    context = graph_result.get("context", "")

                    # Retrieval eval
                    retrieved_docs = graph_result.get("retrieved_docs", {})
                    sources_used = list(retrieved_docs.keys())
                    total_docs = sum(len(d) for d in retrieved_docs.values())
                    result.retrieval_metrics.num_results = total_docs
                    result.retrieval_metrics.diversity = len(sources_used) / max(len(test.expected_sources), 1)
                    result.retrieval_metrics.recall = len(sources_used) / max(len(test.expected_sources), 1)

                    # Generation eval
                    gen_metrics = self.evaluate_generation(
                        response, context, test.expected_citation_patterns
                    )
                    result.generation_metrics = gen_metrics
                    result.has_generation = True

                else:
                    # Retrieval-only eval
                    start = time.time()
                    result.retrieval_metrics = self.evaluate_retrieval(
                        test.query, test.expected_sources
                    )
                    result.latency_ms = (time.time() - start) * 1000

                # Check citation requirement
                if test.should_have_citations:
                    has_citations = result.generation_metrics.citation_coverage > 0
                    if not has_citations:
                        print("  ⚠ No citations found — possible hallucination")

                print(f"  ✓ Retrieval: {result.retrieval_metrics.num_results} docs, "
                      f"diversity={result.retrieval_metrics.diversity:.2f}")
                print(f"  ✓ Generation: faithfulness={result.generation_metrics.faithfulness:.2f}, "
                      f"citation_coverage={result.generation_metrics.citation_coverage:.2f}")
                print(f"  ✓ Latency: {result.latency_ms:.0f}ms")

            except Exception as e:
                result.error = str(e)
                print(f"  ✗ Error: {e}")

            self.results.append(result)

        return self.summarize()

    def summarize(self) -> Dict:
        """Summarize all evaluation results."""
        print("\n" + "=" * 70)
        print("📊 EVALUATION SUMMARY")
        print("=" * 70)

        n = len(self.results)
        if n == 0:
            print("No results to summarize.")
            return {}

        gen_results = [r for r in self.results if r.has_generation]

        avg_latency = sum(r.latency_ms for r in self.results) / n
        avg_diversity = sum(r.retrieval_metrics.diversity for r in self.results) / n
        avg_recall = sum(r.retrieval_metrics.recall for r in self.results) / n

        # Generation metrics are only meaningful when the graph actually ran.
        # In retrieval-only mode there is no answer to evaluate, so we must not
        # report a 100% hallucination rate based on default 0.0 faithfulness.
        if gen_results:
            avg_faithfulness = sum(r.generation_metrics.faithfulness for r in gen_results) / len(gen_results)
            avg_citation_coverage = sum(r.generation_metrics.citation_coverage for r in gen_results) / len(gen_results)
            hallucination_count = sum(
                1 for r in gen_results if r.generation_metrics.faithfulness < 0.5
            )
            hallucination_rate = hallucination_count / len(gen_results)
        else:
            avg_faithfulness = 0.0
            avg_citation_coverage = 0.0
            hallucination_rate = 0.0

        # Error rate
        error_count = sum(1 for r in self.results if r.error)
        error_rate = error_count / n

        summary = {
            "total_queries": n,
            "generation_evaluated": len(gen_results),
            "avg_latency_ms": round(avg_latency, 1),
            "avg_retrieval_diversity": round(avg_diversity, 3),
            "avg_retrieval_recall": round(avg_recall, 3),
            "avg_faithfulness": round(avg_faithfulness, 3),
            "avg_citation_coverage": round(avg_citation_coverage, 3),
            "hallucination_rate": round(hallucination_rate, 3),
            "error_rate": round(error_rate, 3),
        }

        print(f"  Total queries:        {n}")
        print(f"  Avg latency:          {avg_latency:.0f}ms")
        print(f"  Retrieval diversity:  {avg_diversity:.3f}")
        print(f"  Retrieval recall:     {avg_recall:.3f}")
        if gen_results:
            print(f"  Faithfulness:         {avg_faithfulness:.3f}")
            print(f"  Citation coverage:    {avg_citation_coverage:.3f}")
            print(f"  Hallucination rate:   {hallucination_rate:.1%}")
        else:
            print("  Faithfulness:         N/A (retrieval-only mode, no generation)")
            print("  Hallucination rate:   N/A (retrieval-only mode, no generation)")
        print(f"  Error rate:           {error_rate:.1%}")
        print("=" * 70)

        # Grade (only meaningful when generation was actually evaluated)
        if gen_results:
            grade = "A" if avg_faithfulness >= 0.8 and hallucination_rate < 0.1 else \
                    "B" if avg_faithfulness >= 0.6 and hallucination_rate < 0.2 else \
                    "C" if avg_faithfulness >= 0.4 and hallucination_rate < 0.3 else "D"
            print(f"\n  🏆 Overall Grade: {grade}")
            print(f"     (Faithfulness >= 0.8, Hallucination < 10% = A)")
        else:
            print("\n  🏆 Grade: N/A (run with a working LLM/graph for a full grade)")
        print("=" * 70)

        return summary


def main():
    """Run the evaluation."""
    try:
        vector_store = IslamicVectorStore()
    except Exception as e:
        print(f"❌ Could not initialize vector store: {e}")
        print("   Make sure data/vectorstore exists and is populated.")
        print("   Run: python scripts/index_all.py")
        return

    evaluator = RAGEvaluator(vector_store)
    summary = evaluator.run_evaluation()

    # Save results
    output_path = PROJECT_ROOT / "data" / "evaluation_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Results saved to: {output_path}")


if __name__ == "__main__":
    main()
