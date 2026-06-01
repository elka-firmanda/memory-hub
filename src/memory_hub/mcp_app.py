from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .db import MemoryDB

mcp = FastMCP(
    name="Memory Hub",
    stateless_http=True,
    json_response=True,
    host="0.0.0.0",
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["127.0.0.1:*", "localhost:*", "10.10.20.23:*"],
        allowed_origins=["http://127.0.0.1:*", "http://localhost:*", "http://10.10.20.23:*"],
    ),
)
mcp.settings.streamable_http_path = "/"


def get_db() -> MemoryDB:
    path = os.getenv("MEMORY_HUB_DB", os.path.expanduser("~/.memory-hub/memoryhub.sqlite"))
    db = MemoryDB(path)
    db.init()
    return db


@mcp.tool()
def memory_write(
    title: str,
    content: str,
    project: str | None = None,
    type: str = "note",
    tags: list[str] | None = None,
    source_agent: str = "mcp",
    confidence: float = 1.0,
    status: str = "active",
) -> dict[str, Any]:
    """Write a memory to the central Memory Hub."""
    memory = get_db().add_memory(
        type=type,
        title=title,
        content=content,
        project=project,
        tags=tags or [],
        source_agent=source_agent,
        confidence=confidence,
        status=status,
    )
    return memory.model_dump(mode="json")


@mcp.tool()
def memory_search(
    q: str,
    project: str | None = None,
    type: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Search central memories with SQLite FTS5."""
    results = get_db().search(q, project=project, type=type, limit=limit)
    return [result.model_dump(mode="json") for result in results]


@mcp.tool()
def memory_list(
    project: str | None = None,
    type: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List recent memories, optionally filtered by project/type/status."""
    memories = get_db().list_memories(project=project, type=type, status=status, limit=limit)
    return [memory.model_dump(mode="json") for memory in memories]


@mcp.tool()
def memory_read(memory_id: str) -> dict[str, Any] | None:
    """Read one memory by ID."""
    memory = get_db().get_memory(memory_id)
    return memory.model_dump(mode="json") if memory else None


@mcp.tool()
def memory_update(
    memory_id: str,
    title: str | None = None,
    content: str | None = None,
    project: str | None = None,
    tags_json: str | None = None,
    confidence: float | None = None,
    status: str | None = None,
) -> dict[str, Any] | None:
    """Update a memory. Pass tags_json as a JSON array string when updating tags."""
    updates: dict[str, Any] = {}
    for key, value in {
        "title": title,
        "content": content,
        "project": project,
        "confidence": confidence,
        "status": status,
    }.items():
        if value is not None:
            updates[key] = value
    if tags_json is not None:
        updates["tags"] = json.loads(tags_json)
    memory = get_db().update_memory(memory_id, updates, agent="mcp")
    return memory.model_dump(mode="json") if memory else None


@mcp.tool()
def memory_context(project: str, goal: str | None = None, max_items: int = 20) -> str:
    """Generate a compact markdown context pack for a project and optional goal."""
    return get_db().context_pack(project=project, goal=goal, max_items=max_items)


class BearerAuthASGIMiddleware:
    """Small ASGI middleware to protect mounted MCP transport with MEMORY_HUB_TOKEN."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        token = os.getenv("MEMORY_HUB_TOKEN")
        if token and scope.get("type") == "http":
            headers = {k.decode("latin1").lower(): v.decode("latin1") for k, v in scope.get("headers", [])}
            if headers.get("authorization") != f"Bearer {token}":
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [(b"content-type", b"application/json")],
                    }
                )
                await send({"type": "http.response.body", "body": b'{"detail":"Invalid or missing bearer token"}'})
                return
        await self.app(scope, receive, send)


def app():
    return BearerAuthASGIMiddleware(mcp.streamable_http_app())
