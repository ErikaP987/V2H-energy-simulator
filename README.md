# Interactive V2H Energy Simulator (EV4EU)

This repository contains the interactive simulation and optimization tool developed during a research stay at the University of Ljubljana, under the framework of the European Horizon Europe project EV4EU. 

The tool serves as the computational demonstrator for the paper:  
"V2H tool for self-sufficiency analysis: selected residential use cases" (ERK 2026, Portorož, Slovenia).

The application allows users to simulate, visualize, and compare two distinct energy dispatch strategies for a multi-storage Home Energy Management System (HEMS) incorporating PV generation, a stationary battery (BESS), and a bidirectional electric vehicle (V2H).

---

## Technical Architecture and Dispatch Engines

The simulator embeds two distinct control algorithms to manage the daily 24-hour household energy balance:

### 1. Rule-Based Heuristic
A step-by-step local controller operating hour-by-hour ($t = 0 \dots 23$) using deterministic priority rules:
* Priority 1 (Direct Solar Cover): PV generation directly supplies the household demand.
* Priority 2 (Urgent Charging): If the EV's State of Charge (SoC) is too low to guarantee the user's departure target by $t_{\text{dep}}$, the system forces maximum-rate charging using solar surplus and grid imports.
* Priority 3 (Solar Surplus Charging): Opportunistic charging of the EV using excess PV generation.
* Priority 4 (V2H Support): Discharging the EV to support the home load during high-tariff periods, provided the SoC is above the safety floor.

### 2. Mixed-Integer Linear Programming - MILP
A global optimization engine formulated via the PuLP library in Python. Unlike the heuristic approach, the MILP solver considers all 24 hours simultaneously:
* Objective: Maximize the Self-Sufficiency Rate (SSR) while minimizing charging costs.
* Constraints: Respects real-time dynamic tariffs (e.g., Slovenian GEN-I rates), battery/EV physical limits, degradation concerns, and guarantees the exact departure SoC.
* Efficiencies: Separately models charging ($\eta_{\text{chg}} = 92\%$) and discharging ($\eta_{\text{v2h}} = 93\%$) to prevent artificial over-optimization.

---

## Data Sources

* Solar Irradiance: Hourly profiles extracted from the European Commission JRC's PVGIS SARAH3 database for Ljubljana, Slovenia (46.056°N, 14.506°E).
* Electricity Tariffs: Official GEN-I Slovenia "Aktivni cenik" time-of-use tariffs (valid February 2026).
* Load Profiles: Household consumption archetypes adapted from Fraunhofer ISE and Eurostat.

---

## Local Setup

### Prerequisites
Make sure Python 3.9+ is installed on your system.

### 1. Install Dependencies
Clone the repository, open a terminal in the folder, and run:
```bash
pip install -r requirements.txt
