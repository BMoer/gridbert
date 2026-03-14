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
│   ├── agent/                    # Agent-Loop + Tool-Registry
│   │   ├── registry.py           # ToolRegistry Klasse (generisch, keine Business-Imports)
│   │   ├── loop.py               # GridbertAgent — provider-agnostischer Agent-Loop
│   │   ├── tool_registry.py      # build_core_registry() — Gridbert-spezifisches Wiring
│   │   └── types.py              # Event-Typen für SSE-Streaming
│   ├── llm/                      # LLM Provider Abstraktion
│   │   ├── __init__.py           # LLMProvider Protocol + create_provider() Factory
│   │   ├── claude_provider.py    # Anthropic Claude
│   │   └── openai_provider.py    # OpenAI GPT
│   ├── api/                      # FastAPI Backend
│   │   ├── app.py                # App-Factory
│   │   ├── routes/               # Chat, Auth, Dashboard, Admin, Settings
│   │   └── deps.py               # Dependency Injection
│   ├── models/                   # Pydantic Datenmodelle
│   ├── storage/                  # SQLite/PostgreSQL Repositories
│   ├── tools/                    # 13 Agent-Tools
│   │   ├── invoice_parser.py     # Rechnungs-OCR (Claude Vision + Ollama Fallback)
│   │   ├── smartmeter.py         # Smart Meter API (7 österreichische Netzbetreiber)
│   │   ├── tariff_compare.py     # E-Control Stromtarife
│   │   ├── gas_compare.py        # E-Control Gastarife
│   │   ├── beg_advisor.py        # BEG-Vergleich
│   │   ├── switching.py          # Tarifwechsel + Vollmacht-PDF
│   │   ├── load_profile.py       # Lastprofil-Analyse + FDA-Anomalieerkennung
│   │   ├── spot_analysis.py      # ENTSO-E Spot-Tarif-Analyse
│   │   ├── battery_sim.py        # Batteriespeicher-Simulation
│   │   ├── pv_sim.py             # PV/Balkonkraftwerk-Simulation (PVGIS API)
│   │   └── energy_monitor.py     # News, Preise, Förderungen
│   ├── email/                    # Transaktions-Emails
│   ├── prompts/                  # System-Prompt, User-Journey, Persönlichkeit
│   ├── config.py                 # Konfiguration aus .env
│   └── crypto.py                 # Fernet-Verschlüsselung für API-Keys
├── frontend/                     # React SPA (Vite + TailwindCSS v4)
│   ├── src/
│   │   ├── components/Chat/      # Chat-UI mit SSE-Streaming
│   │   ├── components/Dashboard/ # Dashboard-Widgets (live via SSE)
│   │   ├── hooks/                # useChat (SSE), API-Hooks
│   │   └── stores/               # Zustand State Management
│   └── vite.config.ts
├── scripts/
│   └── check_core_boundary.py    # CI-Check: Core-Module ohne Business-Imports
├── homeassistant/                # Home Assistant Integration
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Core / Application Boundary

Die Codebase ist architektonisch in **Core** (wiederverwendbare Bibliothek) und **Application** (Gridbert SaaS) getrennt. Diese Grenze wird per CI enforced und bereitet eine zukünftige Open-Source-Extraktion vor.

### Core-Module (keine Business-Imports)

Diese Module importieren auf Modul-Ebene nichts aus `config`, `storage`, `api`, `prompts`, `email` oder `crypto`:

| Modul | Beschreibung |
|-------|-------------|
| `agent/registry.py` | Generische `ToolRegistry` Klasse |
| `agent/loop.py` | Provider-agnostischer Agent-Loop (`GridbertAgent`) |
| `agent/types.py` | Event-Typen, Tool-Definitionen |
| `llm/` | `LLMProvider` Protocol + Claude/OpenAI Implementierungen |
| `models/` | Alle Pydantic Energie-Datenmodelle |
| `tools/` | Energie-Analyse-Tools (Tarif, Smart Meter, Lastprofil, Spot, Batterie, PV, etc.) |

