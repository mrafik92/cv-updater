from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


ResumeJSON = dict[str, Any]


class RRBaseModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class ResumeBasics(RRBaseModel):
    name: str | None = None
    email: str | None = None
    headline: str | None = None
    phone: str | None = None
    location: dict[str, Any] | None = None
    url: str | None = None
    summary: str | None = None
    photo: str | None = None
    profiles: list[dict[str, Any]] = Field(default_factory=list)


class ResumeSectionItem(RRBaseModel):
    id: str | None = None
    visible: bool | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class ResumeSection(RRBaseModel):
    name: str | None = None
    columns: int | None = None
    visible: bool | None = None
    items: list[ResumeSectionItem] = Field(default_factory=list)


class Resume(RRBaseModel):
    basics: ResumeBasics | None = None
    sections: dict[str, ResumeSection] = Field(default_factory=dict)
