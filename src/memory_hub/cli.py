from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.table import Table

from .db import MemoryDB

app = typer.Typer(help="Memory Hub CLI")
console = Console()


def _db_path() -> Path:
    return Path(os.getenv("MEMORY_HUB_DB", str(Path.home() / ".memory-hub" / "memoryhub.sqlite"))).expanduser()


def _api_url() -> str | None:
    return os.getenv("MEMORY_HUB_URL")


def _headers() -> dict[str, str]:
    token = os.getenv("MEMORY_HUB_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _db() -> MemoryDB:
    db = MemoryDB(_db_path())
    db.init()
    return db


@app.command()
def init(db: Optional[Path] = typer.Option(None, "--db", help="SQLite DB path")) -> None:
    path = db or _db_path()
    MemoryDB(path).init()
    console.print(f"✅ Initialized Memory Hub DB: {path}")


@app.command()
def add(
    content: str = typer.Argument(..., help="Memory content"),
    title: Optional[str] = typer.Option(None, "--title", "-t"),
    type: str = typer.Option("note", "--type"),
    project: Optional[str] = typer.Option(None, "--project", "-p"),
    tags: str = typer.Option("", "--tags", help="Comma-separated tags"),
    source_agent: str = typer.Option("cli", "--source-agent"),
) -> None:
    payload = {
        "type": type,
        "title": title or content[:60],
        "content": content,
        "project": project,
        "tags": [tag.strip() for tag in tags.split(",") if tag.strip()],
        "source_agent": source_agent,
    }
    if _api_url():
        response = httpx.post(f"{_api_url().rstrip('/')}/memories", json=payload, headers=_headers(), timeout=30)
        response.raise_for_status()
        memory = response.json()
    else:
        memory = _db().add_memory(**payload).model_dump(mode="json")
    console.print(f"✅ Added {memory['type']} memory: [bold]{memory['id']}[/bold]")


@app.command(name="list")
def list_cmd(
    project: Optional[str] = typer.Option(None, "--project", "-p"),
    type: Optional[str] = typer.Option(None, "--type"),
    status: Optional[str] = typer.Option(None, "--status"),
    limit: int = typer.Option(20, "--limit"),
) -> None:
    if _api_url():
        response = httpx.get(f"{_api_url().rstrip('/')}/memories", params={"project": project, "type": type, "status": status, "limit": limit}, headers=_headers(), timeout=30)
        response.raise_for_status()
        memories = response.json()
    else:
        memories = [m.model_dump(mode="json") for m in _db().list_memories(project=project, type=type, status=status, limit=limit)]
    _print_memories(memories)


@app.command()
def search(
    query: str = typer.Argument(...),
    project: Optional[str] = typer.Option(None, "--project", "-p"),
    type: Optional[str] = typer.Option(None, "--type"),
    limit: int = typer.Option(20, "--limit"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    if _api_url():
        response = httpx.get(f"{_api_url().rstrip('/')}/search", params={"q": query, "project": project, "type": type, "limit": limit}, headers=_headers(), timeout=30)
        response.raise_for_status()
        results = response.json()
    else:
        results = [r.model_dump(mode="json") for r in _db().search(query, project=project, type=type, limit=limit)]
    if json_output:
        console.print(json.dumps(results, indent=2))
        return
    _print_memories([r["memory"] for r in results])


@app.command()
def context(
    project: str = typer.Option(..., "--project", "-p"),
    goal: Optional[str] = typer.Option(None, "--goal", "-g"),
    max_items: int = typer.Option(20, "--max-items"),
) -> None:
    if _api_url():
        response = httpx.get(f"{_api_url().rstrip('/')}/context", params={"project": project, "goal": goal, "max_items": max_items}, headers=_headers(), timeout=30)
        response.raise_for_status()
        console.print(response.text)
    else:
        console.print(_db().context_pack(project=project, goal=goal, max_items=max_items))


def _print_memories(memories: list[dict]) -> None:
    table = Table(title="Memory Hub")
    table.add_column("ID", overflow="fold")
    table.add_column("Type")
    table.add_column("Project")
    table.add_column("Title")
    table.add_column("Status")
    for memory in memories:
        table.add_row(memory["id"][:8], memory["type"], memory.get("project") or "", memory["title"], memory["status"])
    console.print(table)


if __name__ == "__main__":
    app()
