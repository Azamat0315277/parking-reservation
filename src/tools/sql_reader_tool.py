import os
from sqlalchemy import create_engine, text
from langchain.tools import tool
from dotenv import load_dotenv
load_dotenv()

engine = create_engine(os.getenv("READER_CONNECTION_STRING"))
SCHEMA = os.getenv("SCHEMA", "parking")


@tool
def check_availability(parking_type: str = None) -> str:
    """Check parking space availability, optionally filtered by type.

    Use for: "How many spots are available?", "Are there Premium spots free?",
    occupancy stats, availability counts by type.

    Args:
        parking_type: Optional filter — Standard, Premium, Rooftop, Oversized, or Motorcycle.
                      If omitted, returns counts for all types.
    """
    with engine.connect() as conn:
        if parking_type:
            rows = conn.execute(
                text(
                    f"SELECT parking_type, COUNT(*) as available "
                    f"FROM {SCHEMA}.parking_lots "
                    f"WHERE space_availability = TRUE AND parking_type = :ptype "
                    f"GROUP BY parking_type"
                ),
                {"ptype": parking_type},
            ).fetchall()
        else:
            rows = conn.execute(
                text(
                    f"SELECT parking_type, COUNT(*) as available "
                    f"FROM {SCHEMA}.parking_lots "
                    f"WHERE space_availability = TRUE "
                    f"GROUP BY parking_type ORDER BY parking_type"
                )
            ).fetchall()

        if not rows:
            if parking_type:
                return f"No available {parking_type} parking spots."
            return "No available parking spots."

        lines = [f"{row[0]}: {row[1]} available" for row in rows]
        total = sum(row[1] for row in rows)
        lines.append(f"Total: {total} available")
        return "\n".join(lines)


@tool
def get_pricing(parking_type: str = None) -> str:
    """Get parking pricing information, optionally filtered by type.

    Use for: "What's the price?", "How much does Premium cost?", pricing lookups.

    Args:
        parking_type: Optional filter — Standard, Premium, Rooftop, Oversized, or Motorcycle.
                      If omitted, returns pricing for all types.
    """
    with engine.connect() as conn:
        if parking_type:
            rows = conn.execute(
                text(
                    f"SELECT DISTINCT parking_type, price "
                    f"FROM {SCHEMA}.parking_lots "
                    f"WHERE parking_type = :ptype"
                ),
                {"ptype": parking_type},
            ).fetchall()
        else:
            rows = conn.execute(
                text(
                    f"SELECT DISTINCT parking_type, price "
                    f"FROM {SCHEMA}.parking_lots "
                    f"ORDER BY price DESC"
                )
            ).fetchall()

        if not rows:
            return "No pricing information found."

        lines = [f"{row[0]}: ${row[1]}/hr" for row in rows]
        return "\n".join(lines)


@tool
def get_spot_details(parking_id: int) -> str:
    """Get full details for a specific parking spot by ID.

    Use for: "What's the status of spot #42?", "Is spot 5 available?",
    checking a specific spot's type, price, and reservation times.

    Args:
        parking_id: The parking spot ID number.
    """
    with engine.connect() as conn:
        row = conn.execute(
            text(
                f"SELECT parking_id, parking_type, space_availability, "
                f"reservation_start, reservation_end, price "
                f"FROM {SCHEMA}.parking_lots WHERE parking_id = :id"
            ),
            {"id": parking_id},
        ).fetchone()

        if row is None:
            return f"Parking spot #{parking_id} does not exist."

        status = "Available" if row[2] else "Reserved"
        result = (
            f"Spot #{row[0]}: {row[1]} — {status}, ${row[5]}/hr"
        )
        if not row[2] and row[3] and row[4]:
            result += f"\n  Reserved: {row[3]} to {row[4]}"
        return result


@tool
def find_available_spot(parking_type: str) -> str:
    """Find one available parking spot of the given type.

    Use for: finding a free spot before making a reservation.

    Args:
        parking_type: Required — Standard, Premium, Rooftop, Oversized, or Motorcycle.

    Returns: The parking_id of an available spot, or a message if none available.
    """
    with engine.connect() as conn:
        row = conn.execute(
            text(
                f"SELECT parking_id FROM {SCHEMA}.parking_lots "
                f"WHERE parking_type = :ptype AND space_availability = TRUE "
                f"LIMIT 1"
            ),
            {"ptype": parking_type},
        ).fetchone()

        if row is None:
            return f"No available {parking_type} parking spots found."

        return str(row[0])
