# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Pipeline-Runner mit Thread + Queue für SSE-Progress."""

from __future__ import annotations

import logging
import queue
import shutil
import threading
import uuid
from pathlib import Path

log = logging.getLogger(__name__)

# Aktive Pipeline-Runs: run_id → Queue
_active_runs: dict[str, queue.Queue] = {}


def start_pipeline_run(
    rechnung_path: Path,
    wn_email: str = "",
    wn_password: str = "",
) -> str:
    """Pipeline im Hintergrund-Thread starten, run_id zurückgeben."""
    run_id = uuid.uuid4().hex[:12]
    q: queue.Queue = queue.Queue()
    _active_runs[run_id] = q

    def _run() -> None:
        def on_progress(step_id: str, status: str, message: str) -> None:
            q.put({"step": step_id, "status": status, "message": message})

        try:
            from gridbert.main import run_pipeline

            report, analysis_id = run_pipeline(
                rechnung_path=rechnung_path,
                wn_email=wn_email,
                wn_password=wn_password,
                on_progress=on_progress,
            )
            q.put({"step": "complete", "status": "done", "report": report, "analysis_id": analysis_id})
        except Exception as e:
            log.exception("Pipeline fehlgeschlagen")
            q.put({"step": "complete", "status": "error", "message": str(e)})
        finally:
            # Temp-Verzeichnis aufräumen
            try:
                tmpdir = rechnung_path.parent
                if tmpdir.name.startswith("gridbert_"):
                    shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass

    thread = threading.Thread(target=_run, daemon=True, name=f"gridbert-{run_id}")
    thread.start()
    return run_id


def get_run_queue(run_id: str) -> queue.Queue | None:
    """Queue für einen laufenden Run holen."""
    return _active_runs.get(run_id)


def cleanup_run(run_id: str) -> None:
    """Abgeschlossenen Run aufräumen."""
    _active_runs.pop(run_id, None)
