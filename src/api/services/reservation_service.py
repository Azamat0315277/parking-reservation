import os
import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from filelock import FileLock

from src.tools.parking_reservation_tool import reserve_parking_space
from src.tools.sql_reader_tool import find_available_spot

# Configure logging
logger = logging.getLogger(__name__)

# Path to pending reservations JSON file
BASE_DIR = Path(__file__).parent.parent.parent
PENDING_FILE = BASE_DIR / "customer_data" / "pending_reservations.json"
APPROVED_FILE = BASE_DIR / "customer_data" / "approved_reservations.txt"
LOCK_FILE = PENDING_FILE.with_suffix(".lock")


def _load_pending() -> list[dict]:
    """Load pending reservations from JSON file."""
    if not PENDING_FILE.exists():
        return []
    try:
        with open(PENDING_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _save_pending(reservations: list[dict]) -> None:
    """Save pending reservations to JSON file."""
    PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PENDING_FILE, "w") as f:
        json.dump(reservations, f, indent=2)


class ReservationService:
    """Service for managing pending reservations via file storage."""

    def create_pending_reservation(
        self,
        parking_id: Optional[int],
        parking_type: str,
        start_time: str,
        end_time: str,
        customer_name: str,
        car_number: str,
        total_price: Optional[float] = None,
    ) -> dict:
        """Create a new pending reservation.

        If parking_id is not provided, automatically finds an available spot.
        """
        logger.info(f"Creating reservation: parking_id={parking_id}, type={parking_type}, "
                    f"start={start_time}, end={end_time}, customer={customer_name}")

        # If no parking_id provided, find an available spot
        if parking_id is None:
            logger.info(f"No parking_id provided, finding available {parking_type} spot...")
            result = find_available_spot.invoke(parking_type)
            logger.info(f"find_available_spot result: {result}")
            if "available" in result.lower() and "spot" in result.lower():
                # Extract parking_id from result like "Spot 5 (Premium) is available"
                import re
                match = re.search(r"Spot\s+(\d+)", result)
                if match:
                    parking_id = int(match.group(1))
                    logger.info(f"Found available spot: {parking_id}")
                else:
                    logger.error(f"Could not parse spot ID from: {result}")
                    raise ValueError(f"Could not find available {parking_type} spot")
            else:
                logger.error(f"No available spots: {result}")
                raise ValueError(f"No available {parking_type} spots: {result}")

        with FileLock(LOCK_FILE):
            reservations = _load_pending()

            now = datetime.now().isoformat(timespec="seconds")
            reservation = {
                "id": str(uuid.uuid4()),
                "parking_id": parking_id,
                "parking_type": parking_type,
                "start_time": start_time,
                "end_time": end_time,
                "total_price": total_price,
                "customer_name": customer_name,
                "car_number": car_number,
                "status": "pending",
                "created_at": now,
                "updated_at": now,
                "admin_notes": None,
            }

            reservations.append(reservation)
            _save_pending(reservations)

            return reservation

    def get_pending_reservations(self) -> list[dict]:
        """Get all pending reservations for admin review."""
        with FileLock(LOCK_FILE):
            reservations = _load_pending()
            return [r for r in reservations if r["status"] == "pending"]

    def get_all_reservations(self) -> list[dict]:
        """Get all reservations (any status)."""
        with FileLock(LOCK_FILE):
            return _load_pending()

    def get_reservation_by_id(self, reservation_id: str) -> Optional[dict]:
        """Get a specific reservation by ID."""
        with FileLock(LOCK_FILE):
            reservations = _load_pending()
            for r in reservations:
                if r["id"] == reservation_id:
                    return r
            return None

    def approve_reservation(self, reservation_id: str, admin_notes: Optional[str] = None) -> dict:
        """Approve a pending reservation and execute the actual booking."""
        with FileLock(LOCK_FILE):
            reservations = _load_pending()

            reservation = None
            for r in reservations:
                if r["id"] == reservation_id:
                    reservation = r
                    break

            if not reservation:
                raise ValueError("Reservation not found")

            if reservation["status"] != "pending":
                raise ValueError(f"Reservation already processed: {reservation['status']}")

            # Execute actual reservation in database
            request_json = json.dumps({
                "parking_id": reservation["parking_id"],
                "parking_type": reservation["parking_type"],
                "start_time": reservation["start_time"],
                "end_time": reservation["end_time"],
            })

            result = reserve_parking_space.invoke(request_json)
            result_str = str(result).lower()

            if "confirmed" not in result_str:
                # Reservation failed - mark as rejected
                reservation["status"] = "rejected"
                reservation["admin_notes"] = f"Database reservation failed: {result}"
                reservation["updated_at"] = datetime.now().isoformat(timespec="seconds")
                _save_pending(reservations)
                raise ValueError(f"Reservation failed: {result}")

            # Update status to approved
            reservation["status"] = "approved"
            reservation["admin_notes"] = admin_notes
            reservation["updated_at"] = datetime.now().isoformat(timespec="seconds")
            _save_pending(reservations)

            # Append to approved_reservations.txt
            self._append_to_approved_file(reservation)

            return reservation

    def reject_reservation(self, reservation_id: str, admin_notes: Optional[str] = None) -> dict:
        """Reject a pending reservation."""
        with FileLock(LOCK_FILE):
            reservations = _load_pending()

            reservation = None
            for r in reservations:
                if r["id"] == reservation_id:
                    reservation = r
                    break

            if not reservation:
                raise ValueError("Reservation not found")

            if reservation["status"] != "pending":
                raise ValueError(f"Reservation already processed: {reservation['status']}")

            reservation["status"] = "rejected"
            reservation["admin_notes"] = admin_notes
            reservation["updated_at"] = datetime.now().isoformat(timespec="seconds")
            _save_pending(reservations)

            return reservation

    def _append_to_approved_file(self, reservation: dict) -> None:
        """Append approved reservation to the approved_reservations.txt file."""
        line = (
            f"{reservation['customer_name']} | {reservation['car_number']} | "
            f"Parking #{reservation['parking_id']} ({reservation['parking_type']}) | "
            f"{reservation['start_time']} - {reservation['end_time']} | "
            f"Approved: {reservation['updated_at']}\n"
        )
        with open(APPROVED_FILE, "a") as f:
            f.write(line)
