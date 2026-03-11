import os
import asyncio
import uuid
import json
import httpx
import streamlit as st
from datetime import datetime, date, time, timedelta
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage

load_dotenv()

# Import the parking graph
from src.workflow.workflow import parking_graph

# API base URL for reservation submissions
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="Stargate Parking",
    page_icon="🅿️",
    layout="centered",
)

st.title("🅿️ Stargate Parking Reservation")
st.caption("Ask questions about parking or make a reservation")


def init_session_state():
    """Initialize session state variables."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "awaiting_customer_info" not in st.session_state:
        st.session_state.awaiting_customer_info = False
    if "reservation_details" not in st.session_state:
        st.session_state.reservation_details = None
    if "pending_reservation_id" not in st.session_state:
        st.session_state.pending_reservation_id = None


def display_chat_history():
    """Display all messages in the chat history."""
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


async def process_user_input(user_input: str) -> dict:
    """Process user input through the LangGraph workflow."""
    config = {"configurable": {"thread_id": st.session_state.thread_id}}

    result = await parking_graph.ainvoke(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
    )

    return result


def submit_reservation_to_api(
    reservation_details: dict,
    customer_name: str,
    car_number: str,
) -> dict:
    """Submit a pending reservation to the Admin API."""
    # Normalize parking_type to title case (e.g., "premium" -> "Premium")
    parking_type = reservation_details.get("parking_type", "")
    if parking_type:
        parking_type = parking_type.strip().title()

    # Handle alternative field names for start/end times
    start_time = (
        reservation_details.get("start_time") or
        reservation_details.get("reservation_start") or
        reservation_details.get("start") or
        reservation_details.get("from")
    )
    end_time = (
        reservation_details.get("end_time") or
        reservation_details.get("reservation_end") or
        reservation_details.get("end") or
        reservation_details.get("to")
    )

    # Validate required fields
    if not start_time or not end_time:
        return {
            "error": "Missing required fields: start_time and end_time must be provided. "
                     "Please specify the reservation period (e.g., 'from 2025-06-01 to 2025-06-02').",
            "payload": reservation_details,
        }

    payload = {
        "parking_id": reservation_details.get("parking_id"),
        "parking_type": parking_type,
        "start_time": start_time,
        "end_time": end_time,
        "total_price": reservation_details.get("total_price"),
        "customer_name": customer_name,
        "car_number": car_number,
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{API_BASE_URL}/reservations/request",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        # Get detailed error message from response body
        try:
            error_detail = e.response.json()
            return {"error": str(error_detail), "payload": payload}
        except Exception:
            return {"error": str(e), "payload": payload}
    except httpx.HTTPError as e:
        return {"error": str(e), "payload": payload}


def check_reservation_status(reservation_id: str) -> dict:
    """Check the status of a pending reservation."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{API_BASE_URL}/reservations/{reservation_id}/status"
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        return {"error": str(e)}


def render_customer_info_form():
    """Render the customer information form for reservation submission."""
    st.markdown("---")
    st.subheader("Complete Your Reservation")

    details = st.session_state.reservation_details

    # Get existing values or empty strings
    existing_start = (
        details.get("start_time") or
        details.get("reservation_start") or
        details.get("start") or
        details.get("from") or
        ""
    )
    existing_end = (
        details.get("end_time") or
        details.get("reservation_end") or
        details.get("end") or
        details.get("to") or
        ""
    )

    # Display reservation summary
    with st.expander("📋 Reservation Details", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Type:** {details.get('parking_type', 'N/A')}")
            st.markdown(f"**Spot ID:** {details.get('parking_id') or 'Auto-assign'}")
        with col2:
            st.markdown(f"**From:** {existing_start or 'Not specified'}")
            st.markdown(f"**To:** {existing_end or 'Not specified'}")
        if details.get("total_price"):
            st.markdown(f"**Total Price:** ${details.get('total_price', 0):.2f}")

    # Debug: Show raw details
    with st.expander("Debug: Raw reservation data"):
        st.json(details)

    # Parse existing dates/times if available
    def parse_datetime(dt_str):
        """Parse ISO datetime string to date and time objects."""
        if not dt_str:
            return None, None
        try:
            dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            return dt.date(), dt.time()
        except (ValueError, AttributeError):
            return None, None

    start_date_default, start_time_default = parse_datetime(existing_start)
    end_date_default, end_time_default = parse_datetime(existing_end)

    # Set defaults if not parsed
    today = date.today()
    default_start_time = time(9, 0)  # 9:00 AM
    default_end_time = time(18, 0)   # 6:00 PM

    # Show warning if times are missing
    if not existing_start or not existing_end:
        st.info("📅 Please select your reservation dates and times below.")

    # Customer info form
    with st.form("customer_info_form"):
        st.subheader("👤 Customer Information")
        col1, col2 = st.columns(2)
        with col1:
            customer_name = st.text_input(
                "Your Name",
                placeholder="John Doe",
                help="Enter your full name",
            )
        with col2:
            car_number = st.text_input(
                "Car Number / License Plate",
                placeholder="ABC-1234",
                help="Enter your vehicle's license plate",
            )

        st.subheader("📅 Reservation Period")

        # Start date/time
        st.markdown("**Start**")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=start_date_default or today,
                min_value=today,
                help="Select the start date",
            )
        with col2:
            start_time_input = st.time_input(
                "Start Time",
                value=start_time_default or default_start_time,
                help="Select the start time",
                step=timedelta(minutes=30),
            )

        # End date/time
        st.markdown("**End**")
        col1, col2 = st.columns(2)
        with col1:
            end_date = st.date_input(
                "End Date",
                value=end_date_default or today,
                min_value=today,
                help="Select the end date",
            )
        with col2:
            end_time_input = st.time_input(
                "End Time",
                value=end_time_default or default_end_time,
                help="Select the end time",
                step=timedelta(minutes=30),
            )

        st.markdown("---")
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            submit = st.form_submit_button("✅ Submit Reservation", type="primary", use_container_width=True)
        with col3:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submit:
            if not customer_name or not car_number:
                st.error("Please fill in your name and car number.")
            else:
                # Combine date and time into ISO format strings
                start_datetime = datetime.combine(start_date, start_time_input)
                end_datetime = datetime.combine(end_date, end_time_input)

                # Validate end is after start
                if end_datetime <= start_datetime:
                    st.error("End date/time must be after start date/time.")
                else:
                    # Update details with form values
                    updated_details = st.session_state.reservation_details.copy()
                    updated_details["start_time"] = start_datetime.isoformat()
                    updated_details["end_time"] = end_datetime.isoformat()

                    with st.spinner("Submitting reservation..."):
                        result = submit_reservation_to_api(
                            updated_details,
                            customer_name,
                            car_number,
                        )

                    if "error" in result:
                        st.error(f"Failed to submit reservation: {result['error']}")
                        if "payload" in result:
                            with st.expander("Debug: Sent payload"):
                                st.json(result["payload"])
                    else:
                        st.session_state.pending_reservation_id = result.get("id")
                        st.session_state.awaiting_customer_info = False
                        st.session_state.reservation_details = None

                        # Add confirmation message to chat
                        confirmation_msg = (
                            f"✅ **Reservation submitted successfully!**\n\n"
                            f"- **Reservation ID:** `{result.get('id')}`\n"
                            f"- **Status:** Pending admin approval\n\n"
                            f"An administrator will review your request. "
                            f"You can check the status using the reservation ID."
                        )
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": confirmation_msg,
                        })
                        st.rerun()

        if cancel:
            st.session_state.awaiting_customer_info = False
            st.session_state.reservation_details = None
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Reservation cancelled. How else can I help you?",
            })
            st.rerun()


