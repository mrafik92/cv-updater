from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel, ConfigDict


class JobInput(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="allow")

    title: str | None = None
    company: str | None = None
    description: str
