"""
Unit tests for evaluation CLI module.

Tests argument parsing, filtering, and report formatting.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


class TestLoadGroundTruth:
    """Test load_ground_truth function."""

    def test_load_valid_json(self, tmp_path):
        """Load valid ground truth JSON file."""
        from src.evaluation.cli import load_ground_truth

        gt_file = tmp_path / "ground_truth.json"
        gt_data = {
            'test_cases': [
                {'id': 'tc_001', 'question': 'Q1', 'ground_truth': 'A1'},
                {'id': 'tc_002', 'question': 'Q2', 'ground_truth': 'A2'},
            ]
        }
        gt_file.write_text(json.dumps(gt_data))

        result = load_ground_truth(str(gt_file))

        assert 'test_cases' in result
        assert len(result['test_cases']) == 2

    def test_load_nonexistent_file(self):
        """Loading non-existent file should raise error."""
        from src.evaluation.cli import load_ground_truth

        with pytest.raises(FileNotFoundError):
            load_ground_truth('/nonexistent/path.json')

    def test_load_invalid_json(self, tmp_path):
        """Loading invalid JSON should raise error."""
        from src.evaluation.cli import load_ground_truth

        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json {{{")

        with pytest.raises(json.JSONDecodeError):
            load_ground_truth(str(invalid_file))


class TestFilterQuestions:
    """Test filter_questions function."""

    @pytest.fixture
    def test_cases(self):
        """Sample test cases for filtering."""
        return [
            {'id': 'tc_001', 'category': 'pricing', 'question': 'Q1'},
            {'id': 'tc_002', 'category': 'pricing', 'question': 'Q2'},
            {'id': 'tc_003', 'category': 'hours', 'question': 'Q3'},
            {'id': 'tc_004', 'category': 'ev_charging', 'question': 'Q4'},
            {'id': 'tc_005', 'category': 'pricing', 'question': 'Q5'},
        ]

    def test_filter_by_num_questions(self, test_cases):
        """Filter to first N questions."""
        from src.evaluation.cli import filter_questions

        result = filter_questions(test_cases, num_questions=3)

        assert len(result) == 3
        assert result[0]['id'] == 'tc_001'

    def test_filter_by_category(self, test_cases):
        """Filter by category."""
        from src.evaluation.cli import filter_questions

        result = filter_questions(test_cases, category='pricing')

        assert len(result) == 3
        assert all(tc['category'] == 'pricing' for tc in result)

    def test_filter_by_question_ids(self, test_cases):
        """Filter by specific question IDs."""
        from src.evaluation.cli import filter_questions

        result = filter_questions(test_cases, question_ids=['tc_002', 'tc_004'])

        assert len(result) == 2
        assert result[0]['id'] == 'tc_002'
        assert result[1]['id'] == 'tc_004'

    def test_filter_combined(self, test_cases):
        """Combine multiple filters."""
        from src.evaluation.cli import filter_questions

        # Filter by category first, then limit
        result = filter_questions(test_cases, category='pricing', num_questions=2)

        assert len(result) == 2
        assert all(tc['category'] == 'pricing' for tc in result)

    def test_filter_no_matches(self, test_cases):
        """Return empty list when no matches."""
        from src.evaluation.cli import filter_questions

        result = filter_questions(test_cases, category='nonexistent')

        assert result == []

    def test_filter_none_returns_all(self, test_cases):
        """No filters returns all test cases."""
        from src.evaluation.cli import filter_questions

        result = filter_questions(test_cases)

        assert len(result) == 5


class TestFormatConsoleReport:
    """Test format_console_report function."""

    def test_format_with_scores(self):
        """Format report with evaluation scores."""
        from src.evaluation.cli import format_console_report
        from src.evaluation.metrics.ragas_evaluator import EvaluationResult

        result = EvaluationResult(
            overall_scores={
                'context_precision': 0.85,
                'context_recall': 0.90,
            },
            per_sample_scores=[
                {
                    'question': 'What are the prices?',
                    'answer': 'Prices are $3/hour...',
                    'context_precision': 0.85,
                    'context_recall': 0.90,
                },
            ],
            metadata={
                'num_samples': 1,
                'llm_model': 'gemini-2.0-flash',
            },
        )

        report = format_console_report(result)

        assert 'RAGAS RAG EVALUATION REPORT' in report
        assert 'OVERALL SCORES' in report
        assert 'context_precision' in report
        assert '0.85' in report or '0.8500' in report
        assert 'PER-SAMPLE SCORES' in report

    def test_format_empty_scores(self):
        """Format report with no scores."""
        from src.evaluation.cli import format_console_report
        from src.evaluation.metrics.ragas_evaluator import EvaluationResult

        result = EvaluationResult(
            overall_scores={},
            per_sample_scores=[],
            metadata={'num_samples': 0},
        )

        report = format_console_report(result)

        assert 'RAGAS RAG EVALUATION REPORT' in report
        # Should still produce valid output

    def test_format_long_question_truncated(self):
        """Long questions should be truncated in report."""
        from src.evaluation.cli import format_console_report
        from src.evaluation.metrics.ragas_evaluator import EvaluationResult

        long_question = 'A' * 100  # 100 characters
        result = EvaluationResult(
            overall_scores={'context_precision': 0.5},
            per_sample_scores=[
                {
                    'question': long_question,
                    'answer': 'Answer',
                    'context_precision': 0.5,
                },
            ],
            metadata={'num_samples': 1},
        )

        report = format_console_report(result)

        # Question should be truncated with ...
        assert '...' in report

    def test_format_null_score_shows_na(self):
        """Null scores should show N/A."""
        from src.evaluation.cli import format_console_report
        from src.evaluation.metrics.ragas_evaluator import EvaluationResult

        result = EvaluationResult(
            overall_scores={'context_precision': 0.5},
            per_sample_scores=[
                {
                    'question': 'Q1',
                    'answer': 'A1',
                    'context_precision': None,  # Null score
                    'context_recall': 0.8,
                },
            ],
            metadata={'num_samples': 1},
        )

        report = format_console_report(result)

        assert 'N/A' in report


class TestMainCLI:
    """Test main CLI entry point."""

    @patch('src.evaluation.capture.rag_capture.RAGCaptureEngine')
    @patch('src.evaluation.metrics.ragas_evaluator.RAGASEvaluator')
    @patch('src.evaluation.cli.load_ground_truth')
    def test_main_runs_evaluation(self, mock_load_gt, mock_evaluator_cls, mock_capture_cls, tmp_path):
        """Main should run full evaluation pipeline."""
        from src.evaluation.cli import main
        from src.evaluation.metrics.ragas_evaluator import EvaluationResult

        # Setup mocks
        mock_load_gt.return_value = {
            'test_cases': [
                {'id': 'tc_001', 'question': 'Q1', 'ground_truth': 'A1'},
            ]
        }

        mock_engine = MagicMock()
        mock_output = MagicMock()
        mock_output.question = 'Q1'
        mock_output.answer = 'A1'
        mock_output.contexts = ['ctx']
        mock_engine.batch_query_with_capture.return_value = [mock_output]
        mock_capture_cls.return_value = mock_engine

        mock_eval = MagicMock()
        mock_eval.evaluate.return_value = EvaluationResult(
            overall_scores={'context_precision': 0.9},
            per_sample_scores=[],
            metadata={'num_samples': 1},
        )
        mock_evaluator_cls.return_value = mock_eval

        # Run with mock args
        with patch('sys.argv', ['cli.py', '--questions', '1']):
            with pytest.raises(SystemExit) as exc_info:
                main()

        # Should exit 0 (success) for high score
        assert exc_info.value.code == 0

    @patch('src.evaluation.cli.load_ground_truth')
    def test_main_handles_file_not_found(self, mock_load_gt):
        """Main should handle missing ground truth file."""
        from src.evaluation.cli import main

        mock_load_gt.side_effect = FileNotFoundError("File not found")

        with patch('sys.argv', ['cli.py']):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1

    @patch('src.evaluation.cli.load_ground_truth')
    def test_main_handles_json_error(self, mock_load_gt):
        """Main should handle invalid JSON."""
        from src.evaluation.cli import main

        mock_load_gt.side_effect = json.JSONDecodeError("Invalid", "", 0)

        with patch('sys.argv', ['cli.py']):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1


class TestCLIArguments:
    """Test CLI argument parsing."""

    def test_default_arguments(self):
        """Default arguments should be set correctly."""
        import argparse

        # Parse default args
        parser = argparse.ArgumentParser()
        parser.add_argument('--questions', type=int, default=None)
        parser.add_argument('--category', type=str, default=None)
        parser.add_argument('--verbose', action='store_true')
        parser.add_argument('--metrics', nargs='+', default=['context_precision', 'context_recall'])

        args = parser.parse_args([])

        assert args.questions is None
        assert args.category is None
        assert args.verbose is False
        assert args.metrics == ['context_precision', 'context_recall']

    def test_custom_arguments(self):
        """Custom arguments should be parsed correctly."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument('--questions', '-n', type=int, default=None)
        parser.add_argument('--category', '-c', type=str, default=None)
        parser.add_argument('--output', '-o', type=str, default=None)
        parser.add_argument('--verbose', '-v', action='store_true')
        parser.add_argument('--ids', nargs='+', default=None)

        args = parser.parse_args([
            '--questions', '5',
            '--category', 'pricing',
            '--output', 'report.json',
            '--verbose',
            '--ids', 'tc_001', 'tc_002',
        ])

        assert args.questions == 5
        assert args.category == 'pricing'
        assert args.output == 'report.json'
        assert args.verbose is True
        assert args.ids == ['tc_001', 'tc_002']
