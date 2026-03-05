# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Gridbert?

Personal energy agent for Austrian consumers. Conversational AI that analyzes electricity bills (PDF/image OCR), fetches smart meter data, compares tariffs via E-Control API, evaluates BEG options, and generates savings reports. Built as a SaaS web service with a React frontend and FastAPI backend, powered by Claude API with native tool calling.

## Commands

```bash
# Backend install
pip install -e .           # core
pip install -e ".[dev]"    # with pytest, ruff
pip install -e ".[analysis]"  # scikit-fda, matplotlib, entsoe-py

# Frontend install
cd frontend && npm install

# Run backend (FastAPI + Uvicorn on port 8000)
python3 -m gridbert.api.run

# Run frontend (Vite dev server on port 5173, proxies /api → :8000)
cd frontend && npm run dev

# Run tests
cd /path/to/gridbert && python3 -m pytest -v
python3 -m pytest tests/unit/test_foo.py::test_specific -v

# Lint
python3 -m ruff check gridbert/
python3 -m ruff format gridbert/

# Frontend type check + build
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

## Architecture

### Agent-first design — Claude decides what to do

**`agent/loop.py:GridbertAgent.run()`** is the core. Claude API with native tool calling replaces the old regex-based agent. The LLM decides which tools to call, feeds results back, loops until done. No hardcoded pipeline.

**`agent/tool_registry.py`** maps Python functions → Claude API tool definitions (JSON Schema). `build_default_registry()` registers all tools. To add a new tool: register it in the registry with name, description, input_schema, and handler function.

**`agent/loop.py`** also emits `WIDGET_ADD`/`WIDGET_UPDATE` SSE events when the `add_dashboard_widget` tool is called, so the frontend dashboard updates live during conversation.

### API layer (FastAPI)

```
api/
├── app.py          # Factory: create_app() with CORS, lifespan
├── run.py          # Uvicorn entrypoint (gridbert-api CLI)
├── deps.py         # DI: DbConn, CurrentUserId, CurrentUser (JWT)
└── routes/
    ├── auth.py     # POST /api/auth/register, /api/auth/login, GET /api/auth/me
    ├── chat.py     # POST /api/chat → SSE streaming; GET /api/files, /api/memory, /api/news
    └── dashboard.py # CRUD /api/dashboard/widgets
```

**`POST /api/chat`** is the main endpoint — everything goes through conversation. The SSE stream emits `AgentEvent` objects (text_delta, tool_start, tool_result, widget_add, widget_update, done).

### Storage (SQLAlchemy Core, no ORM)

```
storage/
├── database.py         # Engine, get_connection(), init_db()
├── schema.py           # 6 tables: users, conversations, messages, analyses, user_memory, dashboard_widgets
└── repositories/       # Repository pattern for data access
    ├── user_repo.py
    ├── chat_repo.py
    ├── file_repo.py
    └── memory_repo.py
```

Default: SQLite at `~/.gridbert/gridbert.db`. SaaS: PostgreSQL via `DATABASE_URL`.

### Models (Pydantic)

Split into `models/` package: `invoice.py`, `smart_meter.py`, `tariff.py`, `beg.py`, `report.py`, `load_profile.py`, `spot.py`, `battery.py`, `pv.py`, `gas.py`, `energy_news.py`. All re-exported from `models/__init__.py`.

### Tools (13 registered in tool_registry.py)

```
tools/
├── invoice_parser.py   # Claude Vision (primary) + Ollama (fallback)
├── smartmeter.py       # Wiener Netze PKCE OAuth2
├── tariff_compare.py   # E-Control API (electricity)
├── gas_compare.py      # E-Control API (gas)
├── beg_advisor.py      # BEG comparison (data/beg_providers.json)
├── switching.py        # PDF generation (fpdf2)
├── load_profile.py     # Lastprofil: metrics, FDA anomalies, savings, heatmap/duration curve
├── spot_analysis.py    # Spot tariff analysis (ENTSO-E API), profile cost factor
├── battery_sim.py      # Battery simulation (2/5/10/15 kWh scenarios)
├── pv_sim.py           # PV/BKW simulation (PVGIS API)
├── energy_monitor.py   # Energy news (RSS from ORF + Oesterreichs Energie), Förderungen catalog
└── smartmeter_providers/  # Multi-provider smart meter abstraction
    ├── __init__.py     # SmartMeterProvider protocol, factory, 7 Austrian providers
    ├── wiener_netze.py # Implemented — wraps existing SmartMeterClient
    └── netz_noe.py     # Placeholder (+ 5 more planned: OÖ, Salzburg, Tirol, Steiermark, Kärnten)
