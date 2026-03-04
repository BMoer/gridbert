# Gridbert — Dein persönlicher Energie-Agent

Gridbert ist ein conversational AI-Agent, der österreichischen Konsumenten hilft, ihre Energiekosten zu optimieren. Er analysiert Stromrechnungen, vergleicht Tarife, holt Smart-Meter-Daten, simuliert PV-Anlagen und Batteriespeicher — und merkt sich alles für personalisierte Empfehlungen.

## Was kann Gridbert?

| Fähigkeit | Beschreibung |
|-----------|-------------|
| **Rechnungs-OCR** | PDF oder Bild hochladen — Gridbert liest Lieferant, Tarif, Verbrauch und Preis via Claude Vision |
| **Smart Meter** | Verbrauchsdaten direkt vom Netzbetreiber holen (Wiener Netze, Netz NÖ, Netz OÖ, …) |
| **Tarifvergleich** | Strom- und Gastarife über die E-Control Tarifkalkulator-API vergleichen |
| **BEG-Vergleich** | Bürgerenergiegemeinschaften vergleichen und Ersparnis berechnen |
| **Lastprofil-Analyse** | 15-Minuten-Daten auswerten: Grundlast, Spitzenlast, Anomalien, Sparpotenziale |
| **Spot-Tarif-Analyse** | ENTSO-E Day-Ahead-Preise vs. Fixpreis — lohnt sich ein Spot-Tarif? |
| **PV-Simulation** | Balkonkraftwerk oder PV-Anlage simulieren (PVGIS API), Amortisation berechnen |
| **Batteriespeicher** | Speicher-Szenarien (2–15 kWh) mit Spot-Preisen simulieren |
| **Energie-News** | Aktuelle Nachrichten, Marktentwicklungen und Förderungen personalisiert aufbereiten |
| **Persönliches Gedächtnis** | Gridbert merkt sich deine Situation und gibt zunehmend bessere Empfehlungen |

## Architektur

```
React SPA (Vite + TailwindCSS)
    │ SSE Streaming
    ▼
FastAPI Backend
    │
    ├── GridbertAgent (Claude API mit nativem Tool-Calling)
    ├── Tool Registry (12 Tools, automatisch verfügbar)
    └── SQLite / PostgreSQL (Conversations, Memory, Analysen)
```

**Kernprinzipien:**
- **Agent-First** — Claude entscheidet welche Tools aufgerufen werden, keine hardcodierte Pipeline
- **LLM nur für Sprache** — Alle Berechnungen sind deterministisches Python
- **Alle Preise brutto** — Inklusive 20% österreichischer MwSt

## Voraussetzungen

- **Python 3.11+**
- **Node.js 18+** (für Frontend)
- **Anthropic API Key** ([console.anthropic.com](https://console.anthropic.com))

## Schnellstart

```bash
# 1. Repo klonen
git clone https://github.com/BMoer/gridbert.git
cd gridbert

# 2. Backend installieren
pip install -e .

# 3. Konfiguration
cp .env.example .env
# ANTHROPIC_API_KEY und SECRET_KEY in .env setzen

# 4. Frontend installieren
cd frontend && npm install && cd ..

# 5. Backend starten (Terminal 1)
python3 -m gridbert.api.run

# 6. Frontend starten (Terminal 2)
cd frontend && npm run dev
```

Dann im Browser öffnen: **http://localhost:5173**

## Docker

```bash
cp .env.example .env
# .env editieren (mindestens ANTHROPIC_API_KEY und SECRET_KEY)
docker compose up --build
```

Dann öffnen: **http://localhost:5000**

## Projektstruktur

```
gridbert/
├── gridbert/
│   ├── agent/                  # Agent-Loop + Tool-Registry
│   │   ├── loop.py             # Claude API Agent-Loop
│   │   ├── tool_registry.py    # Tool-Definitionen + Dispatch
│   │   └── types.py            # Event-Typen für SSE-Streaming
│   ├── api/                    # FastAPI Backend
│   │   ├── app.py              # App-Factory
│   │   ├── routes/             # Chat, Auth, Conversations, Dashboard
│   │   └── deps.py             # Dependency Injection
│   ├── models/                 # Pydantic Datenmodelle
│   ├── storage/                # SQLite/PostgreSQL Repositories
│   ├── tools/                  # Alle Agent-Tools
│   │   ├── invoice_parser.py   # Rechnungs-OCR (Claude Vision)
│   │   ├── smartmeter.py       # Smart Meter API
│   │   ├── tariff_compare.py   # E-Control Stromtarife
│   │   ├── gas_compare.py      # E-Control Gastarife
│   │   ├── beg_advisor.py      # BEG-Vergleich
│   │   ├── load_profile.py     # Lastprofil-Analyse
│   │   ├── spot_analysis.py    # ENTSO-E Spot-Tarif-Analyse
│   │   ├── battery_sim.py      # Batteriespeicher-Simulation
│   │   ├── pv_sim.py           # PV/Balkonkraftwerk-Simulation
│   │   └── energy_monitor.py   # News, Preise, Förderungen
│   ├── config.py               # Konfiguration aus .env
│   └── personality.py          # Gridbert System-Prompt
├── frontend/                   # React SPA
│   ├── src/
│   │   ├── components/Chat/    # Chat-UI mit SSE-Streaming
│   │   ├── components/Layout/  # Sidebar, Navigation
│   │   ├── hooks/              # useChat (SSE), API-Hooks
│   │   └── stores/             # Zustand State Management
│   └── vite.config.ts
├── homeassistant/              # Home Assistant Integration
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Konfiguration

Umgebungsvariablen in `.env`:

| Variable | Pflicht | Beschreibung |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Ja | Claude API Key |
| `SECRET_KEY` | Ja (Prod) | JWT-Secret für Auth |
| `DATABASE_URL` | Nein | PostgreSQL URL (default: SQLite) |
| `CORS_ORIGINS` | Nein | Erlaubte Origins (default: localhost) |
| `ENTSOE_API_KEY` | Nein | Für Spot-Tarif-Analyse |
| `WIENER_NETZE_EMAIL` | Nein | Smart Meter Zugang |
| `WIENER_NETZE_PASSWORD` | Nein | Smart Meter Passwort |

## Lizenz

AGPL-3.0-only — siehe [LICENSE](LICENSE).
