"""Tests for gridbert.tools.load_profile — CSV parsing and analysis."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from gridbert.tools.load_profile import _parse_csv_text, analyze_load_profile


def _generate_csv(rows: int = 96 * 7, sep: str = ";") -> str:
    """Generate a realistic CSV with 15-min intervals."""
    lines = [f"Zeitstempel{sep}Verbrauch_kWh"]
    start = datetime(2025, 1, 1)
    for i in range(rows):
        ts = start + timedelta(minutes=15 * i)
        # Simulate daily pattern: higher during day
        hour = ts.hour
        base = 0.3 if 6 <= hour <= 22 else 0.15
        lines.append(f"{ts.isoformat()}{sep}{base:.2f}")
    return "\n".join(lines)


class TestParseCsvText:
    def test_semicolon_separator(self):
        csv = _generate_csv(sep=";")
        result = _parse_csv_text(csv)
        assert len(result) == 96 * 7
        assert "timestamp" in result[0]
        assert "kwh" in result[0]

    def test_comma_separator(self):
        csv = "timestamp,kwh\n2025-01-01T00:00:00,0.3\n2025-01-01T00:15:00,0.25"
        result = _parse_csv_text(csv)
        assert len(result) == 2
        assert result[0]["kwh"] == 0.3

    def test_german_decimal_comma(self):
        csv = "Datum;Verbrauch\n2025-01-01T00:00:00;0,30\n2025-01-01T00:15:00;0,25"
        result = _parse_csv_text(csv)
        assert result[0]["kwh"] == 0.30
        assert result[1]["kwh"] == 0.25

    def test_column_detection_kwh(self):
        csv = "von;bis;kWh\n2025-01-01T00:00;2025-01-01T00:15;0.30"
        result = _parse_csv_text(csv)
        assert result[0]["kwh"] == 0.30

    def test_column_detection_verbrauch(self):
        csv = "date;verbrauch\n2025-01-01;1.5"
        result = _parse_csv_text(csv)
        assert result[0]["kwh"] == 1.5

    def test_empty_csv_raises(self):
        with pytest.raises(ValueError):
            _parse_csv_text("")


class TestAnalyzeLoadProfileCsv:
    def test_csv_text_input(self):
        csv = _generate_csv(rows=96 * 7)
        result = analyze_load_profile(csv_text=csv)
        assert result.analyse_erfolgreich is True
        assert result.metrics.mean_kw > 0
        assert result.metrics.grundlast_kw > 0
        assert result.metrics.spitzenlast_kw > 0

    def test_csv_text_with_price(self):
        csv = _generate_csv(rows=96 * 3)
        result = analyze_load_profile(csv_text=csv, price_per_kwh=0.25)
        assert result.analyse_erfolgreich is True

    def test_no_data_returns_error(self):
        result = analyze_load_profile()
        assert result.analyse_erfolgreich is False
        assert "Keine Daten" in result.fehler

    def test_structured_data_still_works(self):
        """Existing consumption_data path should still work."""
        data = []
        start = datetime(2025, 1, 1)
        for i in range(96 * 2):  # 2 days
            ts = start + timedelta(minutes=15 * i)
            data.append({"timestamp": ts.isoformat(), "kwh": 0.3})
        result = analyze_load_profile(consumption_data=data)
        assert result.analyse_erfolgreich is True
