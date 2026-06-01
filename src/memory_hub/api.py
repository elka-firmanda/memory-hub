from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import PlainTextResponse

from .db import MemoryDB
from .models import Memory, MemoryCreate, MemoryUpdate, SearchResult

app = FastAPI(title="Memory Hub", version="0.1.0")


def get_db() -> MemoryDB:
    path = os.getenv("MEMORY_HUB_DB", str(Path.home() / ".memory-hub" / "memoryhub.sqlite"))
    db = MemoryDB(path)
    db.init()
    return db


def require_auth(authorization: str | None = Header(default=None)) -> None:
    token = os.getenv("MEMORY_HUB_TOKEN")
    if not token:
        return
    if authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")


@app.get("/health")
def health(db: MemoryDB = Depends(get_db)) -> dict[str, str]:
    return {"status": "ok", "db": str(db.path)}


@app.post("/memories", response_model=Memory)
def create_memory(payload: MemoryCreate, db: MemoryDB = Depends(get_db), _: None = Depends(require_auth)) -> Memory:
    return db.add_memory(**payload.model_dump())


@app.get("/memories", response_model=list[Memory])
def list_memories(
    project: str | None = None,
    type: str | None = None,
    status: str | None = None,
    limit: int = Query(default=50, ge=1, le=500),
    db: MemoryDB = Depends(get_db),
    _: None = Depends(require_auth),
) -> list[Memory]:
    return db.list_memories(project=project, type=type, status=status, limit=limit)


@app.get("/memories/{memory_id}", response_model=Memory)
def get_memory(memory_id: str, db: MemoryDB = Depends(get_db), _: None = Depends(require_auth)) -> Memory:
    memory = db.get_memory(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@app.patch("/memories/{memory_id}", response_model=Memory)
def update_memory(memory_id: str, payload: MemoryUpdate, db: MemoryDB = Depends(get_db), _: None = Depends(require_auth)) -> Memory:
    memory = db.update_memory(memory_id, payload.model_dump(exclude_unset=True), agent="api")
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@app.get("/search", response_model=list[SearchResult])
def search_memories(
    q: str,
    project: str | None = None,
    type: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: MemoryDB = Depends(get_db),
    _: None = Depends(require_auth),
) -> list[SearchResult]:
    return db.search(q, project=project, type=type, limit=limit)


@app.get("/context", response_class=PlainTextResponse)
def context_pack(
    project: str,
    goal: str | None = None,
    max_items: int = Query(default=20, ge=1, le=100),
    db: MemoryDB = Depends(get_db),
    _: None = Depends(require_auth),
) -> str:
    return db.context_pack(project=project, goal=goal, max_items=max_items)
