import logging
import os
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.api.schemas import Category

logger = logging.getLogger(__name__)
ML_URL = os.getenv("ML_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")
ML_TIMEOUT = float(os.getenv("ML_TIMEOUT_SECONDS", "2"))


class Prediction(BaseModel):
    category: Category
    confidence: float | None = Field(default=None, ge=0, le=1, strict=True)
    model_version: str = Field(min_length=1)
    classification_source: Literal["model"] = "model"


def classify_ticket(title: str, description: str) -> Prediction | None:
    try:
        response = httpx.post(
            f"{ML_URL}/predict",
            json={"title": title, "description": description},
            timeout=ML_TIMEOUT,
        )
        response.raise_for_status()
        result = response.json()
        if isinstance(result, dict) and result.get("classification_source") == "fallback":
            return None
        prediction = Prediction.model_validate(result)
        if prediction.category != "Unclassified":
            return prediction
    except (httpx.HTTPError, ValidationError, ValueError) as error:
        logger.warning("Ticket classification unavailable (%s); keeping fallback", type(error).__name__)
    return None
