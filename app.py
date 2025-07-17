"""Flask application for the CaCO3–H2SO4 process simulation.
Run on http://localhost:8080
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from simulation.engine import SimulationEngine, get_engine

app = Flask(__name__, static_folder="static")
CORS(app)


def _background_loop(engine: SimulationEngine):
    """Runs the simulation on a background thread."""
    last_time = time.perf_counter()
    while engine.running:
        now = time.perf_counter()
        dt = now - last_time
        last_time = now
        engine.step(dt)
        time.sleep(max(0.05, engine.timestep - dt))  # ~20 Hz


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
