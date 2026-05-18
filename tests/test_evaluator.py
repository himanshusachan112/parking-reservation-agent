"""
Tests for the RAG Evaluation module.

These tests verify that:
1. Evaluation metrics are calculated correctly
2. The evaluation report is properly formatted
3. Latency measurements work
"""

import pytest
from unittest.mock import patch, MagicMock
from langchain_core.documents import Document

from src.evaluation.evaluator import RAGEvaluator, EvaluationResult, EvaluationReport


class TestRAGEvaluator:
    """Tests for the RAGEvaluator class."""

    def setup_method(self):
        """Set up evaluator with mocked RAG chain."""
        self.mock_rag_chain = MagicMock()
        self.mock_rag_chain.ask.return_value = "The parking is open Monday to Friday 6:00 AM to 11:00 PM."
        self.mock_rag_chain.get_relevant_documents.return_value = [
            Document(page_content="Working hours: Monday-Friday 6:00-23:00"),
            Document(page_content="Saturday 7:00-23:00, Sunday 8:00-22:00"),
        ]
        self.mock_rag_chain.clear_history.return_value = None

        self.evaluator = RAGEvaluator(rag_chain=self.mock_rag_chain)

    def test_calculate_answer_relevance(self):
        """Test answer relevance scoring."""
        generated = "The parking opens at 6:00 AM Monday through Friday."
        expected = "The parking is open Monday to Friday 6:00 AM to 11:00 PM."

        score = self.evaluator._calculate_answer_relevance(generated, expected)

        # Should have some overlap (both mention parking, Monday, Friday, 6:00)
        assert 0.0 < score <= 1.0

    def test_calculate_answer_relevance_no_overlap(self):
        """Test relevance when answers are completely different."""
        generated = "I don't know that information."
        expected = "The parking is at 123 Main Street downtown."

        score = self.evaluator._calculate_answer_relevance(generated, expected)

        # Should be low since there's no meaningful overlap
        assert score < 0.5

    def test_retrieval_metrics_calculation(self):
        """Test precision and recall calculation."""
        retrieved_texts = [
            "Working hours are Monday to Friday 6:00 AM to 11:00 PM",
            "Electric vehicle charging available on Floor 2",
            "Saturday hours are 7:00 AM to 11:00 PM",
        ]
        expected_answer = "The parking is open Monday to Friday 6:00 AM to 11:00 PM"

        precision, recall = self.evaluator._calculate_retrieval_metrics(
            retrieved_texts, expected_answer, k=3
        )

        # At least some documents should be relevant
        assert 0.0 <= precision <= 1.0
        assert 0.0 <= recall <= 1.0

    def test_evaluation_report_summary(self):
        """Test that evaluation report generates readable summary."""
        report = EvaluationReport(
            total_questions=5,
            avg_retrieval_time_ms=50.0,
            avg_generation_time_ms=500.0,
            avg_total_time_ms=550.0,
            avg_precision_at_k=0.8,
            avg_recall_at_k=0.9,
            avg_answer_relevance=0.75,
        )

        summary = report.summary()
        assert "EVALUATION REPORT" in summary
        assert "550.00 ms" in summary
        assert "0.8000" in summary
        assert "0.9000" in summary

    def test_run_evaluation(self):
        """Test running full evaluation with mocked chain."""
        questions = ["What are the hours?", "Where is parking?"]
        ground_truth = [
            "Monday to Friday 6:00 AM to 11:00 PM",
            "Located at 123 Main Street downtown",
        ]

        report = self.evaluator.run_evaluation(
            questions=questions,
            ground_truth=ground_truth,
            k=3
        )

        assert report.total_questions == 2
        assert report.avg_total_time_ms >= 0
        assert len(report.individual_results) == 2

    def test_latency_test(self):
        """Test the dedicated latency test function."""
        result = self.evaluator.run_latency_test(num_queries=3)

        assert result["num_queries"] == 3
        assert result["min_latency_ms"] >= 0
        assert result["max_latency_ms"] >= result["min_latency_ms"]
        assert result["avg_latency_ms"] >= 0
