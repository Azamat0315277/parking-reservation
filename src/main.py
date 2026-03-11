import asyncio
import uuid
from dotenv import load_dotenv
from src.workflow.workflow import parking_graph
from langchain_core.messages import HumanMessage
from langgraph.types import Command

load_dotenv()


async def chat_session():
    """Interactive chat session supporting multi-turn conversations with human-in-the-loop."""
    # Generate unique thread ID for this session
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}

    print("=" * 60)
    print("Stargate Parking Assistant")
    print("=" * 60)
    print("Ask about parking availability, policies, or make reservations.")
    print("Type 'exit' or 'quit' to end the session.\n")

    while True:
        # Get user input
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ['exit', 'quit', 'bye']:
            print("\nThank you for using Stargate Parking Assistant. Goodbye!")
            break

        try:
            # Invoke the graph with user message
            result = await parking_graph.ainvoke(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
            )

            # Check if we hit the human approval interrupt
            graph_state = parking_graph.get_state(config)

            if graph_state.next and graph_state.tasks:
                for task in graph_state.tasks:
                    if hasattr(task, "interrupts") and task.interrupts:
                        for intr in task.interrupts:
                            # Display the reservation details
                            print(f"\n{'-' * 60}")
                            print("RESERVATION REQUEST DETECTED")
                            print(f"{'-' * 60}")
                            print(intr.value)
                            print(f"{'-' * 60}")

                            # Collect customer info first, then ask for approval
                            print("\nTo complete this reservation, please provide your details:")
                            customer_name = input("  Your Name: ").strip()
                            car_number = input("  Car/License Plate Number: ").strip()

                            if not customer_name or not car_number:
                                print("\nBoth name and car number are required. Reservation cancelled.")
                                result = await parking_graph.ainvoke(
                                    Command(resume="deny"),
                                    config=config,
                                )
                            else:
                                print(f"\n  Name: {customer_name}")
                                print(f"  Car Number: {car_number}")
                                decision_input = input("\nConfirm reservation? (yes/no): ").strip().lower()

                                if decision_input in ['yes', 'y', 'approve']:
                                    result = await parking_graph.ainvoke(
                                        Command(resume={
                                            "decision": "approve",
                                            "customer_name": customer_name,
                                            "car_number": car_number,
                                        }),
                                        config=config,
                                    )
                                else:
                                    result = await parking_graph.ainvoke(
                                        Command(resume="deny"),
                                        config=config,
                                    )

            # Display the final response
            final_response = result.get('final_response', '')
            if final_response:
                print(f"\nAssistant: {final_response}")
            else:
                # Fallback to last message if final_response not set
                if result.get('messages'):
                    last_msg = result['messages'][-1]
                    if hasattr(last_msg, 'content'):
                        print(f"\nAssistant: {last_msg.content}")

        except Exception as e:
            print(f"\n⚠️  An error occurred: {str(e)}")
            print("Please try again or type 'exit' to quit.")


async def example_flow():
    """Example reservation flow demonstrating the workflow."""
    print("\n" + "=" * 60)
    print("EXAMPLE: Reservation Flow")
    print("=" * 60 + "\n")

    config = {"configurable": {"thread_id": "example-flow"}}

    # Step 1: Informational query
    print("Step 1: Asking about availability...\n")
    result = await parking_graph.ainvoke(
        {"messages": [HumanMessage(content="How many Standard spots are available?")]},
        config=config,
    )
    print(f"Assistant: {result['final_response']}\n")

    # Step 2: Request reservation (same thread)
    print("Step 2: Requesting a reservation...\n")
    result = await parking_graph.ainvoke(
        {"messages": [HumanMessage(content="Reserve a Premium spot from 2025-06-01 to 2025-06-02")]},
        config=config,
    )

    # Check for interrupt
    graph_state = parking_graph.get_state(config)
    if graph_state.next and graph_state.tasks:
        for task in graph_state.tasks:
            if hasattr(task, "interrupts") and task.interrupts:
                for intr in task.interrupts:
                    print(f"Reservation details:\n{intr.value}\n")

    # Step 3: Approve with customer info
    print("Step 3: Approving reservation with customer details...\n")
    result = await parking_graph.ainvoke(
        Command(resume={
            "decision": "approve",
            "customer_name": "John Doe",
            "car_number": "ABC-1234",
        }),
        config=config,
    )

    print(f"Final Result:\n{result['final_response']}\n")


def run_api_server():
    """Run the FastAPI server for admin approval."""
    import uvicorn
    from src.api.main import app

    print("\n" + "=" * 60)
    print("Starting Admin Approval API Server")
    print("=" * 60)
    print("Swagger UI: http://localhost:8000/docs")
    print("ReDoc: http://localhost:8000/redoc")
    print("=" * 60 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)


async def main():
    """Main entry point - choose between interactive chat, example flow, or API server."""
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--example":
            await example_flow()
        elif sys.argv[1] == "--api":
            run_api_server()
        else:
            print("Usage: python -m src.main [--example | --api]")
            print("  (no args)  : Interactive chat session")
            print("  --example  : Run example reservation flow")
            print("  --api      : Start admin approval API server")
    else:
        await chat_session()


if __name__ == "__main__":
    asyncio.run(main())
