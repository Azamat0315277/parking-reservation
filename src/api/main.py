from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.api.routers import reservations

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Parking Reservation Admin API...")
    yield
    print("Shutting down...")


app = FastAPI(
    title="Stargate Parking Reservation Admin API",
    description="Admin approval API for parking reservations. "
                "Admins can view pending requests and approve/reject them.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for admin dashboard / Swagger UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(reservations.router)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
