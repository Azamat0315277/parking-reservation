"""
Unit tests for RAGAS evaluator module.

Tests dataset preparation, evaluation pipeline, and result handling.
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import dataclass


class TestEvaluationResult:
    """Test EvaluationResult dataclass."""

    def test_default_values(self):
        """EvaluationResult should have correct defaults."""
        from src.evaluation.metrics.ragas_evaluator import EvaluationResult

        result = EvaluationResult()

        assert result.overall_scores == {}
        assert result.per_sample_scores == []
        assert result.metadata == {}

    def test_custom_values(self):
        """EvaluationResult should accept custom values."""
        from src.evaluation.metrics.ragas_evaluator import EvaluationResult

        result = EvaluationResult(
            overall_scores={'context_precision': 0.85},
            per_sample_scores=[{'question': 'Q1', 'score': 0.85}],
            metadata={'num_samples': 1},
        )

        assert result.overall_scores['context_precision'] == 0.85
        assert len(result.per_sample_scores) == 1
        assert result.metadata['num_samples'] == 1


class TestMetricNameMapping:
    """Test metric name mapping."""

    def test_metric_name_map_exists(self):
        """Metric name map should be defined."""
        from src.evaluation.metrics.ragas_evaluator import METRIC_NAME_MAP

        assert 'context_precision' in METRIC_NAME_MAP
        assert 'context_recall' in METRIC_NAME_MAP

    def test_metric_name_map_values(self):
        """Metric names should map to RAGAS column names."""
        from src.evaluation.metrics.ragas_evaluator import METRIC_NAME_MAP

        assert METRIC_NAME_MAP['context_precision'] == 'llm_context_precision_without_reference'
        assert METRIC_NAME_MAP['context_recall'] == 'context_recall'

    def test_reverse_mapping_exists(self):
        """Reverse mapping for display should exist."""
        from src.evaluation.metrics.ragas_evaluator import METRIC_DISPLAY_MAP

        assert 'llm_context_precision_without_reference' in METRIC_DISPLAY_MAP
        assert METRIC_DISPLAY_MAP['llm_context_precision_without_reference'] == 'context_precision'


class TestRAGASEvaluatorInit:
    """Test RAGASEvaluator initialization."""

    def test_default_models(self):
        """Default models should be set from environment."""
        from src.evaluation.metrics.ragas_evaluator import RAGASEvaluator

        with patch.dict('os.environ', {
            'LLM_MODEL': 'gemini-2.0-flash',
            'EMBEDDING_MODEL': 'gemini-embedding-001',
        }):
            evaluator = RAGASEvaluator()

        assert evaluator.llm_model == 'gemini-2.0-flash'
        assert evaluator.embedding_model == 'gemini-embedding-001'

    def test_custom_models(self):
        """Custom models should override defaults."""
        from src.evaluation.metrics.ragas_evaluator import RAGASEvaluator

        evaluator = RAGASEvaluator(
            llm_model='custom-llm',
            embedding_model='custom-embeddings',
        )

        assert evaluator.llm_model == 'custom-llm'
        assert evaluator.embedding_model == 'custom-embeddings'

    def test_lazy_initialization(self):
        """LLM and embeddings should be lazily initialized."""
        from src.evaluation.metrics.ragas_evaluator import RAGASEvaluator

        evaluator = RAGASEvaluator()

        assert evaluator._llm is None
        assert evaluator._embeddings is None


class TestRAGASEvaluatorPrepareDataset:
    """Test prepare_dataset method."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator instance."""
        from src.evaluation.metrics.ragas_evaluator import RAGASEvaluator
        return RAGASEvaluator()

    @pytest.fixture
    def mock_rag_outputs(self):
        """Create mock RAG outputs."""
        @dataclass
        class MockRAGOutput:
            question: str
            answer: str
            contexts: list

        return [
            MockRAGOutput(
                question='What are the operating hours?',
                answer='The facility is open 24/7.',
                contexts=['Operating Hours: 24/7', 'We never close.'],
            ),
            MockRAGOutput(
                question='What is the pricing?',
                answer='Regular parking is $3/hour.',
                contexts=['Regular: $3/hour', 'Premium: $5/hour'],
            ),
        ]

    @pytest.fixture
    def ground_truths(self):
        """Create ground truth data."""
        return [
            {
                'question': 'What are the operating hours?',
                'ground_truth': 'The parking facility operates 24/7.',
                'ground_truth_contexts': ['Open 24 hours'],
            },
            {
                'question': 'What is the pricing?',
                'ground_truth': 'Regular parking costs $3 per hour.',
                'ground_truth_contexts': ['$3/hour for regular'],
            },
        ]

    def test_prepare_dataset_matching_questions(self, evaluator, mock_rag_outputs, ground_truths):
        """Prepare dataset with matching questions."""
        dataset = evaluator.prepare_dataset(mock_rag_outputs, ground_truths)

        assert len(dataset.samples) == 2

    def test_prepare_dataset_unmatched_questions(self, evaluator, mock_rag_outputs):
        """Unmatched questions should be excluded."""
        ground_truths = [
            {
                'question': 'Different question',
                'ground_truth': 'Different answer',
            },
        ]

        dataset = evaluator.prepare_dataset(mock_rag_outputs, ground_truths)

        assert len(dataset.samples) == 0

    def test_prepare_dataset_partial_match(self, evaluator, mock_rag_outputs, ground_truths):
        """Partial matches should include only matched questions."""
        # Only include one ground truth
        partial_gt = [ground_truths[0]]

        dataset = evaluator.prepare_dataset(mock_rag_outputs, partial_gt)

        assert len(dataset.samples) == 1


