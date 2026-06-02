from __future__ import annotations

from typing import ClassVar

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FeedbackEntry(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow")

    text: str
    created_at: datetime