### Application-Module (Gridbert SaaS)

| Modul | Beschreibung |
|-------|-------------|
| `agent/tool_registry.py` | `build_core_registry()` — verdrahtet Tools mit DB und User-Kontext |
| `api/` | FastAPI Routes, Auth, Rate Limiting, Admin-Dashboard |
| `storage/` | Datenbank-Schema, Repositories |
| `prompts/` | Gridberts Persönlichkeit und User-Journey |
| `email/` | Email-Templates |
| `config.py` | Umgebungskonfiguration |
| `crypto.py` | Fernet-Verschlüsselung für API-Keys |

### Core standalone verwenden

Der Agent-Loop und die Energie-Tools können ohne die Gridbert-App verwendet werden:

```python
from gridbert.agent.registry import ToolRegistry
from gridbert.agent.loop import GridbertAgent
from gridbert.llm import create_provider
from gridbert.tools.tariff_compare import compare_tariffs

# Nur die Tools registrieren die du brauchst
registry = ToolRegistry()
registry.register("compare_tariffs", "Tarife vergleichen", {
    "type": "object",
    "properties": {
        "plz": {"type": "string"},
        "jahresverbrauch_kwh": {"type": "number"},
        "aktueller_lieferant": {"type": "string"},
        "aktueller_energiepreis": {"type": "number"},
        "aktuelle_grundgebuehr": {"type": "number"},
    },
    "required": ["plz", "jahresverbrauch_kwh", "aktueller_lieferant",
                  "aktueller_energiepreis", "aktuelle_grundgebuehr"],
}, compare_tariffs)

# LLM Provider erstellen (Claude oder OpenAI)
provider = create_provider("claude", api_key="sk-...", model="claude-haiku-4-5-20251001")

# Agent mit eigenem System-Prompt starten
agent = GridbertAgent(
    registry, provider,
    system_prompt_builder=lambda: "Du bist ein Energieberater.",
    max_tokens=4096,
)
result = agent.run("Vergleiche Tarife für PLZ 1060, 3200 kWh")
```

### Boundary-Check

```bash
# Prüft dass Core-Module kein Business-Logik importieren
python scripts/check_core_boundary.py
```

## Konfiguration

Umgebungsvariablen in `.env`:

| Variable | Pflicht | Beschreibung |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | Ja* | Server-Fallback API Key (*User können eigenen Key mitbringen) |
| `SECRET_KEY` | Ja (Prod) | JWT-Signing + Fernet-Verschlüsselungskey |
| `DATABASE_URL` | Nein | PostgreSQL URL (default: SQLite) |
| `CLAUDE_MODEL` | Nein | Standard-Modell (default: `claude-haiku-4-5-20251001`) |
| `CLAUDE_MAX_TOKENS` | Nein | Max Response-Tokens (default: `4096`) |
| `CORS_ORIGINS` | Nein | Erlaubte Origins (default: localhost) |
| `ENTSOE_API_KEY` | Nein | Für Spot-Tarif-Analyse |
| `RESEND_API_KEY` | Nein | Transaktions-Emails (Resend) |
| `ADMIN_EMAILS` | Nein | Komma-getrennte Admin-Email-Adressen |
| `ADMIN_TOKEN` | Nein | Admin-Dashboard Auth-Token |
| `WIENER_NETZE_EMAIL` | Nein | Smart Meter Zugang |
| `WIENER_NETZE_PASSWORD` | Nein | Smart Meter Passwort |

### Optionale Dependencies

```bash
pip install -e ".[dev]"        # pytest, ruff
pip install -e ".[analysis]"   # scikit-fda, matplotlib, entsoe-py
pip install -e ".[openai]"     # OpenAI Provider
pip install -e ".[postgres]"   # PostgreSQL (SaaS)
pip install -e ".[ollama]"     # Ollama (self-hosted LLM Fallback)
```

## Lizenz

AGPL-3.0-only — siehe [LICENSE](LICENSE).
