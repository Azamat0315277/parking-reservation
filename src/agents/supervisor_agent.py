import os
from src.tools.rag_tool import search_parking_policies
from src.tools.sql_reader_tool import (
    check_availability,
    get_pricing,
    get_spot_details,
    find_available_spot,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from src.prompts.supervisor_prompt import SUPERVISOR_PROMPT
load_dotenv()

model = ChatGoogleGenerativeAI(
    model=os.getenv("LLM_MODEL"),
    temperature=0,
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
