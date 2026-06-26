import os
from src.tools.rag_tool import search_parking_policies
from src.tools.sql_reader_tool import (
    check_availability,
    get_pricing,
    get_spot_details,
    find_available_spot,
)
from langchain_ollama import ChatOllama
from langchain.agents import create_agent
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from src.prompts.supervisor_prompt import SUPERVISOR_PROMPT
from src.llm_config import OLLAMA_BASE_URL, ollama_headers
load_dotenv()

model = ChatOllama(
    model=os.getenv("LLM_MODEL", "gemma4:31b-cloud"),
    base_url=OLLAMA_BASE_URL,
    temperature=0,
    reasoning=False,
    client_kwargs={"headers": ollama_headers()},
)

supervisor_agent = create_agent(
    model,
    tools=[
        check_availability,
        get_pricing,
        get_spot_details,
        find_available_spot,
        search_parking_policies,
    ],
    system_prompt=SUPERVISOR_PROMPT,
    checkpointer=InMemorySaver(),
)
