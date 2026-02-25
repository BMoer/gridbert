# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Flask Web-Oberfläche für Gridbert."""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

import markdown
from flask import Flask, Response, render_template, request, stream_with_context

from gridbert.web.sse import cleanup_run, get_run_queue, start_pipeline_run

log = logging.getLogger(__name__)


def create_app() -> Flask:
    """Flask App erstellen."""
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

    @app.route("/")
    def index():  # type: ignore[no-untyped-def]
        return render_template("index.html")

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
                        report_html = markdown.markdown(
                            event["report"],
                            extensions=["tables", "fenced_code"],
                        )
                        data = json.dumps({"html": report_html}, ensure_ascii=False)
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

    return app


def run_web(host: str = "127.0.0.1", port: int = 5000, debug: bool = False) -> None:
    """Gridbert Web-Oberfläche starten."""
    app = create_app()
    print(f"\n⚡ Gridbert Web UI: http://{host}:{port}")
    print("   Öffne den Link im Browser, um loszulegen.\n")
    app.run(host=host, port=port, debug=debug, threaded=True)
