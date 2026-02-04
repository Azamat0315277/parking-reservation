import asyncio
from dotenv import load_dotenv
from src.workflow.workflow import parking_graph
from langchain_core.messages import HumanMessage
from langgraph.types import Command
load_dotenv()


async def main():
    """Main reservation flow with human-in-the-loop."""
    config = {"configurable": {"thread_id": "reserve-2"}}

    # Step 1: Request a reservation — graph will pause at human_approval (interrupt)
    result = await parking_graph.ainvoke(
        {"messages": [HumanMessage(content="Reserve for me Premium spot from 2025-06-01 to 2025-06-02")]},
        config=config,
    )

    # The graph is now paused. Check the interrupt value:
    graph_state = parking_graph.get_state(config)
    for task in graph_state.tasks:
        if hasattr(task, "interrupts"):
            for intr in task.interrupts:
                print(intr.value)

    # Step 2: Resume the graph with customer info + approval (or "deny" to cancel)
    result = await parking_graph.ainvoke(
        Command(resume={
            "decision": "approve",
            "customer_name": "John Doe",
            "car_number": "ABC-1234",
        }),
        config=config,
    )
    print("Final:", result["final_response"])


if __name__ == "__main__":
    asyncio.run(main())
