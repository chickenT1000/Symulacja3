"""Simulation package exposing a singleton SimulationEngine instance.
"""
from __future__ import annotations

from .engine import SimulationEngine

# Singleton instance used by Flask routes
_engine: SimulationEngine | None = None

def get_engine() -> SimulationEngine:
    global _engine
    if _engine is None:
        _engine = SimulationEngine()
    return _engine
