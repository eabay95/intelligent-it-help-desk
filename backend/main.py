import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.auth import router as auth_router
from app.api.tickets import router as tickets_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    with httpx.Client(timeout=5.0) as client:
        app.state.auth_http = client
        yield


api = FastAPI(title="Intelligent IT Help Desk API", version="0.1.0", lifespan=lifespan)
api.include_router(auth_router)
api.include_router(tickets_router)


@api.exception_handler(SQLAlchemyError)
async def database_error(_request: Request, exc: SQLAlchemyError):
    logger.error("Ticket database operation failed (%s)", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "Ticket storage is unavailable."})


@api.get("/")
async def root():
    return {"message": "Hello from backend"}


@api.get("/health")
def health():
    return {"status": "ok", "service": "Intelligent IT Help Desk API"}


# Let approved browsers receive the status of unexpected server errors too.
app = CORSMiddleware(
    api,
    allow_origins=[origin.strip() for origin in os.getenv(
        "FRONTEND_URL", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
)
