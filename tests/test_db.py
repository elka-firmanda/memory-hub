from pathlib import Path

from memory_hub.db import MemoryDB


def test_add_and_get_memory(tmp_path: Path):
    db = MemoryDB(tmp_path / "memory.sqlite")
    db.init()

    created = db.add_memory(
        type="fact",
        title="Discord gateway",
        content="Discord bot token is configured in ~/.hermes/.env",
        project="hermes",
        tags=["discord", "gateway"],
        source_agent="test",
    )

    loaded = db.get_memory(created.id)
    assert loaded is not None
    assert loaded.id == created.id
    assert loaded.type == "fact"
    assert loaded.project == "hermes"
    assert loaded.tags == ["discord", "gateway"]


def test_search_finds_memory_by_content_and_project(tmp_path: Path):
    db = MemoryDB(tmp_path / "memory.sqlite")
    db.init()
    db.add_memory("fact", "Discord", "Gateway uses bot token", project="hermes", tags=["discord"])
    db.add_memory("fact", "Stocks", "IHSG watchlist lives elsewhere", project="stocks", tags=["market"])

    results = db.search("gateway", project="hermes")

    assert len(results) == 1
    assert results[0].memory.title == "Discord"
    assert results[0].memory.project == "hermes"


def test_context_pack_prioritizes_active_project_items(tmp_path: Path):
    db = MemoryDB(tmp_path / "memory.sqlite")
    db.init()
    db.add_memory("fact", "Token", "Discord token exists", project="hermes", tags=["discord"])
    db.add_memory("decision", "Use gateway", "Use Hermes gateway, not standalone bot", project="hermes")
    db.add_memory("task", "Configure channel", "Need guild_id and channel_id", project="hermes", status="active")

    pack = db.context_pack(project="hermes", goal="debug discord gateway", max_items=10)

    assert "# Context Pack: hermes" in pack
    assert "Discord token exists" in pack
    assert "Use Hermes gateway" in pack
    assert "Need guild_id and channel_id" in pack
