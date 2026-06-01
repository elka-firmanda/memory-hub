from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Memory, SearchResult


class MemoryDB:
    def __init__(self, path: str | Path):
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    project TEXT,
                    tags TEXT NOT NULL DEFAULT '[]',
                    source_agent TEXT NOT NULL DEFAULT 'unknown',
                    confidence REAL NOT NULL DEFAULT 1.0,
                    status TEXT NOT NULL DEFAULT 'active',
                    expires_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    id UNINDEXED,
                    title,
                    content,
                    project,
                    tags
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    id TEXT PRIMARY KEY,
                    memory_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    before_json TEXT,
                    after_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE
                );
                """
            )

    def add_memory(
        self,
        type: str,
        title: str,
        content: str,
        project: str | None = None,
        tags: list[str] | None = None,
        source_agent: str = "unknown",
        confidence: float = 1.0,
        status: str = "active",
        expires_at: datetime | None = None,
    ) -> Memory:
        self.init()
        now = _now()
        memory_id = str(uuid.uuid4())
        tags = tags or []
        row = {
            "id": memory_id,
            "type": type,
            "title": title,
            "content": content,
            "project": project,
            "tags": json.dumps(tags),
            "source_agent": source_agent,
            "confidence": confidence,
            "status": status,
            "expires_at": _dt_to_str(expires_at),
            "created_at": now,
            "updated_at": now,
        }
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO memories
                (id, type, title, content, project, tags, source_agent, confidence, status, expires_at, created_at, updated_at)
                VALUES
                (:id, :type, :title, :content, :project, :tags, :source_agent, :confidence, :status, :expires_at, :created_at, :updated_at)
                """,
                row,
            )
            self._upsert_fts(conn, row)
            self._audit(conn, memory_id, "create", source_agent, None, row)
        loaded = self.get_memory(memory_id)
        assert loaded is not None
        return loaded

    def get_memory(self, memory_id: str) -> Memory | None:
        self.init()
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        return _row_to_memory(row) if row else None

    def list_memories(
        self,
        project: str | None = None,
        type: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Memory]:
        self.init()
        clauses: list[str] = []
        params: list[Any] = []
        if project:
            clauses.append("project = ?")
            params.append(project)
        if type:
            clauses.append("type = ?")
            params.append(type)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with self.connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM memories {where} ORDER BY updated_at DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
        return [_row_to_memory(row) for row in rows]

    def search(self, query: str, project: str | None = None, type: str | None = None, limit: int = 20) -> list[SearchResult]:
        self.init()
        clauses = ["memories_fts MATCH ?"]
        params: list[Any] = [query]
        if project:
            clauses.append("m.project = ?")
            params.append(project)
        if type:
            clauses.append("m.type = ?")
            params.append(type)
        params.append(limit)
        sql = f"""
            SELECT m.*, bm25(memories_fts) AS score,
                   snippet(memories_fts, 2, '[', ']', '…', 12) AS snippet
            FROM memories_fts
            JOIN memories m ON m.id = memories_fts.id
            WHERE {' AND '.join(clauses)}
            ORDER BY score
            LIMIT ?
        """
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [SearchResult(memory=_row_to_memory(row), score=float(row["score"]), snippet=row["snippet"]) for row in rows]

    def update_memory(self, memory_id: str, updates: dict[str, Any], agent: str = "unknown") -> Memory | None:
        self.init()
        before = self.get_memory(memory_id)
        if before is None:
            return None
        allowed = {"title", "content", "project", "tags", "confidence", "status", "expires_at"}
        clean = {k: v for k, v in updates.items() if k in allowed and v is not None}
        if not clean:
            return before
        clean["updated_at"] = _now()
        if "tags" in clean:
            clean["tags"] = json.dumps(clean["tags"])
        if isinstance(clean.get("expires_at"), datetime):
            clean["expires_at"] = _dt_to_str(clean["expires_at"])
        assignments = ", ".join(f"{key} = :{key}" for key in clean)
        clean["id"] = memory_id
        with self.connect() as conn:
            conn.execute(f"UPDATE memories SET {assignments} WHERE id = :id", clean)
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
            self._upsert_fts(conn, dict(row))
            self._audit(conn, memory_id, "update", agent, before.model_dump(mode="json"), dict(row))
        return self.get_memory(memory_id)

    def context_pack(self, project: str, goal: str | None = None, max_items: int = 20) -> str:
        self.init()
        query = goal or project
        found = self.search(query, project=project, limit=max_items)
        by_id = {result.memory.id: result.memory for result in found}
        for memory in self.list_memories(project=project, status="active", limit=max_items):
            by_id.setdefault(memory.id, memory)

        grouped: dict[str, list[Memory]] = {}
        for memory in by_id.values():
            grouped.setdefault(memory.type, []).append(memory)

        lines = [f"# Context Pack: {project}"]
        if goal:
            lines += ["", f"Goal: {goal}"]
        order = ["task", "fact", "decision", "project", "credential_ref", "session_summary", "note"]
        for type_name in order:
            items = grouped.get(type_name, [])
            if not items:
                continue
            lines += ["", f"## {type_name.replace('_', ' ').title()}s"]
            for item in sorted(items, key=lambda m: m.updated_at, reverse=True)[:max_items]:
                tag_text = f" [{', '.join(item.tags)}]" if item.tags else ""
                lines.append(f"- **{item.title}**{tag_text}: {item.content}")
        return "\n".join(lines).strip() + "\n"

    def _upsert_fts(self, conn: sqlite3.Connection, row: dict[str, Any]) -> None:
        tags = row.get("tags", "[]")
        if not isinstance(tags, str):
            tags = json.dumps(tags)
        conn.execute("DELETE FROM memories_fts WHERE id = ?", (row["id"],))
        conn.execute(
            "INSERT INTO memories_fts (id, title, content, project, tags) VALUES (?, ?, ?, ?, ?)",
            (row["id"], row["title"], row["content"], row.get("project"), tags),
        )

    def _audit(self, conn: sqlite3.Connection, memory_id: str, action: str, agent: str, before: Any, after: Any) -> None:
        conn.execute(
            "INSERT INTO audit_log (id, memory_id, action, agent, before_json, after_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), memory_id, action, agent, json.dumps(before, default=str) if before is not None else None, json.dumps(after, default=str), _now()),
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dt_to_str(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _row_to_memory(row: sqlite3.Row) -> Memory:
    data = dict(row)
    data["tags"] = json.loads(data.get("tags") or "[]")
    data["created_at"] = _parse_dt(data["created_at"])
    data["updated_at"] = _parse_dt(data["updated_at"])
    data["expires_at"] = _parse_dt(data.get("expires_at"))
    return Memory(**data)
