# Gridbert — Project Conventions

## What is this?
Gridbert is a personal energy agent for Austrian consumers. It analyzes electricity bills, fetches smart meter data, compares tariffs, and generates savings reports.

## Tech Stack
- **Python 3.11+**, no async
- **Ollama** (local LLM) — llama3.1 for text, llava for vision. NO cloud APIs.
- **Pydantic** for data models
- **httpx** for HTTP
- **pdfplumber** for PDF processing

## Architecture
- Simple agent loop in `agent.py` — NO frameworks (no LangChain, no CrewAI)
- Tools are plain Python functions in `gridbert/tools/`
- LLM is ONLY used for language (OCR, conversation, report text). ALL calculations are deterministic Python.
- State is a plain dict passed between agent turns
- Credentials stay local (`.env` file)

## Project Structure
```
gridbert/
├── gridbert/
│   ├── agent.py          # Agent loop (LLM + tool calling)
│   ├── config.py         # Settings from .env
│   ├── main.py           # CLI entry point
│   ├── models.py         # Pydantic data models
│   ├── personality.py    # Gridbert system prompt & tone
│   ├── report.py         # Markdown report generation
│   └── tools/
│       ├── beg_advisor.py     # 7Energy BEG calculation
│       ├── invoice_parser.py  # Bill OCR via Ollama Vision
│       ├── smartmeter.py      # Wiener Netze Smart Meter API
│       └── tariff_compare.py  # E-Control tariff comparison
```

## Key Rules
- All prices are BRUTTO (incl. 20% Austrian VAT)
- Never let the LLM do math — all calculations in Python
- No over-engineering: no ORM, no DB, no async, plain dicts and JSON
- License: AGPL-3.0 — all source files need the SPDX header

## Running
```bash
pip install -e .
gridbert rechnung.pdf --wn-email user@example.com --wn-password secret
```

## Iteration Scope
Currently: User Story 1 ("Zeig mir was ich spare") — full pipeline, minimal depth.
NOT in scope: continuous monitoring, device disaggregation, PV optimization, dynamic tariffs.
