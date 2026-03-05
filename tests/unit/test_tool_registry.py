"""Tests for gridbert.agent.tool_registry."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from gridbert.agent.tool_registry import ToolRegistry


class TestToolRegistry:
    def test_register_and_definitions(self):
        reg = ToolRegistry()
        reg.register(
            name="greet",
            description="Say hello",
            input_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            handler=lambda name="World": f"Hello {name}",
        )

        defs = reg.definitions()
        assert len(defs) == 1
        assert defs[0]["name"] == "greet"
        assert defs[0]["description"] == "Say hello"

    def test_execute_simple(self):
        reg = ToolRegistry()
        reg.register(
            name="add",
            description="Add two numbers",
            input_schema={"type": "object"},
            handler=lambda a, b: a + b,
        )
        result = reg.execute("add", {"a": 3, "b": 4})
        assert result == "7"

    def test_execute_unknown_tool(self):
        reg = ToolRegistry()
        result = reg.execute("nonexistent", {})
        assert "Unbekanntes Tool" in result

    def test_execute_handler_exception(self):
        reg = ToolRegistry()
        reg.register(
            name="fail",
            description="Always fails",
            input_schema={"type": "object"},
            handler=lambda: 1 / 0,
        )
        result = reg.execute("fail", {})
        assert "Fehler bei fail" in result
        assert "division by zero" in result

    def test_execute_pydantic_model(self):
        class MyResult(BaseModel):
            value: int
            label: str

        reg = ToolRegistry()
        reg.register(
            name="model_tool",
            description="Returns a Pydantic model",
            input_schema={"type": "object"},
            handler=lambda: MyResult(value=42, label="answer"),
        )
        result = reg.execute("model_tool", {})
        assert '"value": 42' in result
        assert '"label": "answer"' in result

    def test_tool_names(self):
        reg = ToolRegistry()
        reg.register("a", "desc a", {"type": "object"}, lambda: None)
        reg.register("b", "desc b", {"type": "object"}, lambda: None)
        assert reg.tool_names == ["a", "b"]

    def test_multiple_definitions(self):
        reg = ToolRegistry()
        for i in range(5):
            reg.register(f"tool_{i}", f"Tool {i}", {"type": "object"}, lambda: None)
        defs = reg.definitions()
        assert len(defs) == 5
        names = [d["name"] for d in defs]
        assert names == [f"tool_{i}" for i in range(5)]


class TestBuildDefaultRegistry:
    def test_all_tools_registered(self):
        from gridbert.agent.tool_registry import build_default_registry

        reg = build_default_registry()
        expected_tools = [
            "parse_invoice",
            "fetch_smart_meter_data",
            "list_smart_meter_providers",
            "compare_tariffs",
            "compare_beg_options",
            "generate_savings_report",
            "analyze_load_profile",
            "analyze_spot_tariff",
            "simulate_battery",
            "simulate_pv",
            "compare_gas_tariffs",
            "monitor_energy_news",
            "web_search",
        ]
        for tool in expected_tools:
            assert tool in reg.tool_names, f"Tool {tool} nicht registriert"

    def test_definitions_have_correct_structure(self):
        from gridbert.agent.tool_registry import build_default_registry

        reg = build_default_registry()
        for defn in reg.definitions():
            assert "name" in defn
            assert "description" in defn
            assert "input_schema" in defn
            assert defn["input_schema"]["type"] == "object"

    def test_list_providers_executes(self):
        from gridbert.agent.tool_registry import build_default_registry

        reg = build_default_registry()
        result = reg.execute("list_smart_meter_providers", {})
        assert "wiener_netze" in result.lower() or "Wiener" in result

    def test_pv_tool_requires_ausrichtung(self):
        from gridbert.agent.tool_registry import build_default_registry

        reg = build_default_registry()
        defs = {d["name"]: d for d in reg.definitions()}
        pv_def = defs["simulate_pv"]
        assert "ausrichtung" in pv_def["input_schema"]["required"]

    def test_web_search_registered(self):
        from gridbert.agent.tool_registry import build_default_registry

        reg = build_default_registry()
        assert "web_search" in reg.tool_names

    def test_memory_tool_not_registered_without_context(self):
        from gridbert.agent.tool_registry import build_default_registry

        reg = build_default_registry()
        assert "update_user_memory" not in reg.tool_names

    def test_memory_tool_registered_with_context(self, db_engine):
        from gridbert.agent.tool_registry import build_default_registry

        with db_engine.connect() as conn:
            reg = build_default_registry(user_id=1, db_conn=conn)
            assert "update_user_memory" in reg.tool_names
            assert "get_user_file" in reg.tool_names
            # Verify the tool definition has correct schema
            defs = {d["name"]: d for d in reg.definitions()}
            mem_def = defs["update_user_memory"]
            props = mem_def["input_schema"]["properties"]
            assert "fact_key" in props
            assert "fact_value" in props

    def test_memory_tool_persists(self, db_engine):
        """Memory tool should actually persist to DB."""
        from gridbert.agent.tool_registry import build_default_registry
        from gridbert.storage.repositories.memory_repo import get_user_memories
        from gridbert.storage.repositories.user_repo import create_user

        with db_engine.connect() as conn:
            user_id = create_user(conn, email="mem@test.com", password_hash="x", name="Mem")
            conn.commit()

            reg = build_default_registry(user_id=user_id, db_conn=conn)
            result = reg.execute("update_user_memory", {
                "fact_key": "PLZ",
                "fact_value": "1060",
            })
            assert "Gespeichert" in result
            assert "PLZ" in result

            memories = get_user_memories(conn, user_id)
            assert len(memories) == 1
            assert memories[0]["fact_key"] == "PLZ"
            assert memories[0]["fact_value"] == "1060"
