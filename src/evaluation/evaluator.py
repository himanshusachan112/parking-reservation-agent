"""
RAG Evaluation Module - Performance and Accuracy Measurement.

This module evaluates the RAG system on two dimensions:

1. PERFORMANCE (Speed):
   - Request latency: How long does it take to get a response?
   - Retrieval time: How long does vector search take?
   - End-to-end time: Total time from question to answer

2. ACCURACY (Quality):
   - Recall@K: Of all relevant documents, what fraction did we retrieve?
     Formula: Recall@K = |relevant ∩ retrieved| / |relevant|
   - Precision@K: Of all retrieved documents, what fraction are relevant?
     Formula: Precision@K = |relevant ∩ retrieved| / |retrieved|
   - Answer relevance: Does the generated answer match the expected answer?

HOW EVALUATION WORKS:
1. We have a set of test questions with known answers (ground truth)
2. For each question, we:
   a. Run the RAG pipeline and measure time
   b. Check which documents were retrieved
   c. Compare retrieved docs to expected relevant docs
   d. Compare generated answer to expected answer
3. Aggregate metrics across all test questions

WHY THIS MATTERS:
- Proves the system works (not just a demo)
- Identifies weak spots (e.g., poor retrieval for certain topics)
- Guides improvements (e.g., need better chunking, more data)
"""

import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from src.database.vector_store import VectorStore
from src.database.sql_store import SQLStore
from src.chatbot.rag_chain import RAGChain
from src.data.load_data import get_sample_questions, get_ground_truth_answers


@dataclass
class EvaluationResult:
    """Holds the results of a single evaluation query."""
    question: str
    expected_answer: str
    generated_answer: str
    retrieved_docs: List[str]
    retrieval_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    precision_at_k: float
    recall_at_k: float
    answer_relevance_score: float


@dataclass
class EvaluationReport:
    """Aggregated evaluation results across all test queries."""
    total_questions: int = 0
    avg_retrieval_time_ms: float = 0.0
    avg_generation_time_ms: float = 0.0
    avg_total_time_ms: float = 0.0
    avg_precision_at_k: float = 0.0
    avg_recall_at_k: float = 0.0
    avg_answer_relevance: float = 0.0
    individual_results: List[EvaluationResult] = field(default_factory=list)

    def summary(self) -> str:
        """Generate a human-readable evaluation report."""
        return (
            "=" * 60 + "\n"
            "       RAG SYSTEM EVALUATION REPORT\n"
            "=" * 60 + "\n"
            f"\nTotal questions evaluated: {self.total_questions}\n"
            f"\n--- PERFORMANCE METRICS ---\n"
            f"  Average retrieval time:  {self.avg_retrieval_time_ms:.2f} ms\n"
            f"  Average generation time: {self.avg_generation_time_ms:.2f} ms\n"
            f"  Average total latency:   {self.avg_total_time_ms:.2f} ms\n"
            f"\n--- ACCURACY METRICS ---\n"
            f"  Average Precision@K:     {self.avg_precision_at_k:.4f}\n"
            f"  Average Recall@K:        {self.avg_recall_at_k:.4f}\n"
            f"  Average Answer Relevance: {self.avg_answer_relevance:.4f}\n"
            "=" * 60
        )


