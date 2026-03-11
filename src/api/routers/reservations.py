import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional

from src.api.models.schemas import (
    ReservationRequest,
    ReservationResponse,
    ApprovalRequest,
    StatusCheckResponse,
)
from src.api.services.reservation_service import ReservationService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reservations", tags=["reservations"])


def get_service() -> ReservationService:
    return ReservationService()


@router.post("/request", response_model=ReservationResponse)
async def create_reservation_request(
    request: ReservationRequest,
    service: ReservationService = Depends(get_service),
):
    """
    Create a new pending reservation request.
    The agent calls this endpoint when a user wants to reserve a spot.
    """
    logger.info(f"Received reservation request: {request.model_dump()}")
    try:
        reservation = service.create_pending_reservation(
            parking_id=request.parking_id,
            parking_type=request.parking_type,
            start_time=request.start_time,
            end_time=request.end_time,
            customer_name=request.customer_name,
            car_number=request.car_number,
            total_price=request.total_price,
        )
        logger.info(f"Reservation created successfully: {reservation['id']}")
        return reservation
    except Exception as e:
        logger.error(f"Failed to create reservation: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/pending", response_model=list[ReservationResponse])
async def list_pending_reservations(
    service: ReservationService = Depends(get_service),
):
    """
    List all pending reservations awaiting admin approval.
    Admin dashboard calls this to show the approval queue.
    """
    return service.get_pending_reservations()


@router.get("/all", response_model=list[ReservationResponse])
async def list_all_reservations(
    service: ReservationService = Depends(get_service),
):
    """
    List all reservations (pending, approved, rejected).
    """
    return service.get_all_reservations()


@router.post("/{reservation_id}/approve", response_model=ReservationResponse)
async def approve_reservation(
    reservation_id: str,
    request: Optional[ApprovalRequest] = None,
    service: ReservationService = Depends(get_service),
):
    """
    Admin approves a pending reservation.
    This triggers the actual parking spot reservation in the database.
    """
    try:
        notes = request.admin_notes if request else None
        result = service.approve_reservation(reservation_id, notes)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{reservation_id}/reject", response_model=ReservationResponse)
async def reject_reservation(
    reservation_id: str,
    request: Optional[ApprovalRequest] = None,
    service: ReservationService = Depends(get_service),
):
    """
    Admin rejects a pending reservation.
    """
    try:
        notes = request.admin_notes if request else None
        result = service.reject_reservation(reservation_id, notes)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{reservation_id}/status", response_model=StatusCheckResponse)
async def check_reservation_status(
    reservation_id: str,
    service: ReservationService = Depends(get_service),
):
    """
    Check the status of a reservation request.
    The agent polls this endpoint to know when admin has made a decision.
    """
    reservation = service.get_reservation_by_id(reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")
    return StatusCheckResponse(
        id=reservation["id"],
        status=reservation["status"],
        admin_notes=reservation.get("admin_notes"),
        updated_at=reservation["updated_at"],
    )
