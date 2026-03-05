"""Tests for gridbert.tools.energy_monitor — Förderungskatalog."""

from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import patch

import pytest

from gridbert.models.energy_news import Foerderung
from gridbert.tools.energy_monitor import (
    _check_catalog_freshness,
    _filter_foerderungen,
    load_foerderungen_catalog,
)


class TestLoadFoerderungenCatalog:
    def test_catalog_loads_successfully(self):
        catalog, stand = load_foerderungen_catalog()
        assert len(catalog) > 0
        assert stand != "unbekannt"

    def test_catalog_has_required_fields(self):
        catalog, _ = load_foerderungen_catalog()
        required_fields = ["name", "beschreibung", "status"]
        for entry in catalog:
            for field in required_fields:
                assert field in entry, f"Feld '{field}' fehlt in {entry.get('name', '?')}"

    def test_catalog_entries_have_stand(self):
        catalog, _ = load_foerderungen_catalog()
        for entry in catalog:
            assert entry.get("stand"), f"Kein 'stand' für {entry['name']}"

    def test_catalog_entries_have_quelle(self):
        catalog, _ = load_foerderungen_catalog()
        for entry in catalog:
            if entry.get("status") == "aktiv":
                assert entry.get("quelle"), f"Keine 'quelle' für {entry['name']}"

    def test_catalog_stand_is_valid_date(self):
        _, stand = load_foerderungen_catalog()
        # Should not raise
        date.fromisoformat(stand)


class TestCatalogFreshness:
    def test_fresh_catalog(self):
        today = date.today().isoformat()
        assert _check_catalog_freshness(today) == ""

    def test_stale_catalog(self):
        old = (date.today() - timedelta(days=90)).isoformat()
        warning = _check_catalog_freshness(old)
        assert "90 Tage" in warning
        assert "veraltet" in warning

    def test_unknown_stand(self):
        warning = _check_catalog_freshness("unbekannt")
        assert "unbekannt" in warning

    def test_empty_stand(self):
        warning = _check_catalog_freshness("")
        assert "unbekannt" in warning

    def test_invalid_date(self):
        warning = _check_catalog_freshness("not-a-date")
        assert "ungültig" in warning


class TestFilterFoerderungen:
    @pytest.fixture
    def sample_catalog(self):
        today = date.today()
        return [
            {
                "name": "Bundesförderung PV",
                "beschreibung": "Test",
                "betrag_text": "160 €/kWp",
                "bundesland": "",
                "status": "aktiv",
                "gueltig_bis": (today + timedelta(days=100)).isoformat(),
                "kategorie": "pv",
            },
            {
                "name": "Wien Speicher",
                "beschreibung": "Test Wien",
                "betrag_text": "200 €/kWh",
                "bundesland": "Wien",
                "status": "aktiv",
                "gueltig_bis": (today + timedelta(days=100)).isoformat(),
                "kategorie": "speicher",
            },
            {
                "name": "Tirol PV",
                "beschreibung": "Test Tirol",
                "betrag_text": "125 €/kWp",
                "bundesland": "Tirol",
                "status": "aktiv",
                "gueltig_bis": (today + timedelta(days=100)).isoformat(),
                "kategorie": "pv",
            },
            {
                "name": "Ausgelaufene Förderung",
                "beschreibung": "Expired",
                "betrag_text": "—",
                "bundesland": "",
                "status": "ausgelaufen",
                "gueltig_bis": (today - timedelta(days=30)).isoformat(),
                "kategorie": "pv",
            },
            {
                "name": "Abgelaufene Gültigkeit",
                "beschreibung": "Past validity",
                "betrag_text": "100 €",
                "bundesland": "",
                "status": "aktiv",
                "gueltig_bis": (today - timedelta(days=1)).isoformat(),
                "kategorie": "pv",
            },
        ]

    def test_wien_user_gets_bundesweit_and_wien(self, sample_catalog):
        result = _filter_foerderungen(sample_catalog, "1060")
        names = [f.name for f in result]
        assert "Bundesförderung PV" in names
        assert "Wien Speicher" in names
        assert "Tirol PV" not in names

    def test_tirol_user_gets_bundesweit_and_tirol(self, sample_catalog):
        result = _filter_foerderungen(sample_catalog, "6020")
        names = [f.name for f in result]
        assert "Bundesförderung PV" in names
        assert "Tirol PV" in names
        assert "Wien Speicher" not in names

    def test_expired_foerderungen_excluded(self, sample_catalog):
        result = _filter_foerderungen(sample_catalog, "1060")
        names = [f.name for f in result]
        assert "Ausgelaufene Förderung" not in names

    def test_past_validity_excluded(self, sample_catalog):
        result = _filter_foerderungen(sample_catalog, "1060")
        names = [f.name for f in result]
        assert "Abgelaufene Gültigkeit" not in names

    def test_no_plz_returns_only_bundesweit(self, sample_catalog):
        result = _filter_foerderungen(sample_catalog, "")
        names = [f.name for f in result]
        assert "Bundesförderung PV" in names
        assert "Wien Speicher" not in names
        assert "Tirol PV" not in names

    def test_result_are_foerderung_models(self, sample_catalog):
        result = _filter_foerderungen(sample_catalog, "1060")
        for f in result:
            assert isinstance(f, Foerderung)


class TestCatalogIntegrity:
    """Ensure the actual catalog file is well-formed and consistent."""

    def test_no_active_foerderung_without_url(self):
        catalog, _ = load_foerderungen_catalog()
        for entry in catalog:
            if entry.get("status") == "aktiv":
                assert entry.get("url"), f"Aktive Förderung '{entry['name']}' ohne URL"

    def test_no_active_foerderung_without_gueltig_bis(self):
        catalog, _ = load_foerderungen_catalog()
        for entry in catalog:
            if entry.get("status") == "aktiv":
                assert entry.get("gueltig_bis"), (
                    f"Aktive Förderung '{entry['name']}' ohne gueltig_bis"
                )

    def test_valid_dates_in_catalog(self):
        catalog, _ = load_foerderungen_catalog()
        for entry in catalog:
            for field in ("gueltig_ab", "gueltig_bis", "stand"):
                val = entry.get(field, "")
                if val:
                    try:
                        date.fromisoformat(val)
                    except ValueError:
                        pytest.fail(f"Ungültiges Datum in {entry['name']}.{field}: {val}")

    def test_eag_pv_foerderung_amount_is_160(self):
        """Verify EAG PV amount is 160 €/kWp (corrected from old wrong 285)."""
        catalog, _ = load_foerderungen_catalog()
        eag_pv = [f for f in catalog if f["name"] == "EAG Investitionszuschuss Photovoltaik"]
        assert len(eag_pv) == 1
        assert eag_pv[0]["betrag_eur"] == 160.0
