import os
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
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from langchain.tools import tool
from dotenv import load_dotenv
load_dotenv()

# Path to parking policy document (relative to this file's location)
parking_policy_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),  # go up to src/
    "data",
    "parking_policy.txt"
)

model_name = os.getenv("LLM_MODEL", "gemini-3-flash-preview")
embedding_model_name = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")

Settings.llm = GoogleGenAI(model=model_name, temperature=0)
Settings.embed_model = GoogleGenAIEmbedding(
    model_name=embedding_model_name,
    embed_batch_size=500,
)


def build_sentence_window_index(
    document,
    mongo_uri,
    db_name: str = "my_rag_db",
    collection_name: str = "sentence_vectors",
    index_name: str = "vector_search_index",
):
    """Build or load a VectorStoreIndex with sentence window parsing and MongoDB backend."""
    print(f"Connecting to MongoDB at {mongo_uri}...")
    mongo_client = pymongo.MongoClient(mongo_uri)
    db = mongo_client[db_name]
    collection = db[collection_name]

    vector_store = MongoDBAtlasVectorSearch(
        mongodb_client=mongo_client,
        db_name=db_name,
        collection_name=collection_name,
        vector_index_name=index_name,
    )

    try:
        existing_indexes = [index["name"] for index in collection.list_search_indexes()]
        if index_name not in existing_indexes:
            print(f"Vector search index '{index_name}' not found. Creating a new one...")
            embed_dim = len(Settings.embed_model.get_text_embedding("test"))
            vector_store.create_vector_search_index(
                dimensions=embed_dim,
                path="embedding",
                similarity="cosine",
            )
            print("Vector search index created successfully.")
        else:
            print(f"Vector search index '{index_name}' already exists.")
    except Exception as e:
        print(f"An error occurred while checking or creating the search index: {e}")
        print("Please ensure you are connected to a MongoDB Atlas instance or a local Atlas deployment.")

    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    node_parser = SentenceWindowNodeParser.from_defaults(
        window_size=3,
        window_metadata_key="window",
        original_text_metadata_key="original_text",
    )

    if collection.count_documents({}) == 0:
        print(f"No documents found. Building new index in MongoDB collection '{collection_name}'...")
        nodes = node_parser.get_nodes_from_documents(document)
        sentence_index = VectorStoreIndex(
            nodes,
            storage_context=storage_context,
        )
    else:
        print(f"Loading existing index from MongoDB collection '{collection_name}'...")
        sentence_index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
        )

    print(f"Index ready from MongoDB collection '{collection_name}'.")
    return sentence_index


def get_sentence_window_query_engine(
    sentence_index: VectorStoreIndex,
    similarity_top_k: int = 6,
):
    """Create a query engine with metadata replacement (no LLM reranking)."""
    postproc = MetadataReplacementPostProcessor(target_metadata_key="window")

    sentence_window_engine = sentence_index.as_query_engine(
        similarity_top_k=similarity_top_k,
        node_postprocessors=[postproc],
    )
    return sentence_window_engine


# Lazy-load: build index and query engine only on first use
_query_engine = None


def _get_query_engine():
    global _query_engine
    if _query_engine is None:
        with open(parking_policy_path, "r") as f:
            content = f.read()
        document = [Document(text=content)]

        sentence_index = build_sentence_window_index(
            document=document,
            mongo_uri=os.getenv("MONGODB_URI"),
            db_name="parking_db",
            collection_name="parking_policy",
            index_name="parking_policy",
        )
        _query_engine = get_sentence_window_query_engine(sentence_index)
    return _query_engine


@tool
def search_parking_policies(question: str) -> str:
    """Search parking policy documents for rules, regulations, and guidelines.

    Use for: parking rules, operating hours, payment policies, violation penalties,
    accessibility info, EV charging policies, permits, refunds, cancellation policies.

    Input: Natural language question about parking policies
    """
    engine = _get_query_engine()
    response = engine.query(question)
    return str(response)
