# Interactive V2H Energy Simulator (EV4EU)

This repository contains the interactive simulation and optimization tool developed during a research stay at the University of Ljubljana, under the European Horizon Europe project **EV4EU**. 

The tool serves as the computational demonstrator for the paper:  
*"V2H tool for self-sufficiency analysis: selected residential use cases"* (written for ERK 2026, Portorož, Slovenia).

It allows users to simulate, visualize, and compare two distinct energy dispatch strategies for a multi-storage Home Energy Management System (HEMS) incorporating PV generation, a stationary battery (BESS), and a bidirectional electric vehicle (V2H).

---

## Repository Structure

* `app.py`: The main Streamlit application containing both dispatch engines.
* `requirements.txt`: Python package dependencies required to run the simulation.
* `docs/`: Folder containing the draft of the conference paper detailing the MILP mathematical formulation.

---

## Technical Architecture and Dispatch Engines

The simulator embeds two control algorithms to manage the daily 24-hour household energy balance:

### 1. Rule-Based Heuristic
A step-by-step local controller operating hour-by-hour ($t = 0 \dots 23$) using deterministic priority rules:
* **Priority 1 (Direct Solar Cover):** PV generation directly supplies the household demand.
* **Priority 2 (Urgent Charging):** If the EV's State of Charge (SoC) is too low to guarantee the user's departure target by $t_{\text{dep}}$, the system forces maximum-rate charging using solar surplus and grid imports.
* **Priority 3 (Solar Surplus Charging):** Opportunistic charging of the EV using excess PV generation.
* **Priority 4 (V2H Support):** Discharging the EV to support the home load during high-tariff periods, provided the SoC is above the safety floor.

### 2. Mixed-Integer Linear Programming (MILP)
A global optimization engine formulated via the `PuLP` library in Python. Unlike the heuristic approach, the MILP solver considers all 24 hours simultaneously:
* **Objective:** Maximize the Self-Sufficiency Rate (SSR) while minimizing charging costs.
* **Constraints:** Respects real-time dynamic tariffs (e.g., Slovenian GEN-I rates), battery/EV physical limits, degradation concerns, and guarantees the exact departure SoC.
* **Efficiencies:** Separately models charging ($\eta_{\text{chg}} = 92\%$) and discharging ($\eta_{\text{v2h}} = 93\%$) to prevent artificial over-optimization.

---

## Technical Parameters and Reference Data

* **Solar Irradiance:** Hourly profiles extracted from the European Commission JRC's PVGIS SARAH3 database for Ljubljana, Slovenia (46.056°N, 14.506°E).
* **Electricity Tariffs:** Official GEN-I Slovenia "Aktivni cenik" time-of-use tariffs (valid February 2026).
* **Supported EVs:** 
  * Nissan Leaf (40 kWh | Max AC: 6.6 kW | Max V2H: 7.0 kW)
  * Renault 5 E-Tech (52 kWh | Max AC: 11.0 kW | Max V2H: 7.0 kW)
  * Tesla Model 3 (57.5 kWh | Max AC: 11.0 kW | Max V2H: 11.0 kW)

---

## Key Scientific Findings from the Paper

Our benchmark analysis highlights several critical insights for residential self-sufficiency (SSR):
* Unidirectional EV (G2V) charging contributes 0% improvement to the household SSR.
* Activating V2H capabilities adds 14.3 percentage points of SSR in a PV-only system, and 3.2 percentage points if a stationary battery (BESS) is already present.
* Regulatory Framework: Analysis under Slovenian network rules reveals a structural tension between individual V2H optimization and the local community energy-sharing regulation (*souporaba*).

---

## Local Setup

### Prerequisites
Make sure Python 3.9+ is installed on your system.

### 1. Install Dependencies
Clone the repository, open a terminal in the folder, and run:
```bash
pip install -r requirements.txt
```
### 2. Run the Dashboard
To launch the interactive Streamlit interface:
```bash
streamlit run app.py
```
### Project Authors
* Erika Paofai — UniLaSalle Amiens, France (erika.paofai@etu.unilasalle.fr)
* Tim Marentič — University of Ljubljana, FE, Slovenia
* Matej Zajc — University of Ljubljana, FE, Slovenia

### Acknowledgements
This research was conducted during a research stay at the University of Ljubljana (Faculty of Electrical Engineering, Laboratory of Energy Policy), in collaboration with UniLaSalle Amiens.

We gratefully acknowledge the support of the EV4EU project, which has received funding from the European Union’s Horizon Europe research and innovation programme under grant agreement No. 101056765. Special thanks to the laboratory members and academic supervisors for their guidance and resources throughout this work.
