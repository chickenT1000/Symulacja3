"""Flask application for the CaCO3–H2SO4 process simulation.
Run on http://localhost:8080
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

import logging  # added for diagnostics

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from simulation.engine import SimulationEngine
from simulation import get_engine

app = Flask(__name__, static_folder="static")
CORS(app)

# ---------------------------------------------------------------------------
# Basic diagnostic logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    filename="speed_debug.log",
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)

def _background_loop(engine: SimulationEngine):
    """
    Background simulation thread.

    Each loop:
    • advances the model by the engine’s fixed timestep
      (`engine.step(engine.timestep)`), **not** by real-time Δt
    • sleeps for `timestep / speed_factor`, so the real-time pace
      changes when the UI posts a new speed factor
        – speed_factor == 1  → 1 physics step / s   (low CPU)
        – speed_factor == 10 → 10 steps / s         (faster sim)
    """
    while engine.running:
        # Advance physics
        engine.step(engine.timestep)
        # Real-time pacing
        sf = max(engine.speed_factor, 0.001)  # avoid division by zero
        # Diagnostic entry for each loop iteration
        logging.info("LOOP speed=%.2f dt=%.2f", engine.speed_factor, engine.timestep)
        time.sleep(engine.timestep / sf)


@app.route("/api/state")
def state():
    """Return the current simulation snapshot as JSON."""
    return jsonify(get_engine().snapshot())


@app.route("/api/start", methods=["POST"])
def start():
    engine = get_engine()
    if not engine.running:
        engine.running = True
        threading.Thread(target=_background_loop, args=(engine,), daemon=True).start()
    return ("", 204)


@app.route("/api/pause", methods=["POST"])
def pause():
    engine = get_engine()
    engine.running = False
    return ("", 204)


@app.route("/api/reset", methods=["POST"])
def reset():
    get_engine().reset()
    return ("", 204)

# -----------------------------------------------------
# Speed-control endpoint
# -----------------------------------------------------

@app.route("/api/speed", methods=["POST"])
def set_speed():
    """
    Set the simulation speed multiplier.
    Expects JSON body: { "factor": <number 0-100> }
    """
    data = request.get_json(silent=True) or {}
    if "factor" not in data:
        return jsonify({"error": "JSON payload must include 'factor'"}), 400

    try:
        factor = float(data["factor"])
    except (TypeError, ValueError):
        return jsonify({"error": "'factor' must be a numeric value"}), 400

    engine = get_engine()
    engine.set_speed(factor)
    # Diagnostic entry for speed changes
    logging.info("SET_SPEED %.2f", factor)
    return ("", 204)


# Serve the single-page front-end
@app.route("/")
@app.route("/<path:path>")
def spa(path="index.html"):
    static_dir = Path(app.static_folder).resolve()
    file_path = static_dir / path
    if file_path.is_file():
        return send_from_directory(static_dir, path)
    # Fallback to index.html for SPA routing
    return send_from_directory(static_dir, "index.html")


if __name__ == "__main__":
    app.run(port=8080, debug=True)
