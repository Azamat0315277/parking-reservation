from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class ReservationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReservationRequest(BaseModel):
    """Request body for creating a new pending reservation."""
    parking_id: int = Field(..., gt=0)
    parking_type: str = Field(..., pattern="^(Standard|Premium|Rooftop|Oversized|Motorcycle)$")
    start_time: str
    end_time: str
    total_price: Optional[float] = None
    customer_name: str = Field(..., min_length=1, max_length=255)
    car_number: str = Field(..., min_length=1, max_length=50)


class ReservationResponse(BaseModel):
    """Response model for reservation details."""
    id: str
    parking_id: int
    parking_type: str
    start_time: str
    end_time: str
    total_price: Optional[float]
    customer_name: str
    car_number: str
    status: ReservationStatus
    created_at: str
    updated_at: str
    admin_notes: Optional[str] = None


class ApprovalRequest(BaseModel):
    """Request body for approve/reject actions."""
    admin_notes: Optional[str] = None


class StatusCheckResponse(BaseModel):
    """Response for status check endpoint."""
    id: str
    status: ReservationStatus
    admin_notes: Optional[str] = None
    updated_at: str
