# ⚡ Gridbert — Dein persönlicher Energie-Agent

Gridbert analysiert deine Stromrechnung, vergleicht Tarife über E-Control und zeigt dir, was du mit einer Bürgerenergiegemeinschaft (BEG) sparen kannst — alles lokal, ohne Cloud-APIs.

## Was macht Gridbert?

1. **Rechnung analysieren** — PDF hochladen, Gridbert liest Lieferant, Tarif, Verbrauch und Preis per OCR (Ollama + Qwen2.5)
2. **Smart-Meter-Daten holen** *(optional)* — Echte Verbrauchsdaten von Wiener Netze
3. **Tarife vergleichen** — Automatischer Vergleich über die E-Control Tarifkalkulator-API
4. **BEG-Vorteil berechnen** — Ersparnis durch 7Energy Bürgerenergiegemeinschaft
5. **Report generieren** — Alles zusammen in einem übersichtlichen Einsparungs-Report

## Voraussetzungen

- **Python 3.11+**
- **Ollama** — Lokale LLM-Inferenz ([ollama.com](https://ollama.com))
- ca. 8 GB RAM für die Modelle

## Installation

```bash
# 1. Repo klonen
git clone https://github.com/your-username/gridbert.git
cd gridbert

# 2. Ollama installieren (falls noch nicht vorhanden)
# macOS:
brew install ollama
# Oder: https://ollama.com/download

# 3. Ollama starten und Modelle pullen
ollama serve &
ollama pull qwen2.5:7b
ollama pull qwen2.5vl:7b

# 4. Gridbert installieren
pip install -e .

# 5. Konfiguration (optional)
cp .env.example .env
# .env editieren falls nötig (Wiener Netze Credentials, anderer Ollama Host etc.)
```

## Benutzung

### Web-Oberfläche (empfohlen)

```bash
python3 -m gridbert.main --web
```

Dann im Browser öffnen: **http://localhost:5000**

- Stromrechnung (PDF) hochladen
- Optional: Wiener Netze Credentials für Smart-Meter-Daten eingeben
- Gridbert analysiert und zeigt den Einsparungs-Report

Optionen:
```bash
python3 -m gridbert.main --web --port 8080    # Anderer Port
python3 -m gridbert.main --web -v             # Debug-Logging
```

### Kommandozeile

```bash
python3 -m gridbert.main rechnung.pdf
python3 -m gridbert.main rechnung.pdf --wn-email user@example.com --wn-password geheim
```

## Projektstruktur

```
gridbert/
├── gridbert/
│   ├── main.py               # CLI + Pipeline-Orchestrierung
│   ├── agent.py               # LLM Agent-Loop (für zukünftige interaktive Nutzung)
│   ├── config.py              # Konfiguration aus .env
│   ├── models.py              # Pydantic Datenmodelle
│   ├── personality.py         # Gridbert Persönlichkeit & System-Prompt
│   ├── report.py              # Markdown Report-Generierung
│   ├── tools/
│   │   ├── invoice_parser.py  # Rechnungs-OCR via Ollama
│   │   ├── smartmeter.py      # Wiener Netze Smart Meter API
│   │   ├── tariff_compare.py  # E-Control Tarifvergleich
│   │   └── beg_advisor.py     # 7Energy BEG-Berechnung
│   └── web/
│       ├── app.py             # Flask Web-Oberfläche
│       ├── sse.py             # Server-Sent Events für Pipeline-Progress
│       ├── templates/         # Jinja2 HTML Templates
│       └── static/            # CSS + HTMX
├── pyproject.toml
├── .env.example
└── CLAUDE.md                  # Projekt-Konventionen
```

## Architektur-Prinzipien

- **Kein Cloud-API** — Alles läuft lokal (Ollama für LLM, lokale APIs)
- **LLM nur für Sprache** — OCR und Report-Text. Alle Berechnungen sind deterministisches Python
- **Alle Preise brutto** — Inklusive 20% österreichischer MwSt
- **Kein Over-Engineering** — Kein ORM, kein DB, kein async, plain dicts + Pydantic

## Konfiguration

Umgebungsvariablen in `.env` (oder als CLI-Argumente):

| Variable | Standard | Beschreibung |
|----------|----------|-------------|
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama Server URL |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Text-Modell für Extraktion |
| `OLLAMA_VISION_MODEL` | `qwen2.5vl:7b` | Vision-Modell (Fallback für Scan-PDFs) |
| `WIENER_NETZE_EMAIL` | — | Wiener Netze Login (optional) |
| `WIENER_NETZE_PASSWORD` | — | Wiener Netze Passwort (optional) |

## Lizenz

AGPL-3.0-only — siehe [LICENSE](LICENSE).
