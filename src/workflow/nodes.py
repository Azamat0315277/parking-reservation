import json
import os
import re
import uuid
from langgraph.graph import MessagesState, END
from langgraph.types import interrupt
from langchain_core.messages import AIMessage
from typing import Literal
from datetime import datetime
from src.agents.supervisor_agent import supervisor_agent
from src.tools.sql_reader_tool import find_available_spot
from src.tools.parking_reservation_tool import reserve_parking_space
from src.tools.file_writer_tools import append_reservation
from src.api.services.reservation_service import ReservationService

# Configuration for approval mode
USE_API_APPROVAL = os.getenv("USE_API_APPROVAL", "true").lower() == "true"


# =============================================================
# State
# =============================================================

class ParkingState(MessagesState):
    reservation_details: str  # JSON string with reservation info, or ""
    approval: str             # "approved" / "denied" / "pending_api" / ""
    customer_name: str        # Customer's full name
    car_number: str           # Customer's car/license plate number
    reservation_success: bool # True if reservation UPDATE succeeded
    final_response: str
    pending_reservation_id: str  # UUID of pending reservation (API mode)


# =============================================================
# Node 1: Assistant (Supervisor — handles query + classification)
# =============================================================

def _parse_classification(response_text: str) -> tuple[str, str]:
    """Extract the classification tag and reservation details from supervisor response.

    Returns (clean_response, reservation_details_json_or_empty).
    """
    # Look for <<<RESERVATION:{...}>>> or <<<INFO>>>
    reservation_match = re.search(r'<<<RESERVATION:(\{.*?\})>>>', response_text, re.DOTALL)
    if reservation_match:
        clean = response_text[:reservation_match.start()].strip()
        return clean, reservation_match.group(1)

    info_match = re.search(r'<<<INFO>>>', response_text)
    if info_match:
        clean = response_text[:info_match.start()].strip()
        return clean, ""

    # No tag found — treat as info query
    return response_text.strip(), ""


def assistant_node(state: ParkingState) -> dict:
    """Handle user queries using the supervisor agent and extract classification."""
    user_message = state["messages"][-1].content

    # Use a unique thread_id per invocation to avoid polluting
    # the supervisor agent's context across turns
    supervisor_thread_id = f"supervisor-{uuid.uuid4()}"
    result = supervisor_agent.invoke(
        {"messages": [{"role": "user", "content": user_message}]},
        config={"configurable": {"thread_id": supervisor_thread_id}},
    )

    raw_response = result["messages"][-1].content
    # Some providers return content as a list of blocks; Ollama returns a plain string
    if isinstance(raw_response, list):
        response_text = raw_response[0]["text"] if raw_response else ""
    else:
        response_text = raw_response

    clean_response, reservation_json = _parse_classification(response_text)

    # Validate reservation JSON if present
    reservation_details = ""
    if reservation_json:
        try:
            parsed = json.loads(reservation_json)
            if isinstance(parsed, dict):
                reservation_details = reservation_json
        except json.JSONDecodeError:
            reservation_details = ""

    return {
        "messages": [AIMessage(content=clean_response)],
        "final_response": clean_response,
        "reservation_details": reservation_details,
    }


# =============================================================
# Intent Classifier (passthrough — reads state set by assistant)
# =============================================================

def classify_intent_node(state: ParkingState) -> dict:
    """Passthrough: classification already done in assistant_node."""
    return {}


def route_after_classification(state: ParkingState) -> Literal["human_approval", "__end__"]:
    return "human_approval" if state.get("reservation_details") else END


# =============================================================
# Node 2: Human Approval (Human-in-the-Loop via interrupt)
# =============================================================

def human_approval_node(state: ParkingState) -> dict:
    """Pause the graph and collect customer info + approval decision.

    In CLI mode (USE_API_APPROVAL=false):
        Uses interrupt() for console input.
        Expects resume value as a dict:
            {
                "decision": "approve" or "deny",
                "customer_name": "John Doe",
                "car_number": "ABC-1234"
            }

    In API mode (USE_API_APPROVAL=true):
        Prompts for customer info, creates pending reservation via API,
        and returns immediately. Admin approves/rejects via REST API.
    """
    details_json = state["reservation_details"]
    details = json.loads(details_json)

    if USE_API_APPROVAL:
        # API mode: Prompt for customer info, then submit to API
        response = interrupt(
            f"Reservation request — please provide your name and car number:\n{details_json}"
        )

        if isinstance(response, dict):
            customer_name = response.get("customer_name", "")
            car_number = response.get("car_number", "")
        else:
            customer_name = ""
            car_number = ""

        if not customer_name or not car_number:
            return {
                "approval": "denied",
                "final_response": "Reservation cancelled: customer name and car number are required.",
            }

        # Submit to pending reservations via service
        service = ReservationService()
        try:
            pending = service.create_pending_reservation(
                parking_id=details.get("parking_id"),
                parking_type=details.get("parking_type"),
                start_time=details.get("start_time"),
                end_time=details.get("end_time"),
                customer_name=customer_name,
                car_number=car_number,
                total_price=details.get("total_price"),
            )

            msg = (
                f"Your reservation request has been submitted for admin approval.\n"
                f"  Request ID: {pending['id']}\n"
                f"  Customer: {customer_name}\n"
                f"  Car Number: {car_number}\n"
                f"  Parking: #{details.get('parking_id')} ({details.get('parking_type')})\n"
                f"  From: {details.get('start_time')}\n"
                f"  To: {details.get('end_time')}\n\n"
                f"You will be notified once the admin processes your request.\n"
                f"Check status at: GET /reservations/{pending['id']}/status"
            )

            return {
                "approval": "pending_api",
                "customer_name": customer_name,
                "car_number": car_number,
                "pending_reservation_id": pending["id"],
                "final_response": msg,
            }
        except Exception as e:
            return {
                "approval": "denied",
                "final_response": f"Failed to submit reservation request: {e}",
            }

    # CLI mode: Original interrupt-based logic
    response = interrupt(
        f"Reservation request — please provide your name, car number, "
        f"and approve or deny:\n{details_json}"
    )

    # Support both dict (with customer info) and plain string (legacy)
    if isinstance(response, dict):
        decision = response.get("decision", "deny")
        customer_name = response.get("customer_name", "")
        car_number = response.get("car_number", "")
    else:
        decision = response
        customer_name = ""
        car_number = ""

    approval = "approved" if decision == "approve" else "denied"

    if approval == "approved" and (not customer_name or not car_number):
        return {
            "approval": "denied",
            "final_response": "Reservation cancelled: customer name and car number are required.",
        }

    return {
        "approval": approval,
        "customer_name": customer_name,
        "car_number": car_number,
    }


