# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Rechnungs-Extraktion via LLM Vision (Ollama + LLaVA)."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

import ollama
import pdfplumber

from gridbert.config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_VISION_MODEL
from gridbert.models import Invoice

log = logging.getLogger(__name__)

EXTRACTION_PROMPT = """\
Extrahiere aus dieser österreichischen Stromrechnung die folgenden Felder. \
Antworte AUSSCHLIESSLICH mit einem JSON-Objekt. Kein Text davor, kein Text danach. \
Nur das JSON.

```json
{
  "lieferant": "Name des Stromlieferanten",
  "tarif_name": "Name des Tarifs",
  "energiepreis_ct_kwh": 0.0,
  "grundgebuehr_eur_monat": 0.0,
  "jahresverbrauch_kwh": 0.0,
  "plz": "0000",
  "zaehlpunkt": "AT00...",
  "netzkosten_eur_jahr": 0.0
}
```

Regeln:
- energiepreis_ct_kwh = Arbeitspreis/Energiepreis in CENT pro kWh, BRUTTO (inkl. 20% MwSt)
- grundgebuehr_eur_monat = Grundpauschale/Grundgebühr in EURO pro MONAT, BRUTTO. Falls als €/Jahr angegeben: durch 12 teilen.
- jahresverbrauch_kwh = Gesamtverbrauch in kWh für den Abrechnungszeitraum. Falls kürzer als 1 Jahr: auf 365 Tage hochrechnen.
- Alle Zahlenfelder als Dezimalzahlen (z.B. 19.68, nicht "19,68")
- Falls ein Feld nicht gefunden wird: 0 für Zahlen, "" für Strings

WICHTIG: Antworte NUR mit dem JSON. Keine Erklärung, keine Markdown-Überschriften, nur das JSON-Objekt.
"""


def _pdf_to_images(pdf_path: Path) -> list[bytes]:
    """Konvertiere PDF-Seiten zu PNG-Bildern für Vision-Modell."""
    images: list[bytes] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            img = page.to_image(resolution=200)
            img_bytes = img.original.tobytes()  # noqa: not what we want
            # pdfplumber Image → PIL Image → PNG bytes
            import io

            buf = io.BytesIO()
            img.original.save(buf, format="PNG")
            images.append(buf.getvalue())
    return images


def _pdf_to_text(pdf_path: Path) -> str:
    """Extrahiere Text aus PDF als Fallback."""
    pages: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)


def _image_to_base64(image_path: Path) -> str:
    return base64.b64encode(image_path.read_bytes()).decode()


def _parse_json_response(text: str) -> dict:
    """Extrahiere JSON aus LLM-Antwort (auch wenn drumherum Text steht)."""
    # Versuche direktes Parsing
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Suche nach JSON-Block in Markdown-Codeblock
    if "```" in text:
        for block in text.split("```"):
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            try:
                return json.loads(block)
            except json.JSONDecodeError:
                continue

    # Suche nach erstem { ... } Block
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"Konnte kein JSON aus LLM-Antwort extrahieren: {text[:200]}")


# Feld-Aliase: LLaVA liefert die Felder unter verschiedenen Namen
_FIELD_ALIASES: dict[str, list[str]] = {
    "lieferant": ["lieferant", "supplier", "anbieter", "versorger", "stromlieferant"],
    "tarif_name": ["tarif_name", "tarif", "tarifname", "tariff", "produkt"],
    "energiepreis_ct_kwh": [
        "energiepreis_ct_kwh", "energiepreis", "preis_ct_kwh", "preis",
        "arbeitspreis", "arbeitspreis_ct_kwh", "cent_pro_kwh", "ct_kwh",
        "energy_price", "strompreis",
    ],
    "grundgebuehr_eur_monat": [
        "grundgebuehr_eur_monat", "grundgebuehr", "grundgebühr", "grundpauschale",
        "base_fee", "pauschale", "grundpreis",
    ],
    "jahresverbrauch_kwh": [
        "jahresverbrauch_kwh", "jahresverbrauch", "verbrauch_kwh", "verbrauch",
        "annual_consumption", "consumption", "kwh",
    ],
    "plz": ["plz", "postleitzahl", "zip", "postal_code"],
    "zaehlpunkt": ["zaehlpunkt", "zaehlpunktnummer", "meter_id", "zaehler"],
    "netzkosten_eur_jahr": ["netzkosten_eur_jahr", "netzkosten", "netzgebühr", "netzentgelt"],
}


