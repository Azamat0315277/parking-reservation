"""
CLI entry point for RAG evaluation.

Usage:
    python -m src.evaluation.cli                      # Run full evaluation
    python -m src.evaluation.cli --questions 5       # Evaluate first 5 questions
    python -m src.evaluation.cli --category pricing  # Evaluate specific category
    python -m src.evaluation.cli --output report.json # Save report to file
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv

load_dotenv()


def load_ground_truth(path: str) -> dict:
    """Load ground truth dataset from JSON file."""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def filter_questions(
    test_cases: List[dict],
    num_questions: Optional[int] = None,
    category: Optional[str] = None,
    question_ids: Optional[List[str]] = None,
) -> List[dict]:
    """Filter test cases based on criteria."""
    filtered = test_cases

    if category:
        filtered = [tc for tc in filtered if tc.get('category') == category]

    if question_ids:
        filtered = [tc for tc in filtered if tc.get('id') in question_ids]

    if num_questions:
        filtered = filtered[:num_questions]

    return filtered


def format_console_report(result) -> str:
    """Format evaluation result for console output."""
    lines = []
    lines.append("=" * 70)
    lines.append("RAGAS RAG EVALUATION REPORT")
    lines.append("=" * 70)
    lines.append(f"Timestamp: {datetime.now().isoformat()}")
    lines.append(f"Samples Evaluated: {result.metadata.get('num_samples', 'N/A')}")
    lines.append(f"LLM Model: {result.metadata.get('llm_model', 'N/A')}")
    lines.append("")

    lines.append("-" * 70)
    lines.append("OVERALL SCORES")
    lines.append("-" * 70)
    for metric, score in result.overall_scores.items():
        lines.append(f"  {metric}: {score:.4f}")
    lines.append("")

    lines.append("-" * 70)
    lines.append("PER-SAMPLE SCORES")
    lines.append("-" * 70)
    for i, sample in enumerate(result.per_sample_scores, 1):
        question = sample.get('question', '')
        display_q = question[:55] + '...' if len(question) > 55 else question
        lines.append(f"\n[{i}] {display_q}")
        for key, value in sample.items():
            if key not in ('question', 'answer'):
                if value is not None:
                    lines.append(f"    {key}: {value:.4f}")
                else:
                    lines.append(f"    {key}: N/A")

    lines.append("")
    lines.append("=" * 70)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Run RAGAS evaluation on the parking RAG system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.evaluation.cli                        # Full evaluation
  python -m src.evaluation.cli --questions 5          # First 5 questions
  python -m src.evaluation.cli --category ev_charging # Specific category
  python -m src.evaluation.cli --output results.json  # Save to file
  python -m src.evaluation.cli --verbose              # Detailed output
        """
    )

    # Get default ground truth path
    default_gt_path = Path(__file__).parent / "datasets" / "ground_truth.json"

    parser.add_argument(
        '--ground-truth',
        type=str,
        default=str(default_gt_path),
        help='Path to ground truth dataset'
    )

    parser.add_argument(
        '--questions', '-n',
        type=int,
        default=None,
        help='Number of questions to evaluate (default: all)'
    )

    parser.add_argument(
        '--category', '-c',
        type=str,
        default=None,
        help='Filter by category (e.g., pricing, ev_charging, operating_hours)'
    )

    parser.add_argument(
        '--ids',
        type=str,
        nargs='+',
        default=None,
        help='Specific test case IDs to evaluate (e.g., tc_001 tc_002)'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output file path for JSON report (optional)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show verbose output including retrieved contexts'
    )

    parser.add_argument(
        '--metrics',
        type=str,
        nargs='+',
        default=['context_precision', 'context_recall'],
        help='Metrics to evaluate (default: context_precision context_recall)'
    )

    args = parser.parse_args()

    # Load ground truth
    print(f"Loading ground truth from: {args.ground_truth}")
    try:
        gt_data = load_ground_truth(args.ground_truth)
    except FileNotFoundError:
        print(f"Error: Ground truth file not found: {args.ground_truth}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in ground truth file: {e}")
        sys.exit(1)

    test_cases = gt_data.get('test_cases', [])
    print(f"Found {len(test_cases)} test cases in ground truth")

    # Filter test cases
    filtered_cases = filter_questions(
        test_cases,
        num_questions=args.questions,
        category=args.category,
        question_ids=args.ids,
    )

    if not filtered_cases:
        print("Error: No test cases match the specified filters")
        sys.exit(1)

    print(f"Evaluating {len(filtered_cases)} test cases...")

    # Get questions to evaluate
    questions = [tc['question'] for tc in filtered_cases]

    # Run capture
    print("\nCapturing RAG outputs...")
    from src.evaluation.capture.rag_capture import RAGCaptureEngine

    capture_engine = RAGCaptureEngine()
    rag_outputs = capture_engine.batch_query_with_capture(questions, verbose=args.verbose)

    if args.verbose:
        print("\n--- Captured RAG Outputs ---")
        for output in rag_outputs:
            print(f"\nQ: {output.question}")
            print(f"A: {output.answer[:200]}...")
            print(f"Contexts: {len(output.contexts)} retrieved")

    # Run evaluation
    print("\nRunning RAGAS evaluation...")
    from src.evaluation.metrics.ragas_evaluator import RAGASEvaluator

    evaluator = RAGASEvaluator()
    result = evaluator.evaluate(
        rag_outputs,
        filtered_cases,
        metrics=args.metrics,
    )

    # Output results
    console_report = format_console_report(result)
    print(console_report)

    # Save to file if requested
    if args.output:
        output_data = {
            'timestamp': datetime.now().isoformat(),
            'ground_truth_file': args.ground_truth,
            'filters': {
                'num_questions': args.questions,
                'category': args.category,
                'ids': args.ids,
            },
            'overall_scores': result.overall_scores,
            'per_sample_scores': result.per_sample_scores,
            'metadata': result.metadata,
        }

        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2)

        print(f"\nReport saved to: {args.output}")

    # Exit with appropriate code
    avg_score = sum(result.overall_scores.values()) / len(result.overall_scores) if result.overall_scores else 0
    sys.exit(0 if avg_score >= 0.5 else 1)


if __name__ == "__main__":
    main()
