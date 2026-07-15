# V2H Energy Simulator & Self-Sufficiency Analysis

[![Streamlit App](https://static.streamlit.io/badge-gradient.svg)](https://share.streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Conference: ERK 2026](https://img.shields.io/badge/Conference-ERK%202026-blue)](https://www.ieee.si/erk/)

An interactive Vehicle-to-Home (V2H) energy simulator designed to analyze residential self-sufficiency in Ljubljana. This tool was developed under the framework of the European Horizon Europe project **EV4EU** and presented at the **ERK 2026** conference (Portorož, Slovenia).

---

## Project Overview

This repository contains the implementation of a V2H simulation tool that evaluates the impact of integrating bidirectional electric vehicles (EVs) on household energy self-sufficiency. 

The model uses a priority-based heuristic approach to coordinate energy flows within a Home Energy Management System (HEMS) comprising:
* A **6 kWp** photovoltaic (PV) array.
* A **10 kWh** stationary home battery (BESS) — depending on the selected scenario.
* A **60 kWh** electric vehicle (EV) with bidirectional (V2H) capabilities.

This work corresponds to the research paper:  
**"V2H tool for self-sufficiency analysis: selected residential use cases"** (ERK 2026) by Erika Paofai, Tim Marentič, and Matej Zajc (University of Ljubljana / UniLaSalle Amiens).

---

## Streamlit Dashboard Features

The interactive web application allows users to:
1. **Configure Profiles**: Select household consumption archetypes (Standard Family, Teleworker, Energy Saver) and charger power ratings.
2. **Simulate Mobility**: Adjust EV departure/return times, daily travel distance, and target State of Charge (SoC) for departure.
3. **Compare Tariffs**: Integrate real-world electricity tariffs from the Slovenian operator **GEN-I** (active as of Feb 2026).
4. **Visualize Flows**: Interactive Plotly charts displaying real-time battery SoC, grid exchanges, and solar self-consumption.

---

## Installation & Local Setup

### Prerequisites
Make sure you have Python 3.9+ installed.

### 1. Clone the repository
```bash
git clone [https://github.com/YOUR_USERNAME/v2h-energy-simulator.git](https://github.com/YOUR_USERNAME/v2h-energy-simulator.git)
cd v2h-energy-simulator