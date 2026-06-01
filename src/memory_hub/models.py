from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

MemoryType = Literal[
    "fact",
    "task",
    "decision",
    "note",
    "project",
    "credential_ref",
    "session_summary",
]
MemoryStatus = Literal["active", "stale", "archived", "done", "blocked"]


class MemoryCreate(BaseModel):
    type: MemoryType = "note"
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    project: str | None = None
    tags: list[str] = Field(default_factory=list)
    source_agent: str = "unknown"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    status: MemoryStatus = "active"
    expires_at: datetime | None = None


class MemoryUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    project: str | None = None
    tags: list[str] | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    status: MemoryStatus | None = None
    expires_at: datetime | None = None


class Memory(MemoryCreate):
    id: str
    created_at: datetime
    updated_at: datetime


class SearchResult(BaseModel):
    memory: Memory
    score: float = 0.0
    snippet: str | None = None
