from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FeedbackEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    text: str
    created_at: datetime