def render_status_checker():
    """Render the reservation status checker in the sidebar."""
    with st.sidebar:
        st.subheader("Check Reservation Status")

        reservation_id = st.text_input(
            "Reservation ID",
            value=st.session_state.pending_reservation_id or "",
            placeholder="Enter reservation ID",
        )

        if st.button("Check Status"):
            if reservation_id:
                with st.spinner("Checking status..."):
                    status = check_reservation_status(reservation_id)

                if "error" in status:
                    st.error(f"Error: {status['error']}")
                else:
                    status_emoji = {
                        "pending": "⏳",
                        "approved": "✅",
                        "rejected": "❌",
                    }.get(status.get("status"), "❓")

                    st.info(
                        f"{status_emoji} **Status:** {status.get('status', 'Unknown').upper()}\n\n"
                        f"**Updated:** {status.get('updated_at', 'N/A')}"
                    )

                    if status.get("admin_notes"):
                        st.caption(f"Admin notes: {status['admin_notes']}")
            else:
                st.warning("Please enter a reservation ID.")


def main():
    """Main application entry point."""
    init_session_state()

    # Sidebar for status checking
    render_status_checker()

    # Display chat history
    display_chat_history()

    # Show customer info form if awaiting
    if st.session_state.awaiting_customer_info:
        render_customer_info_form()
    else:
        # Chat input
        if user_input := st.chat_input("Ask about parking or request a reservation..."):
            # Add user message to chat
            st.session_state.messages.append({"role": "user", "content": user_input})

            with st.chat_message("user"):
                st.markdown(user_input)

            # Process through LangGraph
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        result = asyncio.run(process_user_input(user_input))

                        # Get the assistant's response
                        assistant_response = result.get("final_response", "")
                        if not assistant_response and result.get("messages"):
                            # Get last AI message
                            for msg in reversed(result["messages"]):
                                if hasattr(msg, "content") and msg.type == "ai":
                                    assistant_response = msg.content
                                    break

                        # Check if this is a reservation request
                        reservation_details = result.get("reservation_details", "")
                        if reservation_details:
                            try:
                                details = json.loads(reservation_details)
                                st.session_state.reservation_details = details
                                st.session_state.awaiting_customer_info = True

                                # Clean response (remove the tag)
                                clean_response = assistant_response
                                if "<<<RESERVATION:" in clean_response:
                                    clean_response = clean_response.split("<<<RESERVATION:")[0].strip()
                                elif "<<<INFO>>>" in clean_response:
                                    clean_response = clean_response.replace("<<<INFO>>>", "").strip()

                                st.markdown(clean_response)
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": clean_response,
                                })
                                st.rerun()
                            except json.JSONDecodeError:
                                st.markdown(assistant_response)
                                st.session_state.messages.append({
                                    "role": "assistant",
                                    "content": assistant_response,
                                })
                        else:
                            # Clean response for info queries
                            clean_response = assistant_response
                            if "<<<INFO>>>" in clean_response:
                                clean_response = clean_response.replace("<<<INFO>>>", "").strip()

                            st.markdown(clean_response)
                            st.session_state.messages.append({
                                "role": "assistant",
                                "content": clean_response,
                            })

                    except Exception as e:
                        error_msg = f"Sorry, an error occurred: {str(e)}"
                        st.error(error_msg)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": error_msg,
                        })


if __name__ == "__main__":
    main()
