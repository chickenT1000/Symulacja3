# Process Simulation Specification

## Purpose
Create a web application that simulates the chemical reaction of sulfuric acid with a calcium-carbonate suspension.  
The application must display a P&ID-style diagram with animated flows, pump and agitator status, and liquid levels.

---

## Main process equipment and tags

1. **Buffer tank T-01** (5 m³)  
   • Contains concentrated sulfuric acid.  
   • Discharged to the dilution tank by **pump P-01**.

2. **Pump P-01**  
   • Transfers acid from T-01 to the dilution tank **M-01**.

3. **Dilution tank M-01** (10 m³)  
   • Equipped with agitator **AG-01**.  
   • Demineralized water dosed via valve **V-01** (capacity 4 m³/h).  
   • Computes solution concentration, temperature and heat of dilution.

4. **Transfer pump P-02**  
   • Delivers diluted acid from M-01 to the reactor.

5. **Pressurised reactor R-01** (10 m³ total volume)  
   • Initially charged with 5 m³ of CaCO₃ slurry (10 % w/w).  
   • Generates CO₂ and a pressure rise during reaction.  
   • Fitted with safety valve **PSV-01** opening at **3 bar (g)**  
     (i.e. 4 bar absolute).

---

## Required functionality

* Real-time simulation showing:  
  – Liquid levels in all vessels  
  – Operating state of pumps and agitator  
  – Current concentration, temperature and **gauge pressure** values  
  – **Simulation clock in hh:mm:ss format**
* **Calculations** tab displaying the equations and steps while the simulation is paused.  
* **Charts** tab with online plots of key parameters and event tags (pump start, valve opening, …).  
* **Assumptions** tab describing adopted simplifications (perfect mixing, no flow resistance).  
* **Controls:** Start, **Pause**, Reset buttons.  
* **Speed slider** allowing the user to run the model from **0.1× to 100× real-time**.  
  Charts must update only while the Charts tab is visible.

---

## Simplifying assumptions

1. Perfect mixing with instantaneous mass and energy exchange.  
2. No hydrodynamic modelling (no pressure drops or gradients).  
3. Reaction of CaCO₃ with H₂SO₄ considered instantaneous.  
4. Heat from reaction and dilution included; system treated as adiabatic.

---

## Typical process sequence

1. Start pump P-01 to transfer acid from T-01 to M-01.  
2. Valve V-01 simultaneously feeds demineralised water at 4 m³/h into M-01.  
3. M-01 continuously computes solution concentration and temperature.  
4. When target conditions are reached, pump P-02 sends the mixture to reactor R-01.  
5. Reaction in R-01 increases pressure; if it exceeds 3 bar, PSV-01 opens and the CO₂ flow rate is calculated and displayed.
   (Pressure comparison is done on a gauge basis.)

---

## Technical requirements

* Web application written in Python (Flask) or another suitable framework.  
* Front-end must use an SVG/Canvas library for drawing and animating the P&ID.  
* Real-time charts: **Chart.js 4 (or similar).**  
* Modular structure separating calculation logic from presentation.  
* Application must run on **localhost, port 8080** (not 3000).  
* Provide a `start.bat` script that installs dependencies, launches the local server, and opens a browser window pointing to the running application.

### REST API (JSON)
```
GET  /api/state   ➔ {time, tanks[], ca_mass, pressure_bar_g,
                      running, speed_factor}
POST /api/start
POST /api/pause
POST /api/reset
POST /api/speed   { "factor": <0.1-100> }
```

### Additional implementation notes
* Internal engine tracks absolute pressure; UI and PSV logic use
  `pressure_bar_g = max(0, pressure_bar_abs − 1)`.
* The **speed factor** multiplies the simulation timestep (`dt_sim = dt × factor`)
  and applies consistently to all flow and reaction rates.