class RAGEvaluator:
    """
    Evaluates the RAG system's performance and accuracy.
    
    Usage:
        evaluator = RAGEvaluator(rag_chain)
        report = evaluator.run_evaluation()
        print(report.summary())
    """

    def __init__(self, rag_chain: RAGChain = None):
        """
        Initialize the evaluator.
        
        Args:
            rag_chain: The RAG chain to evaluate. If None, creates a new one.
        """
        self.rag_chain = rag_chain

    def run_evaluation(
        self,
        questions: List[str] = None,
        ground_truth: List[str] = None,
        k: int = 5
    ) -> EvaluationReport:
        """
        Run the full evaluation suite.
        
        Args:
            questions: List of test questions (defaults to sample questions)
            ground_truth: Expected answers (defaults to sample ground truth)
            k: Number of documents to retrieve for K-based metrics
            
        Returns:
            EvaluationReport with all metrics
        """
        if questions is None:
            questions = get_sample_questions()
        if ground_truth is None:
            ground_truth = get_ground_truth_answers()

        assert len(questions) == len(ground_truth), \
            "Number of questions must match number of ground truth answers"

        results = []

        for question, expected in zip(questions, ground_truth):
            result = self._evaluate_single_query(question, expected, k)
            results.append(result)

        # Aggregate results
        report = self._aggregate_results(results)
        return report

    def _evaluate_single_query(
        self,
        question: str,
        expected_answer: str,
        k: int
    ) -> EvaluationResult:
        """
        Evaluate a single question.
        
        Steps:
        1. Measure retrieval time
        2. Measure generation time
        3. Calculate precision and recall
        4. Score answer relevance
        """
        # Step 1: Measure retrieval time
        start_time = time.time()
        retrieved_docs = self.rag_chain.get_relevant_documents(question)
        retrieval_time = (time.time() - start_time) * 1000  # Convert to ms

        # Step 2: Measure generation time
        start_time = time.time()
        generated_answer = self.rag_chain.ask(question)
        generation_time = (time.time() - start_time) * 1000

        total_time = retrieval_time + generation_time

        # Get document texts for analysis
        doc_texts = [doc.page_content for doc in retrieved_docs]

        # Step 3: Calculate Precision@K and Recall@K
        precision, recall = self._calculate_retrieval_metrics(
            doc_texts, expected_answer, k
        )

        # Step 4: Calculate answer relevance
        relevance_score = self._calculate_answer_relevance(
            generated_answer, expected_answer
        )

        # Clear chat history between evaluations
        self.rag_chain.clear_history()

        return EvaluationResult(
            question=question,
            expected_answer=expected_answer,
            generated_answer=generated_answer,
            retrieved_docs=doc_texts,
            retrieval_time_ms=retrieval_time,
            generation_time_ms=generation_time,
            total_time_ms=total_time,
            precision_at_k=precision,
            recall_at_k=recall,
            answer_relevance_score=relevance_score,
        )

    def _calculate_retrieval_metrics(
        self,
        retrieved_texts: List[str],
        expected_answer: str,
        k: int
    ) -> tuple:
        """
        Calculate Precision@K and Recall@K.
        
        A retrieved document is "relevant" if it contains keywords
        from the expected answer. This is a simplified relevance metric.
        
        Precision@K = relevant_retrieved / total_retrieved
        Recall@K = relevant_retrieved / total_relevant (estimated)
        
        Args:
            retrieved_texts: The text content of retrieved documents
            expected_answer: The expected correct answer
            k: The K value for metrics
            
        Returns:
            Tuple of (precision, recall)
        """
        # Extract key terms from expected answer (words > 4 chars, lowercased)
        expected_terms = set(
            word.lower().strip(".,!?;:'\"")
            for word in expected_answer.split()
            if len(word) > 4  # Skip short common words
        )

        if not expected_terms:
            return 0.0, 0.0

        # Count how many retrieved docs contain relevant terms
        relevant_count = 0
        for doc_text in retrieved_texts[:k]:
            doc_lower = doc_text.lower()
            # A doc is "relevant" if it contains at least 2 key terms
            matching_terms = sum(1 for term in expected_terms if term in doc_lower)
            if matching_terms >= 2:
                relevant_count += 1

        # Precision@K: what fraction of retrieved docs are relevant
        precision = relevant_count / min(k, len(retrieved_texts)) if retrieved_texts else 0.0

        # Recall@K: what fraction of relevant info did we find
        # Estimate total relevant = max(relevant_count, 1) since we know at least
        # one doc should have the answer
        estimated_total_relevant = max(relevant_count, 1)
        recall = relevant_count / estimated_total_relevant if estimated_total_relevant > 0 else 0.0

        return precision, recall

    def _calculate_answer_relevance(
        self,
        generated_answer: str,
        expected_answer: str
    ) -> float:
        """
        Calculate how relevant the generated answer is to the expected answer.
        
        Uses a simple keyword overlap score (Jaccard similarity on key terms).
        For production, you'd use an LLM-as-judge or embedding similarity.
        
        Score range: 0.0 (completely irrelevant) to 1.0 (perfect match)
        """
        # Tokenize and normalize
        def extract_terms(text: str) -> set:
            return set(
                word.lower().strip(".,!?;:'\"()")
                for word in text.split()
                if len(word) > 3
            )

        generated_terms = extract_terms(generated_answer)
        expected_terms = extract_terms(expected_answer)

        if not expected_terms or not generated_terms:
            return 0.0

        # Jaccard similarity: intersection / union
        intersection = generated_terms & expected_terms
        union = generated_terms | expected_terms

        return len(intersection) / len(union) if union else 0.0

    def _aggregate_results(self, results: List[EvaluationResult]) -> EvaluationReport:
        """Aggregate individual results into a summary report."""
        n = len(results)
        if n == 0:
            return EvaluationReport()

        report = EvaluationReport(
            total_questions=n,
            avg_retrieval_time_ms=sum(r.retrieval_time_ms for r in results) / n,
            avg_generation_time_ms=sum(r.generation_time_ms for r in results) / n,
            avg_total_time_ms=sum(r.total_time_ms for r in results) / n,
            avg_precision_at_k=sum(r.precision_at_k for r in results) / n,
            avg_recall_at_k=sum(r.recall_at_k for r in results) / n,
            avg_answer_relevance=sum(r.answer_relevance_score for r in results) / n,
            individual_results=results,
        )

        return report

    def run_latency_test(self, num_queries: int = 10) -> Dict[str, Any]:
        """
        Run a dedicated latency/performance test.
        
        Sends multiple queries and measures response time statistics.
        
        Args:
            num_queries: Number of queries to run
            
        Returns:
            Dict with min, max, avg, p95 latency in milliseconds
        """
        questions = get_sample_questions()
        latencies = []

        for i in range(num_queries):
            question = questions[i % len(questions)]
            start = time.time()
            self.rag_chain.ask(question)
            latency = (time.time() - start) * 1000
            latencies.append(latency)
            self.rag_chain.clear_history()

        latencies.sort()

        return {
            "num_queries": num_queries,
            "min_latency_ms": latencies[0],
            "max_latency_ms": latencies[-1],
            "avg_latency_ms": sum(latencies) / len(latencies),
            "median_latency_ms": latencies[len(latencies) // 2],
            "p95_latency_ms": latencies[int(len(latencies) * 0.95)],
        }
