import os
import httpx
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# API base URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(
    page_title="Stargate Parking Admin",
    page_icon="🔧",
    layout="wide",
)

st.title("🔧 Stargate Parking Admin Panel")
st.caption("Review and manage parking reservation requests")


def fetch_pending_reservations() -> list:
    """Fetch all pending reservations from the API."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_BASE_URL}/reservations/pending")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        st.error(f"Failed to fetch reservations: {e}")
        return []


def fetch_all_reservations() -> list:
    """Fetch all reservations from the API."""
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(f"{API_BASE_URL}/reservations/all")
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        st.error(f"Failed to fetch reservations: {e}")
        return []


def approve_reservation(reservation_id: str, notes: str = None) -> dict:
    """Approve a reservation."""
    try:
        with httpx.Client(timeout=30.0) as client:
            payload = {"admin_notes": notes} if notes else None
            response = client.post(
                f"{API_BASE_URL}/reservations/{reservation_id}/approve",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        return {"error": str(e)}


def reject_reservation(reservation_id: str, notes: str = None) -> dict:
    """Reject a reservation."""
    try:
        with httpx.Client(timeout=10.0) as client:
            payload = {"admin_notes": notes} if notes else None
            response = client.post(
                f"{API_BASE_URL}/reservations/{reservation_id}/reject",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        return {"error": str(e)}


def render_reservation_card(reservation: dict, show_actions: bool = True):
    """Render a single reservation card."""
    status = reservation.get("status", "unknown")
    status_colors = {
        "pending": "🟡",
        "approved": "🟢",
        "rejected": "🔴",
    }
    status_icon = status_colors.get(status, "⚪")

    with st.container():
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            st.markdown(f"**Customer:** {reservation.get('customer_name', 'N/A')}")
            st.markdown(f"**Car Number:** {reservation.get('car_number', 'N/A')}")
            st.caption(f"ID: `{reservation.get('id', 'N/A')[:8]}...`")

        with col2:
            st.markdown(f"**Spot:** #{reservation.get('parking_id', 'N/A')} ({reservation.get('parking_type', 'N/A')})")
            st.markdown(f"**Period:** {reservation.get('start_time', 'N/A')} → {reservation.get('end_time', 'N/A')}")
            if reservation.get("total_price"):
                st.markdown(f"**Price:** ${reservation.get('total_price', 0):.2f}")

        with col3:
            st.markdown(f"{status_icon} **{status.upper()}**")
            st.caption(f"Created: {reservation.get('created_at', 'N/A')[:10]}")

        if show_actions and status == "pending":
            render_action_buttons(reservation)

        if reservation.get("admin_notes"):
            st.info(f"Admin notes: {reservation.get('admin_notes')}")

        st.divider()


def render_action_buttons(reservation: dict):
    """Render approve/reject buttons for a reservation."""
    reservation_id = reservation.get("id")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        notes = st.text_input(
            "Admin notes (optional)",
            key=f"notes_{reservation_id}",
            placeholder="Add a note...",
        )

    with col2:
        if st.button("✅ Approve", key=f"approve_{reservation_id}", type="primary"):
            with st.spinner("Approving..."):
                result = approve_reservation(reservation_id, notes)

            if "error" in result:
                st.error(f"Failed: {result['error']}")
            else:
                st.success("Reservation approved!")
                st.rerun()

    with col3:
        if st.button("❌ Reject", key=f"reject_{reservation_id}"):
            with st.spinner("Rejecting..."):
                result = reject_reservation(reservation_id, notes)

            if "error" in result:
                st.error(f"Failed: {result['error']}")
            else:
                st.warning("Reservation rejected.")
                st.rerun()


def render_pending_tab():
    """Render the pending reservations tab."""
    st.subheader("Pending Reservations")

    if st.button("🔄 Refresh", key="refresh_pending"):
        st.rerun()

    reservations = fetch_pending_reservations()

    if not reservations:
        st.info("No pending reservations. All caught up! 🎉")
    else:
        st.markdown(f"**{len(reservations)} reservation(s) awaiting approval**")
        st.divider()

        for reservation in reservations:
            render_reservation_card(reservation, show_actions=True)


def render_history_tab():
    """Render the reservation history tab."""
    st.subheader("Reservation History")

    if st.button("🔄 Refresh", key="refresh_history"):
        st.rerun()

    reservations = fetch_all_reservations()

    if not reservations:
        st.info("No reservations found.")
    else:
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox(
                "Filter by status",
                ["All", "pending", "approved", "rejected"],
            )
        with col2:
            sort_order = st.selectbox(
                "Sort by",
                ["Newest first", "Oldest first"],
            )

        # Apply filters
        filtered = reservations
        if status_filter != "All":
            filtered = [r for r in filtered if r.get("status") == status_filter]

        # Apply sorting
        filtered.sort(
            key=lambda x: x.get("created_at", ""),
            reverse=(sort_order == "Newest first"),
        )

        st.markdown(f"**Showing {len(filtered)} of {len(reservations)} reservation(s)**")
        st.divider()

        for reservation in filtered:
            render_reservation_card(reservation, show_actions=False)


def render_stats_sidebar():
    """Render statistics in the sidebar."""
    with st.sidebar:
        st.subheader("📊 Statistics")

        reservations = fetch_all_reservations()

        if reservations:
            pending = len([r for r in reservations if r.get("status") == "pending"])
            approved = len([r for r in reservations if r.get("status") == "approved"])
            rejected = len([r for r in reservations if r.get("status") == "rejected"])

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Pending", pending)
                st.metric("Approved", approved)
            with col2:
                st.metric("Rejected", rejected)
                st.metric("Total", len(reservations))

            if pending > 0:
                st.warning(f"⚠️ {pending} reservation(s) need attention!")
        else:
            st.info("No data available")

        st.divider()
        st.caption(f"API: {API_BASE_URL}")


def main():
    """Main application entry point."""
    render_stats_sidebar()

    # Tabs for different views
    tab1, tab2 = st.tabs(["📋 Pending Approvals", "📜 History"])

    with tab1:
        render_pending_tab()

    with tab2:
        render_history_tab()


if __name__ == "__main__":
    main()