class TestRAGASEvaluatorEvaluate:
    """Test evaluate method."""

    @pytest.fixture
    def evaluator(self):
        """Create evaluator with mocked LLM."""
        from src.evaluation.metrics.ragas_evaluator import RAGASEvaluator

        evaluator = RAGASEvaluator()
        evaluator._llm = MagicMock()
        evaluator._embeddings = MagicMock()
        return evaluator

    def test_evaluate_empty_dataset(self, evaluator):
        """Empty dataset should return error result."""
        from src.evaluation.metrics.ragas_evaluator import EvaluationResult

        result = evaluator.evaluate([], [])

        assert result.overall_scores == {}
        assert 'error' in result.metadata

    @patch('src.evaluation.metrics.ragas_evaluator.evaluate')
    def test_evaluate_returns_scores(self, mock_ragas_evaluate, evaluator):
        """Successful evaluation should return scores."""
        import pandas as pd
        from src.evaluation.capture.rag_capture import RAGOutput

        # Mock RAGAS results
        mock_results = MagicMock()
        mock_results.to_pandas.return_value = pd.DataFrame({
            'user_input': ['Q1'],
            'response': ['A1'],
            'llm_context_precision_without_reference': [0.85],
            'context_recall': [0.90],
        })
        mock_ragas_evaluate.return_value = mock_results

        rag_outputs = [
            RAGOutput(question='Q1', answer='A1', contexts=['ctx'], source_nodes=[]),
        ]
        ground_truths = [
            {'question': 'Q1', 'ground_truth': 'GT1', 'ground_truth_contexts': ['ctx']},
        ]

        result = evaluator.evaluate(rag_outputs, ground_truths)

        assert 'context_precision' in result.overall_scores
        assert 'context_recall' in result.overall_scores

    @patch('src.evaluation.metrics.ragas_evaluator.evaluate')
    def test_evaluate_handles_exception(self, mock_ragas_evaluate, evaluator):
        """Evaluation errors should be handled gracefully."""
        from src.evaluation.capture.rag_capture import RAGOutput

        mock_ragas_evaluate.side_effect = Exception("Evaluation failed")

        rag_outputs = [
            RAGOutput(question='Q1', answer='A1', contexts=['ctx'], source_nodes=[]),
        ]
        ground_truths = [
            {'question': 'Q1', 'ground_truth': 'GT1', 'ground_truth_contexts': ['ctx']},
        ]

        result = evaluator.evaluate(rag_outputs, ground_truths)

        assert 'error' in result.metadata
        assert 'Evaluation failed' in result.metadata['error']

    @patch('src.evaluation.metrics.ragas_evaluator.evaluate')
    def test_evaluate_custom_metrics(self, mock_ragas_evaluate, evaluator):
        """Should support custom metric selection."""
        import pandas as pd
        from src.evaluation.capture.rag_capture import RAGOutput

        mock_results = MagicMock()
        mock_results.to_pandas.return_value = pd.DataFrame({
            'user_input': ['Q1'],
            'response': ['A1'],
            'llm_context_precision_without_reference': [0.85],
        })
        mock_ragas_evaluate.return_value = mock_results

        rag_outputs = [
            RAGOutput(question='Q1', answer='A1', contexts=['ctx'], source_nodes=[]),
        ]
        ground_truths = [
            {'question': 'Q1', 'ground_truth': 'GT1', 'ground_truth_contexts': ['ctx']},
        ]

        # Only evaluate context_precision
        result = evaluator.evaluate(rag_outputs, ground_truths, metrics=['context_precision'])

        # Should have called RAGAS with only precision metric
        assert mock_ragas_evaluate.called