def route_after_approval(state: ParkingState) -> Literal["reservation", "denial", "__end__"]:
    approval = state.get("approval", "")
    if approval == "approved":
        return "reservation"
    elif approval == "pending_api":
        # API mode: workflow ends here, admin will approve/reject via API
        return END
    else:
        return "denial"


def route_after_reservation(state: ParkingState) -> Literal["file_recording", "denial"]:
    return "file_recording" if state.get("reservation_success") else "denial"


# =============================================================
# Node 3: Reservation (Direct SQL — no LLM)
# =============================================================

def reservation_node(state: ParkingState) -> dict:
    """Find an available spot (if needed) and reserve it via direct SQL UPDATE."""
    details = json.loads(state["reservation_details"])

    # If no valid parking_id, find an available spot directly
    parking_id = details.get("parking_id")
    if not isinstance(parking_id, int):
        parking_type = details.get("parking_type", "Standard")
        available_result = find_available_spot.invoke({"parking_type": parking_type})

        try:
            details["parking_id"] = int(available_result)
        except (ValueError, TypeError):
            msg = f"No available {parking_type} parking spots found."
            return {
                "messages": [AIMessage(content=msg)],
                "final_response": msg,
                "reservation_success": False,
            }

    # Execute reservation via direct SQL
    result = reserve_parking_space.invoke(json.dumps(details))
    result_str = str(result).lower()

    if "confirmed" in result_str:
        return {
            "messages": [AIMessage(content=str(result))],
            "reservation_details": json.dumps(details),
            "reservation_success": True,
        }
    else:
        return {
            "messages": [AIMessage(content=str(result))],
            "final_response": f"Reservation failed: {result}",
            "reservation_success": False,
        }


# =============================================================
# Node 4: File Recording (MCP File Agent)
# =============================================================

async def file_recording_node(state: ParkingState) -> dict:
    """Append approved reservation to approved_reservations.txt via MCP."""
    details = json.loads(state["reservation_details"])

    customer_name = state.get("customer_name", "N/A")
    car_number = state.get("car_number", "N/A")
    parking_id = details.get("parking_id", "N/A")
    parking_type = details.get("parking_type", "N/A")
    start_time = details.get("start_time", "N/A")
    end_time = details.get("end_time", "N/A")
    approval_time = datetime.now().isoformat(timespec="seconds")

    reservation_line = (
        f"{customer_name} | {car_number} | "
        f"Parking #{parking_id} ({parking_type}) | "
        f"{start_time} - {end_time} | "
        f"Approved: {approval_time}"
    )
    result = await append_reservation.ainvoke(reservation_line)
    return {"messages": [AIMessage(content=str(result))]}


# =============================================================
# Successful Reservation Node
# =============================================================

def succesfull_reservation_node(state: ParkingState) -> dict:
    """Format and return reservation confirmation details."""
    details = json.loads(state["reservation_details"])

    customer_name = state.get("customer_name", "N/A")
    car_number = state.get("car_number", "N/A")
    parking_id = details.get("parking_id", "N/A")
    parking_type = details.get("parking_type", "N/A")
    start_time = details.get("start_time", "N/A")
    end_time = details.get("end_time", "N/A")
    total_price = details.get("total_price", "N/A")

    msg = (
        f"Reservation confirmed!\n"
        f"  Customer: {customer_name}\n"
        f"  Car Number: {car_number}\n"
        f"  Parking ID: {parking_id}\n"
        f"  Type: {parking_type}\n"
        f"  From: {start_time}\n"
        f"  To:   {end_time}\n"
        f"  Total: ${total_price}"
    )

    return {
        "messages": [AIMessage(content=msg)],
        "final_response": msg,
    }


# =============================================================
# Denial Node
# =============================================================

def denial_node(state: ParkingState) -> dict:
    """Handle reservation denial."""
    msg = "Reservation cancelled. Let me know if you need anything else."
    return {
        "messages": [AIMessage(content=msg)],
        "final_response": msg,
    }
