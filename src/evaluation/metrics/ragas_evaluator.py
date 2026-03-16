"""
RAGAS evaluation pipeline for RAG system.

Implements Context Precision and Context Recall metrics using the RAGAS library.
"""

import os
import json
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path

import pandas as pd
from ragas import evaluate, EvaluationDataset, SingleTurnSample
from ragas.metrics import LLMContextPrecisionWithoutReference, LLMContextRecall
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from dotenv import load_dotenv

from src.evaluation.capture.rag_capture import RAGOutput

load_dotenv()

# Mapping from user-friendly names to actual RAGAS column names
METRIC_NAME_MAP = {
    'context_precision': 'llm_context_precision_without_reference',
    'context_recall': 'context_recall',
}

# Reverse mapping for display
METRIC_DISPLAY_MAP = {v: k for k, v in METRIC_NAME_MAP.items()}


@dataclass
class EvaluationResult:
    """Container for evaluation results."""
    overall_scores: Dict[str, float] = field(default_factory=dict)
    per_sample_scores: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class RAGASEvaluator:
    """
    RAGAS-based evaluator for RAG system.

    Evaluates Context Precision and Context Recall metrics.
    """

    def __init__(
        self,
        llm_model: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        """
        Initialize the RAGAS evaluator.

        Args:
            llm_model: LLM model name for evaluation (default from env)
            embedding_model: Embedding model name (default from env)
        """
        self.llm_model = llm_model or os.getenv("LLM_MODEL", "gemini-2.0-flash")
        self.embedding_model = embedding_model or os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

        self._llm = None
        self._embeddings = None

    def _get_llm(self):
        """Get configured LLM for RAGAS evaluation."""
        if self._llm is None:
            langchain_llm = ChatGoogleGenerativeAI(
                model=self.llm_model,
                temperature=0,
            )
            self._llm = LangchainLLMWrapper(langchain_llm)
        return self._llm

    def _get_embeddings(self):
        """Get configured embeddings for RAGAS evaluation."""
        if self._embeddings is None:
            langchain_embeddings = GoogleGenerativeAIEmbeddings(
                model=f"models/{self.embedding_model}",
            )
            self._embeddings = LangchainEmbeddingsWrapper(langchain_embeddings)
        return self._embeddings

    def prepare_dataset(
        self,
        rag_outputs: List[RAGOutput],
        ground_truths: List[Dict[str, Any]],
    ) -> EvaluationDataset:
        """
        Prepare a RAGAS EvaluationDataset for evaluation.

        Args:
            rag_outputs: List of RAG outputs from capture engine
            ground_truths: List of ground truth entries (from ground_truth.json)

        Returns:
            RAGAS EvaluationDataset
        """
        # Build a lookup from question to ground truth
        gt_lookup = {gt['question']: gt for gt in ground_truths}

        samples = []
        for output in rag_outputs:
            if output.question in gt_lookup:
                gt = gt_lookup[output.question]
                sample = SingleTurnSample(
                    user_input=output.question,
                    response=output.answer,
                    retrieved_contexts=output.contexts,
                    reference=gt['ground_truth'],
                    reference_contexts=gt.get('ground_truth_contexts', []),
                )
                samples.append(sample)

        return EvaluationDataset(samples=samples)

    def evaluate(
        self,
        rag_outputs: List[RAGOutput],
        ground_truths: List[Dict[str, Any]],
        metrics: Optional[List[str]] = None,
    ) -> EvaluationResult:
        """
        Run RAGAS evaluation on RAG outputs.

        Args:
            rag_outputs: List of RAG outputs from capture engine
            ground_truths: List of ground truth entries
            metrics: List of metric names to evaluate (default: precision, recall)

        Returns:
            EvaluationResult with overall and per-sample scores
        """
        # Default metrics
        if metrics is None:
            metrics = ['context_precision', 'context_recall']

        # Build metric objects
        metric_objects = []
        if 'context_precision' in metrics:
            metric_objects.append(LLMContextPrecisionWithoutReference())
        if 'context_recall' in metrics:
            metric_objects.append(LLMContextRecall())

        # Prepare dataset
        dataset = self.prepare_dataset(rag_outputs, ground_truths)

        if len(dataset.samples) == 0:
            return EvaluationResult(
                overall_scores={},
                per_sample_scores=[],
                metadata={'error': 'No matching questions found in ground truth'},
            )

        # Get LLM and embeddings
        llm = self._get_llm()
        embeddings = self._get_embeddings()

        # Run RAGAS evaluation with error handling
        try:
            results = evaluate(
                dataset=dataset,
                metrics=metric_objects,
                llm=llm,
                embeddings=embeddings,
            )
        except Exception as e:
            print(f"RAGAS evaluation failed: {e}")
            return EvaluationResult(
                overall_scores={},
                per_sample_scores=[],
                metadata={
                    'error': str(e),
                    'num_samples': len(dataset.samples),
                },
            )

        # Extract overall scores - handle different RAGAS result formats
        overall_scores = {}
        results_df = results.to_pandas()

        try:
            for metric_name in metrics:
                # Get the actual RAGAS column name
                ragas_col = METRIC_NAME_MAP.get(metric_name, metric_name)

                # Try both the user-friendly name and the RAGAS column name
                col_to_use = None
                if ragas_col in results_df.columns:
                    col_to_use = ragas_col
                elif metric_name in results_df.columns:
                    col_to_use = metric_name

                if col_to_use:
                    scores = results_df[col_to_use].dropna()
                    if len(scores) > 0:
                        overall_scores[metric_name] = float(scores.mean())
        except Exception as e:
            print(f"Error extracting overall scores: {e}")

        # Extract per-sample scores
        per_sample_scores = []
        try:
            for idx, row in results_df.iterrows():
                sample_score = {
                    'question': str(row.get('user_input', '')) if 'user_input' in row.index else '',
                }

                # Truncate answer for display
                answer = str(row.get('response', '')) if 'response' in row.index else ''
                sample_score['answer'] = answer[:200] + '...' if len(answer) > 200 else answer

                for metric_name in metrics:
                    # Get the actual RAGAS column name
                    ragas_col = METRIC_NAME_MAP.get(metric_name, metric_name)

                    # Try both names
                    value = None
                    if ragas_col in row.index:
                        value = row[ragas_col]
                    elif metric_name in row.index:
                        value = row[metric_name]

                    if value is not None and pd.notna(value):
                        sample_score[metric_name] = float(value)
                    else:
                        sample_score[metric_name] = None

                per_sample_scores.append(sample_score)
        except Exception as e:
            print(f"Error extracting per-sample scores: {e}")

        return EvaluationResult(
            overall_scores=overall_scores,
            per_sample_scores=per_sample_scores,
            metadata={
                'num_samples': len(dataset.samples),
                'metrics_evaluated': metrics,
                'llm_model': self.llm_model,
                'embedding_model': self.embedding_model,
            },
        )


def load_ground_truth(path: str = None) -> List[Dict[str, Any]]:
    """Load ground truth dataset from JSON file."""
    if path is None:
        # Default path relative to this file
        path = Path(__file__).parent.parent / "datasets" / "ground_truth.json"

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data.get('test_cases', [])


def evaluate_rag_system(
    questions: Optional[List[str]] = None,
    ground_truth_path: str = None,
    verbose: bool = True,
) -> EvaluationResult:
    """
    Convenience function to run full RAG evaluation pipeline.

    Args:
        questions: Optional list of specific questions to evaluate
                   (default: all questions from ground truth)
        ground_truth_path: Path to ground truth JSON file
        verbose: Whether to print progress

    Returns:
        EvaluationResult with all metrics
    """
    # Load ground truth
    test_cases = load_ground_truth(ground_truth_path)

    # Determine questions to evaluate
    if questions is None:
        questions = [tc['question'] for tc in test_cases]

    if verbose:
        print(f"Loaded {len(test_cases)} test cases")
        print(f"Evaluating {len(questions)} questions...")

    # Capture RAG outputs
    if verbose:
        print("\nCapturing RAG outputs...")

    from src.evaluation.capture.rag_capture import RAGCaptureEngine

    capture_engine = RAGCaptureEngine()
    rag_outputs = capture_engine.batch_query_with_capture(questions, verbose=verbose)

    # Run evaluation
    if verbose:
        print("\nRunning RAGAS evaluation...")

    evaluator = RAGASEvaluator()
    return evaluator.evaluate(rag_outputs, test_cases)
