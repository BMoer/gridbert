# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Rechnungs-Extraktion via Claude Vision API oder Ollama (Fallback)."""

from __future__ import annotations

import base64
import io
import json
import logging
from pathlib import Path
from typing import Any

import pdfplumber

from gridbert.config import ANTHROPIC_API_KEY
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
- grundgebuehr_eur_monat = Grundpauschale/Grundgebühr in EURO pro MONAT, BRUTTO. \
Falls als €/Jahr angegeben: durch 12 teilen.
- jahresverbrauch_kwh = Gesamtverbrauch in kWh für den Abrechnungszeitraum. \
Falls kürzer als 1 Jahr: auf 365 Tage hochrechnen.
- Alle Zahlenfelder als Dezimalzahlen (z.B. 19.68, nicht "19,68")
- Falls ein Feld nicht gefunden wird: 0 für Zahlen, "" für Strings

WICHTIG: Antworte NUR mit dem JSON. Keine Erklärung, keine Markdown-Überschriften, \
nur das JSON-Objekt.
"""


# --- PDF/Bild Helpers (wiederverwendet aus v0.2) ------------------------------

def _pdf_to_images(pdf_path: Path) -> list[bytes]:
    """Konvertiere PDF-Seiten zu PNG-Bildern für Vision-Modell."""
    images: list[bytes] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            img = page.to_image(resolution=200)
            buf = io.BytesIO()
            img.original.save(buf, format="PNG")
            images.append(buf.getvalue())
    return images


def _pdf_to_text(pdf_path: Path) -> str:
    """Extrahiere Text aus PDF."""
    pages: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)


def _parse_json_response(text: str) -> dict:
    """Extrahiere JSON aus LLM-Antwort (auch wenn drumherum Text steht)."""
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


# --- LLM-based extraction (Claude or OpenAI via LLMProvider) ------------------

def _extract_via_llm(
    llm_provider: Any = None,
    text: str = "",
    image_b64: str = "",
) -> dict:
    """Extrahiere Rechnungsdaten via LLM Provider (Claude Vision, OpenAI, etc.)."""
    if llm_provider is None:
        # Fallback: create Claude provider from server config
        from gridbert.config import CLAUDE_MODEL
        from gridbert.llm import create_provider

        llm_provider = create_provider("claude", ANTHROPIC_API_KEY, CLAUDE_MODEL)

    if image_b64:
        attachments = [{"media_type": "image/png", "data": image_b64, "file_name": "rechnung.png"}]
        user_content = llm_provider.build_user_content(EXTRACTION_PROMPT, attachments)
    else:
        prompt = (
            f"Hier ist der Text einer österreichischen Stromrechnung:\n\n"
            f"{text}\n\n{EXTRACTION_PROMPT}"
        )
        user_content = prompt

    response = llm_provider.chat(
        system="Du bist ein Experte für österreichische Stromrechnungen.",
        messages=[{"role": "user", "content": user_content}],
        tools=[],
        max_tokens=1024,
    )

    response_text = "\n".join(response.text_parts)
    return _parse_json_response(response_text)


# --- Ollama Fallback (für self-hosted) ----------------------------------------

def _extract_via_ollama(text: str = "", image_b64: str = "") -> dict:
    """Extrahiere Rechnungsdaten via Ollama (Fallback für self-hosted)."""
    import ollama

    from gridbert.config import OLLAMA_HOST, OLLAMA_MODEL, OLLAMA_VISION_MODEL

    client = ollama.Client(host=OLLAMA_HOST, timeout=300)

    if image_b64:
        response = client.chat(
            model=OLLAMA_VISION_MODEL,
            messages=[{
                "role": "user",
                "content": EXTRACTION_PROMPT,
                "images": [image_b64],
            }],
        )
    else:
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
                {"role": "user", "content": EXTRACTION_PROMPT},
            ],
        )

    return _parse_json_response(response.message.content)


# --- Haupt-Funktion -----------------------------------------------------------

def parse_invoice(file_path: str | Path, llm_provider: Any = None) -> Invoice:
    """Extrahiere Rechnungsdaten aus PDF oder Bild.

    Uses the provided LLM provider, falls back to Claude API or Ollama.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {path}")

    # Determine extraction backend
    if llm_provider is not None or ANTHROPIC_API_KEY:
        def extract_fn(text: str = "", image_b64: str = "") -> dict:
            return _extract_via_llm(llm_provider=llm_provider, text=text, image_b64=image_b64)
        backend_name = llm_provider.provider_name if llm_provider else "Claude"
    else:
        extract_fn = _extract_via_ollama
        backend_name = "Ollama"

    if path.suffix.lower() == ".pdf":
        text = _pdf_to_text(path)
        if text.strip():
            # Text kürzen falls zu lang
            if len(text) > 6000:
                text = text[:6000]
                log.info("PDF-Text auf 6000 Zeichen gekürzt")
            log.info("Sende PDF-Text (%d Zeichen) an %s", len(text), backend_name)
            raw = extract_fn(text=text)
        else:
            # Scan-PDF → Vision mit erster Seite
            images = _pdf_to_images(path)
            if not images:
                raise ValueError(f"PDF enthält weder Text noch Bilder: {path}")
            log.info("PDF ist Scan — sende Seite 1 an %s Vision", backend_name)
            raw = extract_fn(image_b64=base64.b64encode(images[0]).decode())
    else:
        # Bild (JPG, PNG, etc.)
        log.info("Sende Bild an %s Vision", backend_name)
        raw = extract_fn(image_b64=base64.b64encode(path.read_bytes()).decode())

    # Direkt als Invoice parsen — Claude liefert exakte Feldnamen
    # Defaults für fehlende Felder
    raw.setdefault("lieferant", "Unbekannt")
    raw.setdefault("energiepreis_ct_kwh", 0.0)
    raw.setdefault("jahresverbrauch_kwh", 0.0)
    raw.setdefault("plz", "")

    log.info("Extrahierte Rechnungsdaten: %s", raw)
    return Invoice(**raw)
