"""
RAG output capture module for evaluation.

This module provides a wrapper around the existing RAG query engine
to capture both retrieved contexts and generated answers for RAGAS evaluation.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

import pymongo
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Document,
    Settings,
)
from llama_index.core.node_parser import SentenceWindowNodeParser
from llama_index.core.postprocessor import MetadataReplacementPostProcessor
from llama_index.vector_stores.mongodb import MongoDBAtlasVectorSearch
from llama_index.llms.ollama import Ollama
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from dotenv import load_dotenv

from src.llm_config import OLLAMA_BASE_URL, ollama_headers

load_dotenv()


@dataclass
class RAGOutput:
    """Container for RAG query output with captured contexts."""
    question: str
    answer: str
    contexts: List[str] = field(default_factory=list)
    source_nodes: List[dict] = field(default_factory=list)


class RAGCaptureEngine:
    """
    Wrapper around LlamaIndex query engine that captures retrieved contexts.

    This class mirrors the setup in src/tools/rag_tool.py but exposes
    the intermediate retrieval results needed for RAGAS evaluation.
    """

    def __init__(
        self,
        mongo_uri: Optional[str] = None,
        db_name: str = "parking_db",
        collection_name: str = "parking_policy",
        index_name: str = "parking_policy",
        similarity_top_k: int = 6,
    ):
        self.mongo_uri = mongo_uri or os.getenv("MONGODB_URI")
        self.db_name = db_name
        self.collection_name = collection_name
        self.index_name = index_name
        self.similarity_top_k = similarity_top_k

        self._index: Optional[VectorStoreIndex] = None
        self._query_engine = None
        self._retriever = None

        self._setup_settings()

    def _setup_settings(self):
        """Configure LlamaIndex settings (mirrors rag_tool.py)."""
        model_name = os.getenv("LLM_MODEL", "gemma4:31b-cloud")
        embedding_model_name = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

        Settings.llm = Ollama(
            model=model_name,
            base_url=OLLAMA_BASE_URL,
            temperature=0,
            request_timeout=120.0,
            thinking=False,
            headers=ollama_headers(),
        )
        Settings.embed_model = GoogleGenAIEmbedding(
            model_name=embedding_model_name,
            embed_batch_size=500,
        )

    def _build_index(self) -> VectorStoreIndex:
        """Build or load the vector store index."""
        mongo_client = pymongo.MongoClient(self.mongo_uri)

        vector_store = MongoDBAtlasVectorSearch(
            mongodb_client=mongo_client,
            db_name=self.db_name,
            collection_name=self.collection_name,
            vector_index_name=self.index_name,
        )

        # Load existing index (assumes it's already built by rag_tool.py)
        return VectorStoreIndex.from_vector_store(vector_store=vector_store)

    def _get_index(self) -> VectorStoreIndex:
        """Lazy-load the index."""
        if self._index is None:
            self._index = self._build_index()
        return self._index

    def _get_retriever(self):
        """Get the retriever component for context capture."""
        if self._retriever is None:
            index = self._get_index()
            self._retriever = index.as_retriever(
                similarity_top_k=self.similarity_top_k
            )
        return self._retriever

    def _get_query_engine(self):
        """Get the query engine for answer generation."""
        if self._query_engine is None:
            index = self._get_index()
            postproc = MetadataReplacementPostProcessor(target_metadata_key="window")
            self._query_engine = index.as_query_engine(
                similarity_top_k=self.similarity_top_k,
                node_postprocessors=[postproc],
            )
        return self._query_engine

    def query_with_capture(self, question: str) -> RAGOutput:
        """
        Execute RAG query and capture both contexts and answer.

        Args:
            question: The user's question

        Returns:
            RAGOutput containing question, answer, and retrieved contexts
        """
        # Step 1: Retrieve contexts
        retriever = self._get_retriever()
        retrieved_nodes = retriever.retrieve(question)

        # Extract context text from nodes
        # Use 'window' metadata if available (sentence window approach)
        contexts = []
        source_nodes = []

        for node in retrieved_nodes:
            # Prefer window context over original text
            if hasattr(node, 'node') and hasattr(node.node, 'metadata'):
                window_text = node.node.metadata.get('window', '')
                if window_text:
                    contexts.append(window_text)
                else:
                    contexts.append(node.get_content())
            else:
                contexts.append(node.get_content())

            # Store node metadata for debugging
            source_nodes.append({
                'text': node.get_content(),
                'score': getattr(node, 'score', None),
                'metadata': getattr(node.node, 'metadata', {}) if hasattr(node, 'node') else {},
            })

        # Step 2: Generate answer using full query engine
        query_engine = self._get_query_engine()
        response = query_engine.query(question)
        answer = str(response)

        return RAGOutput(
            question=question,
            answer=answer,
            contexts=contexts,
            source_nodes=source_nodes,
        )

    def batch_query_with_capture(
        self,
        questions: List[str],
        verbose: bool = False
    ) -> List[RAGOutput]:
        """
        Execute multiple queries and capture all outputs.

        Args:
            questions: List of questions to evaluate
            verbose: Whether to print progress

        Returns:
            List of RAGOutput objects
        """
        results = []
        total = len(questions)

        for i, question in enumerate(questions, 1):
            if verbose:
                print(f"Processing {i}/{total}: {question[:50]}...")

            try:
                result = self.query_with_capture(question)
                results.append(result)
            except Exception as e:
                # Log error but continue with other questions
                print(f"Error processing question '{question}': {e}")
                results.append(RAGOutput(
                    question=question,
                    answer=f"Error: {str(e)}",
                    contexts=[],
                    source_nodes=[],
                ))

        return results
