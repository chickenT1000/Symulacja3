"""Basic discrete-time simulation of the CaCO3 + H2SO4 process.
This is intentionally simplified and suitable for educational/demo use.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict

R_GAS = 8.314  # J/mol·K
M_CACO3 = 100.09  # kg/kmol
M_H2SO4 = 98.079  # kg/kmol


@dataclass
class Vessel:
    name: str
    volume_m3: float
    level_m3: float
    temperature_K: float
    concentration_wt: float  # H2SO4 wt-% for acid vessels


class SimulationEngine:
    # Run loop target period – one physics step per real-time second
    timestep = 1.0  # [s]

    def __init__(self):
        self.reset()

    # -----------------------------------------------------
    # Public API
    # -----------------------------------------------------
    running: bool = False

    def reset(self):
        # Vessels
        self.t01 = Vessel("T-01", 5.0, 5.0, 298.0, 98.0)
        self.m01 = Vessel("M-01", 10.0, 0.0, 298.0, 0.0)
        self.r01 = Vessel("R-01", 10.0, 5.0, 298.0, 0.0)
        # Reaction data
        self.ca_slurry_mass_kg = 5.0 * 1000.0 * 0.10  # 5 m3 × 1000 kg/m3 × 10 %
        # absolute pressure in bar (1 bar = atmospheric, so 0 barg)
        self.pressure_bar_abs = 1.0
        self.time_s = 0.0
        # simulation speed multiplier (1.0 = real-time, 10 = 10× faster, etc.)
        self.speed_factor = 1.0

    def step(self, dt: float):
        """Advance simulation by dt seconds."""
        # dt is already scaled by the caller (background thread) according
        # to `speed_factor`, so we use it directly.
        self.time_s += dt
        # Acid transfer T-01 → M-01 via P-01 (simplified: 0.5 m3/h when running)
        transfer_rate = 0.5 / 3600.0  # m3/s
        if self.t01.level_m3 > 0 and self.m01.level_m3 < self.m01.volume_m3:
            dV = min(transfer_rate * dt, self.t01.level_m3)
            self.t01.level_m3 -= dV
            self.m01.level_m3 += dV
            # Mix concentration in M-01 (simple mass balance)
            self.m01.concentration_wt = (
                self.m01.concentration_wt * (self.m01.level_m3 - dV)
                + self.t01.concentration_wt * dV
            ) / self.m01.level_m3
        # Water feed V-01 (4 m3/h)
        water_rate = 4.0 / 3600.0  # m3/s
        if self.m01.level_m3 < self.m01.volume_m3:
            dVw = min(water_rate * dt, self.m01.volume_m3 - self.m01.level_m3)
            self.m01.level_m3 += dVw
            # dilution, concentration ↓
            if self.m01.level_m3 > 0:
                self.m01.concentration_wt *= (self.m01.level_m3 - dVw) / self.m01.level_m3
        # When M-01 level >2 m3 and conc <60 %, pump P-02 to reactor (1 m3/h)
        p2_rate = 1.0 / 3600.0
        if self.m01.level_m3 > 2.0 and self.m01.concentration_wt < 60.0 and self.r01.level_m3 < self.r01.volume_m3:
            dV2 = min(p2_rate * dt, self.m01.level_m3, self.r01.volume_m3 - self.r01.level_m3)
            self.m01.level_m3 -= dV2
            self.r01.level_m3 += dV2
        # Instantaneous reaction in reactor when acid present
        if self.r01.concentration_wt < 1e-3 and self.m01.concentration_wt < 60.0:
            # first arrival of acid
            self.r01.concentration_wt = self.m01.concentration_wt
        if self.r01.concentration_wt > 0 and self.ca_slurry_mass_kg > 0:
            # stoichiometric reaction: CaCO3 + H2SO4 → CaSO4 + CO2 + H2O
            acid_moles = (
                self.r01.level_m3 * 1000.0 * self.r01.concentration_wt / 100.0 / M_H2SO4 * 1000.0
            )
            ca_moles = self.ca_slurry_mass_kg / M_CACO3 * 1000.0
            reacted = min(acid_moles, ca_moles)
            self.ca_slurry_mass_kg -= reacted * M_CACO3 / 1000.0
            # CO2 generation increases pressure (ideal gas, adiabatic in 10 m3)
            if self.r01.level_m3 < self.r01.volume_m3:
                free_vol_m3 = self.r01.volume_m3 - self.r01.level_m3
                n_CO2 = reacted  # kmol
                T = self.r01.temperature_K
                p_Pa = n_CO2 * 1000.0 * R_GAS * T / free_vol_m3
                self.pressure_bar_abs = p_Pa / 1e5

        # PSV opens at 3 barg (i.e. 4 bar absolute)
        if self.pressure_bar_g > 3.0:
            # simple proportional relief back towards 3 barg
            relief = (self.pressure_bar_g - 3.0) * 0.1
            # convert relief (gauge) to absolute delta
            self.pressure_bar_abs -= relief

    # -----------------------------------------------------
    # Convenience helpers
    # -----------------------------------------------------
    def set_speed(self, factor: float):
        """Set simulation speed multiplier (0 .. 100)."""
        # clamp to sane range
        self.speed_factor = max(0.0, min(factor, 100.0))

    def snapshot(self) -> Dict:
        return {
            "time": self.time_s,
            "tanks": [asdict(v) for v in (self.t01, self.m01, self.r01)],
            "ca_mass": self.ca_slurry_mass_kg,
            "pressure_bar_abs": self.pressure_bar_abs,
            "pressure_bar_g": self.pressure_bar_g,
            "running": self.running,
            "speed_factor": self.speed_factor,
        }

    # -----------------------------------------------------
    # Derived properties
    # -----------------------------------------------------

    @property
    def pressure_bar_g(self) -> float:
        """Gauge pressure (relative to 1 bar atmosphere)."""
        return max(0.0, self.pressure_bar_abs - 1.0)