class TestLoadGroundTruth:
    """Test load_ground_truth function."""

    def test_load_from_default_path(self, tmp_path):
        """Load ground truth from default path."""
        import json
        from pathlib import Path

        # Create test file
        gt_file = tmp_path / "ground_truth.json"
        gt_data = {
            'test_cases': [
                {'question': 'Q1', 'ground_truth': 'A1'},
            ]
        }
        gt_file.write_text(json.dumps(gt_data))

        from src.evaluation.metrics.ragas_evaluator import load_ground_truth

        with patch.object(Path, '__new__', return_value=tmp_path):
            result = load_ground_truth(str(gt_file))

        assert len(result) == 1

    def test_load_from_custom_path(self, tmp_path):
        """Load ground truth from custom path."""
        import json
        from src.evaluation.metrics.ragas_evaluator import load_ground_truth

        custom_file = tmp_path / "custom_gt.json"
        gt_data = {
            'test_cases': [
                {'question': 'Q1', 'ground_truth': 'A1'},
                {'question': 'Q2', 'ground_truth': 'A2'},
            ]
        }
        custom_file.write_text(json.dumps(gt_data))

        result = load_ground_truth(str(custom_file))

        assert len(result) == 2


class TestEvaluateRAGSystem:
    """Test evaluate_rag_system convenience function."""

    @patch('src.evaluation.capture.rag_capture.RAGCaptureEngine')
    @patch('src.evaluation.metrics.ragas_evaluator.RAGASEvaluator')
    @patch('src.evaluation.metrics.ragas_evaluator.load_ground_truth')
    def test_evaluate_rag_system_full_pipeline(self, mock_load_gt, mock_evaluator_cls, mock_capture_cls):
        """Full pipeline should capture and evaluate."""
        from src.evaluation.metrics.ragas_evaluator import evaluate_rag_system, EvaluationResult

        mock_load_gt.return_value = [
            {'question': 'Q1', 'ground_truth': 'A1'},
        ]

        mock_engine = MagicMock()
        mock_engine.batch_query_with_capture.return_value = [MagicMock()]
        mock_capture_cls.return_value = mock_engine

        mock_eval_instance = MagicMock()
        mock_eval_instance.evaluate.return_value = EvaluationResult(
            overall_scores={'context_precision': 0.9},
            per_sample_scores=[],
            metadata={},
        )
        mock_evaluator_cls.return_value = mock_eval_instance

        result = evaluate_rag_system(verbose=False)

        assert result.overall_scores['context_precision'] == 0.9
        mock_engine.batch_query_with_capture.assert_called_once()
        mock_eval_instance.evaluate.assert_called_once()

    @patch('src.evaluation.capture.rag_capture.RAGCaptureEngine')
    @patch('src.evaluation.metrics.ragas_evaluator.load_ground_truth')
    def test_evaluate_with_specific_questions(self, mock_load_gt, mock_capture_cls):
        """Should evaluate only specified questions."""
        from src.evaluation.metrics.ragas_evaluator import evaluate_rag_system, RAGASEvaluator

        mock_load_gt.return_value = [
            {'question': 'Q1', 'ground_truth': 'A1'},
            {'question': 'Q2', 'ground_truth': 'A2'},
        ]

        mock_engine = MagicMock()
        mock_engine.batch_query_with_capture.return_value = []
        mock_capture_cls.return_value = mock_engine

        with patch.object(RAGASEvaluator, 'evaluate') as mock_eval:
            mock_eval.return_value = MagicMock(overall_scores={})

            evaluate_rag_system(questions=['Q1'], verbose=False)

            # Should only capture Q1
            call_args = mock_engine.batch_query_with_capture.call_args
            assert call_args[0][0] == ['Q1']