```

The `add_dashboard_widget` tool (registered with user context) lets the agent create/update dashboard widgets during conversation. It uses upsert logic (same widget_type → update, new → insert).

### Frontend (React + Vite + TailwindCSS v4)

**Design system**: "Küchentisch-Ingenieur" — warm, analog aesthetic. CSS custom properties in `index.css`:
- Colors: `--bone` (bg), `--ink` (text), `--terracotta` (accent), `--kreide` (cards), `--warm-grau` (muted)
- Fonts: Fraunces (display), Source Serif 4 (body), JetBrains Mono (data)
- Shadows: `--shadow-card`, `--shadow-raised`, `--shadow-floating`

**Dashboard-first architecture** — the dashboard is a live conversation canvas. As the agent analyzes data and calls `add_dashboard_widget`, dashboard cards appear/update in real-time via SSE events.

```
frontend/src/
├── components/
│   ├── Chat/
│   │   ├── ChatDrawer.tsx     # Slide-in panel (420px right side), opens from dashboard
│   │   ├── ChatWindow.tsx     # Standalone chat view (used inside drawer)
│   │   ├── ChatInput.tsx      # Text input + file upload (PDF, images, CSV, Excel)
│   │   └── MessageBubble.tsx  # Markdown rendering + expandable ToolIndicator
│   ├── Dashboard/
│   │   ├── Dashboard.tsx      # CSS Grid orchestrator, dynamic layout based on available data
│   │   ├── KPICard.tsx        # Consumption/savings KPIs (only shown when data exists)
│   │   ├── ChartArea.tsx      # Load profile chart (only shown with consumption_chart widget)
│   │   ├── GridbertArea.tsx   # SVG avatar + speech bubble (renders last assistant message as markdown)
│   │   ├── TaskList.tsx       # "Deine Schritte" — clickable checklist, triggers chat actions
│   │   ├── QuestionArea.tsx   # Inline chat input in dashboard grid
│   │   ├── NewsArea.tsx       # Energy news from ORF RSS (GET /api/news)
│   │   └── DocumentTable.tsx  # User files + knowledge facts + drag-and-drop upload
│   ├── Layout/
│   │   ├── MainLayout.tsx     # Header + Dashboard + ChatDrawer
│   │   └── Header.tsx         # Logo, chat button, conversation selector, user menu
│   └── Auth/                  # LoginPage, RegisterPage (design system styled)
├── hooks/
│   └── useChat.ts             # SSE streaming, widget_add/widget_update event handling
├── stores/
│   ├── chatStore.ts           # Zustand: messages, toolActivity, conversationId
│   ├── dashboardStore.ts      # Zustand: widgets, userFiles, userMemory (reactive, SSE-updated)
│   └── authStore.ts           # JWT token management
└── api/client.ts              # REST helpers (auth, conversations, dashboard, files, memory, news)
```

**Key patterns:**
- `useChatStore.getState()` inside callbacks to avoid stale closures (no deps in useCallback)
- `dashboardStore` is updated both on mount (API fetch) and live via SSE events during conversation
- Dashboard grid adapts: no data → Gridbert spans full top; with KPIs/chart → 3-column layout
- `TaskList` items are clickable buttons that open chat drawer and send prompts to Gridbert
- `QuestionArea` provides an inline chat input embedded in the dashboard grid
- `GridbertArea` speech bubble renders full markdown with scroll overflow
- File uploads: base64-encoded in request body as `attachments[]`
- Vite dev proxy: `/api` → `http://localhost:8000`

### Data flow

1. User sends message via `POST /api/chat` (or clicks a TaskList item / uses QuestionArea)
2. Agent builds system prompt enriched with user memory facts
3. Claude decides which tools to call (invoice OCR, smart meter, tariffs, etc.)
4. Tool results feed back to Claude → loops until final text response
5. `add_dashboard_widget` tool calls emit `widget_add`/`widget_update` SSE events → dashboard updates live
6. Events stream to frontend via SSE → chatStore + dashboardStore update reactively
7. Messages and memory persisted to DB

## Key Rules

- **All prices are BRUTTO** (incl. 20% Austrian VAT). E-Control API returns netto → multiply by 1.2.
- **LLM is ONLY for language** — OCR and conversation. ALL calculations are deterministic Python.
- **No frameworks** — no LangChain, no CrewAI. Agent loop is hand-rolled using anthropic SDK directly.
- **Config** from `.env` via python-dotenv (see `config.py`): `ANTHROPIC_API_KEY`, `DATABASE_URL`, `SECRET_KEY`, `WIENER_NETZE_EMAIL`, `WIENER_NETZE_PASSWORD`.
- **License**: AGPL-3.0-only — all source files need the SPDX header:
  ```python
  # Gridbert — Persönlicher Energie-Agent
  # SPDX-License-Identifier: AGPL-3.0-only
  ```

## Scope

Phase 1 (complete): Agent core + FastAPI backend + auth + chat SSE + storage.
Phase 2 (complete): React SPA with conversational UI + adaptive dashboard.
Phase 3 (complete): 12 tools — load profile, spot tariffs, battery/PV sim, gas, energy monitor.
Phase 4 (complete): Multi-provider smart meter (7 providers), Docker self-hosted, Home Assistant integration.
Phase 5 (WIP): Küchentisch-Ingenieur UI redesign — dashboard-first, live widget canvas, design system. Builds OK but needs debugging.

## Docker Deployment

```bash
# Self-hosted: copy .env.example → .env, set ANTHROPIC_API_KEY, then:
docker compose up -d
# Open http://localhost:5000
```

Multi-stage Dockerfile: Node frontend build → Python runtime. Frontend served as static files via FastAPI `StaticFiles` mount at `/`. Data persisted in `gridbert-data` Docker volume at `/data/gridbert.db`.

## File Upload Flow

1. Frontend `ChatInput` (in ChatDrawer) or `DocumentTable` (drag-and-drop on dashboard) accepts PDF, images, CSV, Excel
2. Files are base64-encoded and sent as `attachments[]` in the `/api/chat` POST body
3. `_build_user_content()` in `loop.py` routes by media type:
   - `application/pdf` → Claude `document` block (native PDF reading)
   - `image/*` → Claude `image` block (Vision)
   - CSV/Excel → `_decode_tabular_file()` decodes to text, inlined in message (50k char limit)
4. A text hint tells Claude the files are inline — no tool call needed to read them

## Optional Dependencies

```bash
pip install -e ".[analysis]"   # scikit-fda, matplotlib, entsoe-py (FDA anomaly detection, visualizations, spot prices)
pip install -e ".[postgres]"   # psycopg (SaaS deployment)
pip install -e ".[ollama]"     # ollama SDK (self-hosted LLM fallback)
```
