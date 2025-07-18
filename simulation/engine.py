"""Basic discrete-time simulation of the CaCO3 + H2SO4 process.
This is intentionally simplified and suitable for educational/demo use.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Dict

R_GAS = 8.314  # J/mol·K
M_CACO3 = 100.09  # kg/kmol
M_H2SO4 = 98.079  # kg/kmol
M_CO2 = 44.01    # kg/kmol
M_H2O = 18.02    # kg/kmol

# Heat capacity of water (J/kg·K)
CP_WATER = 4186
# Heat of reaction for CaCO3 + H2SO4 → CaSO4 + CO2 + H2O (kJ/mol)
HEAT_OF_REACTION = -101.32  # Exothermic


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
        # -------------------------------------------------
        # Operator-controlled devices – all start OFF
        # -------------------------------------------------
        self.P01 = False  # Transfer pump T-01 → M-01
        self.P02 = False  # Transfer pump M-01 → R-01
        self.V01 = False  # Water valve
        self.AG01 = False  # Agitator (visual only)

        # Diagnostics / extra outputs
        self.co2_flow_kg_h: float = 0.0
        self.co2_flow_m3_h: float = 0.0
        self.off_gas_temp_C: float = self.r01.temperature_K - 273.15
        self.humidity_pct: float = 0.0  # relative humidity in reactor headspace
        self.heat_kJ_cum: float = 0.0   # Cumulative heat released from reaction

    def _psat_bar(self, temp_K: float) -> float:
        """
        Calculate saturated vapor pressure of water using Antoine equation.
        Returns pressure in bar.
        """
        # Antoine coefficients for water (valid 1-100°C)
        A = 8.07131
        B = 1730.63
        C = 233.426
        
        # Convert K to °C for the equation
        temp_C = temp_K - 273.15
        
        # Clamp temperature to valid range
        temp_C = max(1.0, min(temp_C, 100.0))
        
        # Calculate log10(P) where P is in mmHg
        log_p_mmHg = A - (B / (C + temp_C))
        
        # Convert mmHg to bar
        p_mmHg = 10 ** log_p_mmHg
        p_bar = p_mmHg * 0.00133322
        
        return p_bar

    def step(self, dt: float):
        """Advance simulation by dt seconds."""
        # dt is already scaled by the caller (background thread) according
        # to `speed_factor`, so we use it directly.

        # Reset per-tick production values
        produced_kmol = 0.0          # CO₂ generated this step [kmol]
        vented_kmol = 0.0            # CO₂ vented through PSV   [kmol]
        self.time_s += dt
        # Acid transfer T-01 → M-01 via P-01 (simplified: 0.5 m3/h when running)
        transfer_rate = 0.5 / 3600.0  # m3/s
        if self.P01 and self.t01.level_m3 > 0 and self.m01.level_m3 < self.m01.volume_m3:
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
        if self.V01 and self.m01.level_m3 < self.m01.volume_m3:
            dVw = min(water_rate * dt, self.m01.volume_m3 - self.m01.level_m3)
            self.m01.level_m3 += dVw
            # dilution, concentration ↓
            if self.m01.level_m3 > 0:
                self.m01.concentration_wt *= (self.m01.level_m3 - dVw) / self.m01.level_m3
        # When M-01 level >2 m3 and conc <60 %, pump P-02 to reactor (1 m3/h)
        p2_rate = 1.0 / 3600.0
        if (
            self.P02
            and self.m01.level_m3 > 0
            and self.r01.level_m3 < self.r01.volume_m3
        ):
            dV2 = min(p2_rate * dt, self.m01.level_m3, self.r01.volume_m3 - self.r01.level_m3)
            self.m01.level_m3 -= dV2
            self.r01.level_m3 += dV2
        else:
            dV2 = 0.0

        # Instantaneous reaction in reactor driven by incremental acid dV2
        if self.r01.concentration_wt < 1e-3 and self.m01.concentration_wt < 60.0:
            # first arrival of acid
            self.r01.concentration_wt = self.m01.concentration_wt
        if dV2 > 0 and self.ca_slurry_mass_kg > 0:
            # moles of H2SO4 in this parcel
            acid_kmol = (
                dV2
                * 1000.0
                * self.m01.concentration_wt
                / 100.0
                / M_H2SO4
            )
            ca_kmol = self.ca_slurry_mass_kg / M_CACO3
            reacted = min(acid_kmol, ca_kmol)
            produced_kmol = reacted  # 1:1 stoichiometry → kmol CO2
            self.ca_slurry_mass_kg -= reacted * M_CACO3
            
            # Heat released from reaction (exothermic)
            # Q = n * ΔH (kJ)
            heat_released_kJ = reacted * abs(HEAT_OF_REACTION)
            self.heat_kJ_cum += heat_released_kJ  # Accumulate total heat released
            
            # Temperature rise calculation
            # Q = m * Cp * ΔT
            # Simplified: assume all heat goes to liquid in reactor
            if self.r01.level_m3 > 0:
                mass_kg = self.r01.level_m3 * 1000  # Assume density = 1000 kg/m³
                delta_T = heat_released_kJ * 1000 / (mass_kg * CP_WATER)  # K
                self.r01.temperature_K += delta_T
            
            # CO2 generation increases pressure (ideal gas, adiabatic in 10 m3)
            if self.r01.level_m3 < self.r01.volume_m3:
                free_vol_m3 = self.r01.volume_m3 - self.r01.level_m3
                T = self.r01.temperature_K
                
                # Add partial pressure from CO2
                p_CO2_Pa = produced_kmol * 1000.0 * R_GAS * T / free_vol_m3
                
                # Add water vapor partial pressure (saturated at reactor temperature)
                p_H2O_bar = self._psat_bar(T)
                p_H2O_Pa = p_H2O_bar * 1e5
                
                # ADD to existing pressure (not replace) - fix for pressure accumulation
                self.pressure_bar_abs += (p_CO2_Pa + p_H2O_Pa) / 1e5

        # PSV opens at 3 barg (i.e. 4 bar absolute)
        if self.pressure_bar_g > 3.0:
            # simple proportional relief back towards 3 barg
            relief = (self.pressure_bar_g - 3.0) * 0.1
            # convert relief (gauge) to absolute delta
            self.pressure_bar_abs -= relief
            # quantify vented moles (ideal gas)
            free_vol_m3 = max(1e-6, self.r01.volume_m3 - self.r01.level_m3)
            deltaP_Pa = relief * 1e5
            vented_kmol = deltaP_Pa * free_vol_m3 / (R_GAS * self.r01.temperature_K) / 1000.0

        # -------------------------------------------------
        # Diagnostics / derived extra variables
        # -------------------------------------------------
        if dt > 0:
            # only show flow when PSV open
            if self.pressure_bar_g > 3.0:
                # Calculate CO2 flow in standard m³/h (at 1 bar, reactor temperature)
                self.co2_flow_m3_h = (
                    vented_kmol * R_GAS * self.r01.temperature_K / 1e5   # m³ at 1 bar
                ) * 3600.0 / dt
                
                # Also calculate mass flow
                self.co2_flow_kg_h = vented_kmol * M_CO2 * 3600.0 / dt
            else:
                self.co2_flow_m3_h = 0.0
                self.co2_flow_kg_h = 0.0
        else:
            self.co2_flow_m3_h = 0.0
            self.co2_flow_kg_h = 0.0

        self.off_gas_temp_C = self.r01.temperature_K - 273.15
        
        # Calculate humidity based on water vapor pressure
        # When PSV is open, assume saturated vapor at reactor temperature
        if self.pressure_bar_g > 3.0:
            p_sat = self._psat_bar(self.r01.temperature_K)
            # Water vapor partial pressure in the gas phase
            p_water = min(p_sat, self.pressure_bar_abs - 1.0)  # Can't exceed total pressure - 1 bar
            self.humidity_pct = (p_water / p_sat) * 100.0
        else:
            self.humidity_pct = 0.0  # No flow, no humidity

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
            "co2_flow_m3_h": self.co2_flow_m3_h,
            "co2_flow_kg_h": self.co2_flow_kg_h,
            "off_gas_temp_C": self.off_gas_temp_C,
            "humidity_pct": self.humidity_pct,
            "heat_kJ_cum": self.heat_kJ_cum,
            "devices": {
                "P01": self.P01,
                "P02": self.P02,
                "V01": self.V01,
                "AG01": self.AG01,
            },
        }

    # -----------------------------------------------------
    # Derived properties
    # -----------------------------------------------------

    @property
    def pressure_bar_g(self) -> float:
        """Gauge pressure (relative to 1 bar atmosphere)."""
        return max(0.0, self.pressure_bar_abs - 1.0)

    # -----------------------------------------------------
    # Device control helper (called by Flask /api/device)
    # -----------------------------------------------------
    def set_device(self, dev_id: str, on: bool) -> None:
        mapping = {
            "P01": "P01",
            "P02": "P02",
            "V01": "V01",
            "AG01": "AG01",
        }
        attr = mapping.get(dev_id.upper())
        if attr is None:
            raise ValueError(f"Unknown device id '{dev_id}'")
        setattr(self, attr, bool(on))
