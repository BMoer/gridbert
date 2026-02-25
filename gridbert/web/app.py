# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Flask Web-Oberfläche für Gridbert."""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

import markdown as md
from flask import Flask, Response, render_template, request, stream_with_context

from gridbert.storage import GridbertStorage
from gridbert.web.sse import cleanup_run, get_run_queue, start_pipeline_run

log = logging.getLogger(__name__)


def create_app() -> Flask:
    """Flask App erstellen."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

    @app.route("/")
    def index():  # type: ignore[no-untyped-def]
        # Profil laden für vorausgefüllte Felder
        try:
            storage = GridbertStorage()
            profile = storage.get_profile()
            last = storage.get_last_analysis()
            storage.close()
        except Exception:
            profile = {}
            last = None
        return render_template("index.html", profile=profile, last_analysis=last)

    @app.route("/analyze", methods=["POST"])
    def analyze():  # type: ignore[no-untyped-def]
        """Rechnung hochladen, Pipeline starten, Progress-Seite zeigen."""
        file = request.files.get("rechnung")
        if not file or not file.filename:
            return render_template("index.html", error="Bitte eine Rechnung hochladen."), 400

        # Datei in Temp-Verzeichnis speichern
        tmpdir = tempfile.mkdtemp(prefix="gridbert_")
        filename = file.filename
        filepath = Path(tmpdir) / filename
        file.save(filepath)

        wn_email = request.form.get("wn_email", "").strip()
        wn_password = request.form.get("wn_password", "").strip()

        run_id = start_pipeline_run(filepath, wn_email, wn_password)
        return render_template("progress.html", run_id=run_id)

    @app.route("/stream/<run_id>")
    def stream(run_id: str):  # type: ignore[no-untyped-def]
        """SSE-Endpoint: Pipeline-Fortschritt streamen."""
        q = get_run_queue(run_id)
        if q is None:
            return "Run nicht gefunden", 404

        def generate():  # type: ignore[no-untyped-def]
            while True:
                try:
                    event = q.get(timeout=300)  # 5 min max warten
                except Exception:
                    yield "event: error\ndata: {\"message\": \"Timeout — Pipeline hat zu lange gedauert.\"}\n\n"
                    cleanup_run(run_id)
                    break

                if event.get("step") == "complete":
                    if event["status"] == "done":
                        report_html = md.markdown(
                            event["report"],
                            extensions=["tables", "fenced_code"],
                        )
                        data = json.dumps({
                            "html": report_html,
                            "analysis_id": event.get("analysis_id"),
                        }, ensure_ascii=False)
                        yield f"event: complete\ndata: {data}\n\n"
                    else:
                        data = json.dumps(
                            {"message": event.get("message", "Unbekannter Fehler")},
                            ensure_ascii=False,
                        )
                        yield f"event: error\ndata: {data}\n\n"
                    cleanup_run(run_id)
                    break
                else:
                    data = json.dumps(event, ensure_ascii=False)
                    yield f"event: progress\ndata: {data}\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    @app.route("/history")
    def history():  # type: ignore[no-untyped-def]
        """Vergangene Analysen anzeigen."""
        try:
            storage = GridbertStorage()
            analyses = storage.get_analyses(limit=20)
            storage.close()
        except Exception:
            analyses = []
        return render_template("history.html", analyses=analyses)

    @app.route("/history/<int:analysis_id>")
    def history_detail(analysis_id: int):  # type: ignore[no-untyped-def]
        """Einzelne Analyse anzeigen."""
        try:
            storage = GridbertStorage()
            analyses = storage.get_analyses(limit=100)
            storage.close()
            analysis = next((a for a in analyses if a["id"] == analysis_id), None)
        except Exception:
            analysis = None

        if not analysis or not analysis.get("report_markdown"):
            return "Analyse nicht gefunden", 404

        report_html = md.markdown(
            analysis["report_markdown"],
            extensions=["tables", "fenced_code"],
        )
        return render_template("history_detail.html", analysis=analysis, report_html=report_html)

    @app.route("/download/switching/<int:analysis_id>")
    def download_switching(analysis_id: int):  # type: ignore[no-untyped-def]
        """Tarifwechsel-Vollmacht als PDF herunterladen."""
        from flask import send_file

        from gridbert.models import Invoice, Tariff
        from gridbert.tools.switching import generate_switching_pdf

        try:
            storage = GridbertStorage()
            analyses = storage.get_analyses(limit=100)
            profile = storage.get_profile()
            storage.close()
            analysis = next((a for a in analyses if a["id"] == analysis_id), None)
        except Exception:
            return "Fehler beim Laden", 500

        if not analysis or not analysis.get("raw_json"):
            return "Analyse nicht gefunden", 404

        raw = json.loads(analysis["raw_json"])
        inv_data = raw.get("invoice", {})
        tc_data = raw.get("tariff_comparison", {})
        alts = tc_data.get("alternativen", [])
        if not alts:
            return "Kein Wechsel-Tarif vorhanden", 404

        invoice = Invoice(**inv_data)
        best = Tariff(**alts[0])
        pdf_path = generate_switching_pdf(invoice, best, profile)
        return send_file(str(pdf_path), as_attachment=True, download_name="tarifwechsel_vollmacht.pdf")

    @app.route("/download/beg/<int:analysis_id>")
    def download_beg(analysis_id: int):  # type: ignore[no-untyped-def]
        """BEG-Beitritts-Checkliste als PDF herunterladen."""
        from flask import send_file

        from gridbert.models import BEGCalculation, Invoice
        from gridbert.tools.switching import generate_beg_joining_pdf

        try:
            storage = GridbertStorage()
            analyses = storage.get_analyses(limit=100)
            profile = storage.get_profile()
            storage.close()
            analysis = next((a for a in analyses if a["id"] == analysis_id), None)
        except Exception:
            return "Fehler beim Laden", 500

        if not analysis or not analysis.get("raw_json"):
            return "Analyse nicht gefunden", 404

        raw = json.loads(analysis["raw_json"])
        inv_data = raw.get("invoice", {})
        beg_data = raw.get("beg_comparison", {})
        optionen = beg_data.get("optionen", [])
        # Beste BEG = erste mit positiver Ersparnis
        profitable = [o for o in optionen if o.get("aktueller_preis_ct_kwh", 0) > o.get("beg_preis_ct_kwh", 999)]
        if not profitable:
            return "Keine profitable BEG vorhanden", 404

        invoice = Invoice(**inv_data)
        beg = BEGCalculation(**profitable[0])
        netzbetreiber = raw.get("tariff_comparison", {}).get("netzbetreiber", "")
        pdf_path = generate_beg_joining_pdf(invoice, beg, profile, netzbetreiber)
        return send_file(str(pdf_path), as_attachment=True, download_name="beg_beitritt.pdf")

    @app.route("/chat/<int:analysis_id>", methods=["POST"])
    def chat(analysis_id: int):  # type: ignore[no-untyped-def]
        """Chat-Endpoint: Streaming-Antwort auf Rückfrage."""
        from gridbert.web.chat import chat_stream

        data = request.get_json(silent=True) or {}
        message = data.get("message", "").strip()
        history = data.get("history", [])

        if not message:
            return "Keine Nachricht", 400

        # Report-Markdown aus DB laden
        try:
            storage = GridbertStorage()
            analyses = storage.get_analyses(limit=100)
            storage.close()
            analysis = next((a for a in analyses if a["id"] == analysis_id), None)
        except Exception:
            analysis = None

        report_md = analysis.get("report_markdown", "") if analysis else ""

        def generate():  # type: ignore[no-untyped-def]
            for token in chat_stream(message, report_md, history):
                escaped = json.dumps(token, ensure_ascii=False)
                yield f"data: {escaped}\n\n"
            yield "data: [DONE]\n\n"

        return Response(
            stream_with_context(generate()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    return app


def run_web(host: str = "127.0.0.1", port: int = 5000, debug: bool = False) -> None:
    """Gridbert Web-Oberfläche starten."""
    app = create_app()
    print(f"\n⚡ Gridbert Web UI: http://{host}:{port}")
    print("   Öffne den Link im Browser, um loszulegen.\n")
    app.run(host=host, port=port, debug=debug, threaded=True)
