# Gridbert — Iteration Commentary

## v0.1 — User Story 1: "Zeig mir was ich spare"
*2026-02-25 · Projekt hieß vorher "Energie Copilot", heißt jetzt **Gridbert**.*

### Technische Retrospektive (Agent)

Ollama mit Qwen2.5 7B lokal, weil Rechnungsdaten nicht an eine Cloud-API gehen sollen — der Trade-off ist, dass 7B-Modelle kein zuverlässiges Tool-Calling können. llama3.1 hat Tool-Aufrufe als Plaintext ausgegeben statt als strukturierte Calls; Qwen2.5 war marginal besser, aber auch nicht stabil genug. Die Konsequenz: der Agent-Loop ist tot, stattdessen eine hart verdrahtete 5-Schritt-Pipeline. Das LLM extrahiert JSON aus Rechnungstext, alles andere — Tarifvergleich, BEG-Berechnung, Report — ist deterministisches Python. Funktioniert, aber skaliert architektonisch nicht über den einen Use Case hinaus, und die JSON-Extraktion braucht einen Two-Turn-Chat-Hack, weil Qwen2.5 Single-Turn-JSON-Instruktionen ignoriert. E-Control als Tarif-API ist die einzige öffentliche Option in Österreich, antwortet aber regelmäßig nicht innerhalb von 30 Sekunden — Retry mit Backoff ist drin, löst aber nicht das Grundproblem, dass die API offenbar nicht für maschinelle Abfragen gedacht ist.

### Persönliche Reflexion

Es ist irre wie schnell ein erster Prototyp steht. Die größte Herausforderung war im ersten Schritt tatsächlich, die Designprinzipien klar zu bekommen und sich nicht von Hype-Termini aufhalten zu lassen. Bauchweh macht mir noch die Agent Loop, die ich im ersten Case leider nicht "gebraucht" und damit aufgegeben hab. Das kommt aber noch.

Bin schon recht hyped, muss es jetzt aber mal abhängen lassen und vor allem Feedback einholen!

### Frontend Screenshot
`web_ui_v0.1.png` — Einsparungs-Report im Browser: Lieferant, Tarif, BEG-Vergleich, 7Energy-Sektion.

### Links
- GitHub: https://github.com/BMoer/gridbert
