import os
import json
from datetime import datetime
from sqlalchemy import create_engine, text
from langchain.tools import tool
from dotenv import load_dotenv
load_dotenv()

VALID_TYPES = {"Standard", "Premium", "Rooftop", "Oversized", "Motorcycle"}

engine = create_engine(os.getenv("WRITER_CONNECTION_STRING"))


@tool
def reserve_parking_space(request: str) -> str:
    """Reserve a parking space by updating it in the database.

    Use for: creating new parking reservations only.

    Input: JSON object with reservation details:
        - parking_type: Type of parking (Standard/Premium/Rooftop/Oversized/Motorcycle)
        - parking_id: ID of the parking space to reserve
        - start_time: Reservation start (ISO 8601 format)
        - end_time: Reservation end (ISO 8601 format)

    Returns: Confirmation message or validation error
    """
    try:
        details = json.loads(request)
    except (json.JSONDecodeError, TypeError):
        return "Invalid input: expected a JSON object with parking_type, parking_id, start_time, end_time."

    parking_id = details.get("parking_id")
    parking_type = details.get("parking_type")
    start_time = details.get("start_time")
    end_time = details.get("end_time")

    # Validate parking_id
    if not isinstance(parking_id, int) or parking_id <= 0:
        return "Invalid parking_id: must be a positive integer."

    # Validate parking_type
    if parking_type not in VALID_TYPES:
        return f"Invalid parking_type: must be one of {', '.join(sorted(VALID_TYPES))}."

    # Validate timestamps
    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
    except (ValueError, TypeError):
        return "Invalid timestamps: start_time and end_time must be valid ISO 8601 format."

    if end_dt <= start_dt:
        return "Invalid time range: end_time must be after start_time."

    with engine.connect() as conn:
        # Verify spot exists, is available, and matches type
        row = conn.execute(
            text(
                "SELECT parking_id, parking_type, space_availability "
                "FROM parking.parking_lots WHERE parking_id = :id"
            ),
            {"id": parking_id},
        ).fetchone()

        if row is None:
            return f"Parking space #{parking_id} does not exist."

        if row[1] != parking_type:
            return f"Parking space #{parking_id} is not of type {parking_type}."

        if not row[2]:
            return f"Parking space #{parking_id} is not available or already reserved."

        # Execute reservation UPDATE
        result = conn.execute(
            text(
                "UPDATE parking.parking_lots "
                "SET space_availability = FALSE, "
                "    reservation_start = :start, "
                "    reservation_end = :end "
                "WHERE parking_id = :id AND space_availability = TRUE"
            ),
            {"id": parking_id, "start": start_time, "end": end_time},
        )
        conn.commit()

        if result.rowcount == 1:
            return f"Reservation confirmed for parking space #{parking_id} from {start_time} to {end_time}."
        else:
            return f"Parking space #{parking_id} is not available or already reserved."
