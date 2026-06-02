from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class JobInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str | None = None
    company: str | None = None
    description: str
