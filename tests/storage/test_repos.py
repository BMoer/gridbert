"""Tests for storage repositories (user, chat, memory)."""

from __future__ import annotations

import pytest

from gridbert.storage.repositories.chat_repo import (
    add_message,
    create_conversation,
    get_conversations,
    get_messages,
)
from gridbert.storage.repositories.memory_repo import (
    delete_memory,
    get_user_memories,
    upsert_memory,
)
from gridbert.storage.repositories.user_repo import (
    create_user,
    get_user_by_email,
    get_user_by_id,
    update_user,
)


class TestUserRepo:
    def test_create_and_get_by_id(self, db_conn):
        uid = create_user(db_conn, email="a@b.com", password_hash="hash123", name="Alice")
        db_conn.commit()
        user = get_user_by_id(db_conn, uid)
        assert user is not None
        assert user["email"] == "a@b.com"
        assert user["name"] == "Alice"

    def test_get_by_email(self, db_conn):
        create_user(db_conn, email="bob@test.com", password_hash="hash", name="Bob")
        db_conn.commit()
        user = get_user_by_email(db_conn, "bob@test.com")
        assert user is not None
        assert user["name"] == "Bob"

    def test_get_nonexistent_user(self, db_conn):
        assert get_user_by_id(db_conn, 99999) is None
        assert get_user_by_email(db_conn, "no@one.com") is None

    def test_update_user(self, db_conn):
        uid = create_user(db_conn, email="u@t.com", password_hash="h")
        db_conn.commit()
        update_user(db_conn, uid, name="Updated", plz="1060")
        db_conn.commit()
        user = get_user_by_id(db_conn, uid)
        assert user["name"] == "Updated"
        assert user["plz"] == "1060"

    def test_update_rejects_disallowed_fields(self, db_conn):
        uid = create_user(db_conn, email="x@t.com", password_hash="h")
        db_conn.commit()
        # password_hash is not in allowed fields
        update_user(db_conn, uid, password_hash="evil")
        db_conn.commit()
        user = get_user_by_id(db_conn, uid)
        assert user["password_hash"] == "h"


class TestChatRepo:
    def _make_user(self, db_conn) -> int:
        uid = create_user(db_conn, email=f"chat-{id(db_conn)}@t.com", password_hash="h")
        db_conn.commit()
        return uid

    def test_create_conversation(self, db_conn):
        uid = self._make_user(db_conn)
        cid = create_conversation(db_conn, uid, title="Test Chat")
        db_conn.commit()
        assert isinstance(cid, int)
        assert cid > 0

    def test_get_conversations(self, db_conn):
        uid = self._make_user(db_conn)
        create_conversation(db_conn, uid, title="Chat 1")
        create_conversation(db_conn, uid, title="Chat 2")
        db_conn.commit()
        convs = get_conversations(db_conn, uid)
        assert len(convs) == 2
        titles = [c["title"] for c in convs]
        assert "Chat 1" in titles
        assert "Chat 2" in titles

    def test_add_and_get_messages(self, db_conn):
        uid = self._make_user(db_conn)
        cid = create_conversation(db_conn, uid, title="msg test")
        add_message(db_conn, cid, role="user", content="Hallo")
        add_message(db_conn, cid, role="assistant", content="Hi zurück!")
        db_conn.commit()

        msgs = get_messages(db_conn, cid)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[0]["content"] == "Hallo"
        assert msgs[1]["role"] == "assistant"

    def test_message_with_tool_metadata(self, db_conn):
        uid = self._make_user(db_conn)
        cid = create_conversation(db_conn, uid)
        add_message(db_conn, cid, role="assistant", content="Ergebnis",
                    tool_name="compare_tariffs", tool_input={"plz": "1060"})
        db_conn.commit()
        msgs = get_messages(db_conn, cid)
        assert msgs[0]["tool_name"] == "compare_tariffs"

    def test_message_limit(self, db_conn):
        uid = self._make_user(db_conn)
        cid = create_conversation(db_conn, uid)
        for i in range(10):
            add_message(db_conn, cid, role="user", content=f"msg {i}")
        db_conn.commit()
        msgs = get_messages(db_conn, cid, limit=3)
        assert len(msgs) == 3


class TestMemoryRepo:
    def _make_user(self, db_conn) -> int:
        uid = create_user(db_conn, email=f"mem-{id(db_conn)}@t.com", password_hash="h")
        db_conn.commit()
        return uid

    def test_upsert_and_get(self, db_conn):
        uid = self._make_user(db_conn)
        upsert_memory(db_conn, uid, "PLZ", "1060", source="user_said")
        db_conn.commit()
        memories = get_user_memories(db_conn, uid)
        assert len(memories) == 1
        assert memories[0]["fact_key"] == "PLZ"
        assert memories[0]["fact_value"] == "1060"

    def test_upsert_updates_existing(self, db_conn):
        uid = self._make_user(db_conn)
        upsert_memory(db_conn, uid, "Name", "Ben")
        db_conn.commit()
        upsert_memory(db_conn, uid, "Name", "Benjamin")
        db_conn.commit()
        memories = get_user_memories(db_conn, uid)
        name_facts = [m for m in memories if m["fact_key"] == "Name"]
        assert len(name_facts) == 1
        assert name_facts[0]["fact_value"] == "Benjamin"

    def test_delete_memory(self, db_conn):
        uid = self._make_user(db_conn)
        upsert_memory(db_conn, uid, "Heizung", "Gas")
        db_conn.commit()
        delete_memory(db_conn, uid, "Heizung")
        db_conn.commit()
        memories = get_user_memories(db_conn, uid)
        assert len(memories) == 0

    def test_multiple_facts(self, db_conn):
        uid = self._make_user(db_conn)
        upsert_memory(db_conn, uid, "PLZ", "1060")
        upsert_memory(db_conn, uid, "Verbrauch", "3200 kWh")
        upsert_memory(db_conn, uid, "Lieferant", "Wien Energie")
        db_conn.commit()
        memories = get_user_memories(db_conn, uid)
        assert len(memories) == 3
        # Ordered by fact_key
        keys = [m["fact_key"] for m in memories]
        assert keys == sorted(keys)
