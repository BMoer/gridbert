# Gridbert — Persönlicher Energie-Agent
# SPDX-License-Identifier: AGPL-3.0-only

"""Uvicorn Entrypoint für gridbert-api CLI Command."""

from __future__ import annotations

import logging


def main() -> None:
    """API Server starten."""
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
    uvicorn.run(
        "gridbert.api.app:create_app",
        factory=True,
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