def _normalize_invoice(raw: dict) -> Invoice:
    """Normalisiere LLM-Output zu Invoice — robustes Feld-Mapping."""
    normalized: dict = {}

    # Lowercase alle Keys für einfacheres Matching
    raw_lower = {k.lower().replace(" ", "_"): v for k, v in raw.items()}

    for field, aliases in _FIELD_ALIASES.items():
        for alias in aliases:
            if alias in raw_lower and raw_lower[alias] is not None:
                val = raw_lower[alias]
                # Versuche numerische Felder zu parsen
                if field in ("energiepreis_ct_kwh", "grundgebuehr_eur_monat",
                             "jahresverbrauch_kwh", "netzkosten_eur_jahr"):
                    try:
                        # "31,35" → 31.35 (österreichisches Format)
                        if isinstance(val, str):
                            val = val.replace(",", ".").replace("€", "").replace("ct", "").strip()
                        val = float(val)
                    except (ValueError, TypeError):
                        continue
                normalized[field] = val
                break

    # Defaults für fehlende Pflichtfelder
    normalized.setdefault("lieferant", "Unbekannt")
    normalized.setdefault("energiepreis_ct_kwh", 0.0)
    normalized.setdefault("jahresverbrauch_kwh", 0.0)
    normalized.setdefault("plz", "")

    log.info("Normalisierte Rechnungsdaten: %s", normalized)
    return Invoice(**normalized)


def parse_invoice(file_path: str | Path) -> Invoice:
    """Extrahiere Rechnungsdaten aus PDF oder Bild via Ollama Vision."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")

    client = ollama.Client(host=OLLAMA_HOST, timeout=300)

    if path.suffix.lower() == ".pdf":
        # PDF: Bevorzugt Text-Extraktion (schneller + zuverlässiger), Vision als Fallback
        text = _pdf_to_text(path)
        if text.strip():
            # Text kürzen falls zu lang (erste ~4000 Zeichen reichen für Rechnungsdaten)
            if len(text) > 4000:
                text = text[:4000]
                log.info("PDF-Text auf 4000 Zeichen gekürzt")
            log.info("Sende PDF-Text (%d Zeichen) an %s", len(text), OLLAMA_MODEL)
            response = client.chat(
                model=OLLAMA_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": f"Hier ist der Text einer österreichischen Stromrechnung:\n\n{text}",
                    },
                    {
                        "role": "assistant",
                        "content": "Ich habe den Rechnungstext gelesen. Was soll ich damit tun?",
                    },
                    {
                        "role": "user",
                        "content": EXTRACTION_PROMPT,
                    },
                ],
            )
        else:
            # Kein Text extrahierbar (Scan-PDF) → Vision mit erster Seite
            images = _pdf_to_images(path)
            if not images:
                raise ValueError(f"PDF enthält weder Text noch Bilder: {path}")
            log.info("PDF ist Scan — sende Seite 1 an %s", OLLAMA_VISION_MODEL)
            response = client.chat(
                model=OLLAMA_VISION_MODEL,
                messages=[
                    {
                        "role": "user",
                        "content": EXTRACTION_PROMPT,
                        "images": [base64.b64encode(images[0]).decode()],
                    }
                ],
            )
    else:
        # Bild (JPG, PNG, etc.)
        log.info("Sende Bild an %s", OLLAMA_VISION_MODEL)
        b64 = _image_to_base64(path)
        response = client.chat(
            model=OLLAMA_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": EXTRACTION_PROMPT,
                    "images": [b64],
                }
            ],
        )

    raw = _parse_json_response(response.message.content)
    return _normalize_invoice(raw)
