# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║            V2H ENERGY SIMULATOR  —  EV4EU / Erasmus 2026                     ║
# ║            Vehicle-to-Home · Ljubljana · Streamlit Dashboard                 ║
# ╠══════════════════════════════════════════════════════════════════════════════╣
# ║  STRUCTURE                                                                   ║
# ║  1. PAGE CONFIG & CSS       — Streamlit layout and custom styling            ║
# ║  2. CONSTANTS & DATABASE    — EV specs, efficiency values, irradiance data   ║
# ║  3. SIMULATION ENGINE       — Core 24-slot heuristic decision loop           ║
# ║  4. USER INPUTS (SIDEBAR)   — Interactive parameter controls                 ║
# ║  5. OUTPUT — DASHBOARD      — Charts, KPIs, scenario comparison              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# SIMULATION LOGIC SUMMARY
# ─────────────────────────
# At each hourly time step t = 0 to 23, the engine applies a priority heuristic:
#
#   Priority 1 — Solar covers house directly    dp = min(prd, cns)
#   Priority 2 — If urgent (SOC too low to reach departure target):
#                   Charge from solar surplus + grid   [beta = 1]
#   Priority 3 — If solar surplus and not urgent:
#                   Charge EV from free solar           [beta = 1]
#   Priority 4 — No surplus, not urgent:
#                   V2H discharge if SOC > floor        [beta = 0]
#
#   Constraint: beta in {0, 1}  — no simultaneous charge AND discharge
#   Constraint: SOC in [soc_floor, cap]  at every slot
#   Constraint: SOC >= soc_target  at departure slot
#   Constraint: Only PV surplus can export to grid (EV cannot export)
#
# KEY REFERENCES
# ──────────────
#   PVGIS SARAH3            — European Commission JRC (solar irradiance data)
#   GEN-I Slovenia          — Official electricity tariffs, valid 06 Feb. 2026
#   Fraunhofer ISE (2023)   — Consumption profiles
#   Eurostat (2022)         — Residential consumption statistics
#   IEC 62196 / Yilmaz & Krein (2013) — Charging efficiency eta = 92%
#   CHAdeMO (2022)          — V2H discharge efficiency eta = 93%
#   Xu et al. (2018)        — Battery degradation model, Energy & Environ. Sci.
#   Kempton & Tomic (2005)  — V2H fundamentals, J. Power Sources
#   EV4EU Project (2022-2025) — ev4eu.eu

# ─────────────────────────────────────────────────────────────────
# DEPENDENCIES
# ─────────────────────────────────────────────────────────────────
import streamlit as st          # Web dashboard framework
import numpy as np              # Numerical operations
import plotly.graph_objects as go  # Interactive charts
import time                     # Used for animation delay in play mode

# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG & GLOBAL CSS
# ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="V2H Simulator · EV4EU", layout="wide", page_icon="⚡")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500&family=Outfit:wght@300;400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"] {
    background: #F7F8FA !important;
    font-family: 'Outfit', sans-serif !important;
}
[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #EAECF0 !important;
    min-width: 264px !important; max-width: 264px !important;
}
[data-testid="stSidebar"] * { font-family: 'Outfit', sans-serif !important; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,[data-testid="stSidebar"] h3 {
    font-size: 12px !important; font-weight: 700 !important;
    letter-spacing: 0.03em !important; text-transform: uppercase !important;
    color: #1BB87F !important; margin: 8px 0 3px 0 !important; padding: 0 !important;
}
[data-testid="stSidebar"] .stSlider { margin-bottom: -10px !important; }
[data-testid="stSidebar"] .stSlider > div { padding-top: 0px !important; padding-bottom: 0px !important; }
[data-testid="stSidebar"] .stSlider [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] .stSelectbox [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] .stNumberInput [data-testid="stWidgetLabel"] p,
[data-testid="stSidebar"] .stToggle [data-testid="stWidgetLabel"] p { font-size: 11px !important; color: #6B7280 !important; margin-bottom: 0 !important; }
[data-testid="stSidebar"] div[data-baseweb="select"] > div { font-size: 12px !important; }
[data-testid="stSidebar"] .stCaption p { font-size: 10px !important; color: #9CA3AF !important; margin-top: -4px !important; margin-bottom: 0 !important; }
[data-testid="stSidebar"] .stExpander { margin-top: 6px !important; }
[data-testid="stSidebar"] .stExpander summary { font-size: 12px !important; font-weight: 700 !important; color: #1BB87F !important; text-transform: uppercase !important; }
section[data-testid="stSidebar"] > div { padding-top: 4px !important; padding-bottom: 2px !important; }
/* Force padding inside bordered containers to prevent overflow */
[data-testid="stVerticalBlock"] > [data-testid="element-container"] > div[data-testid="stVerticalBlock"] {
    background: #FFFFFF !important; border: 1px solid #E5E7EB !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
    padding-bottom: 16px !important;
    overflow: hidden !important;
}
[data-testid="stMetric"] {
    background: #F9FAFB !important; border: 1px solid #F0F0F2 !important;
    border-radius: 10px !important; padding: 10px 12px !important;
}
[data-testid="stMetricLabel"] p {
    font-family: 'IBM Plex Mono', monospace !important; font-size: 10px !important;
    color: #9CA3AF !important; text-transform: uppercase !important; letter-spacing: 0.06em !important;
}
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace !important; font-size: 18px !important;
    color: #111827 !important; font-weight: 500 !important;
}
[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, #1BB87F, #0EA5C9) !important; border-radius: 99px !important;
}
[data-testid="stProgressBar"] { background: #F0F1F3 !important; border-radius: 99px !important; }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 2px; }
.sec-title {
    font-family: 'Outfit', sans-serif; font-size: 11px; font-weight: 600;
    letter-spacing: 0.07em; text-transform: uppercase; color: #6B7280; margin-bottom: 6px;
}
.kpi-pill {
    display: inline-flex; align-items: center; gap: 5px;
    border-radius: 7px; padding: 4px 10px; font-size: 12px;
    font-family: 'IBM Plex Mono', monospace;
}
.pill-green { background:#F0FDF4; border:1px solid #BBF7D0; color:#166534; }
.pill-red   { background:#FEF2F2; border:1px solid #FECACA; color:#991B1B; }
.pill-amber { background:#FFFBEB; border:1px solid #FDE68A; color:#92400E; }
.pill-blue  { background:#EFF6FF; border:1px solid #BFDBFE; color:#1E40AF; }
.badge {
    display:inline-block; padding:2px 8px; border-radius:99px;
    font-family:'IBM Plex Mono',monospace; font-size:10px; font-weight:500;
}
.badge-green { background:#DCFCE7; color:#166534; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — CONSTANTS & DATABASE
# ═══════════════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────
# EV DATABASE
# Each entry contains the vehicle's usable battery capacity (kWh),
# maximum AC charge power (kW), maximum V2H discharge power (kW),
# and energy consumption per 100 km (kWh/100km).
# ─────────────────────────────────────────────────────────────────
db_voitures = {
    "Nissan Leaf (40 kWh)":      {"capacite_utile": 39.0,  "puissance_charge_max": 6.6,  "puissance_v2h_max": 7.0,  "conso_100km": 17.0},
    "Renault 5 E-Tech (52 kWh)": {"capacite_utile": 52.0,  "puissance_charge_max": 11.0, "puissance_v2h_max": 7.0,  "conso_100km": 15.5},
    "Tesla Model 3 (57.5 kWh)":  {"capacite_utile": 57.5,  "puissance_charge_max": 11.0, "puissance_v2h_max": 11.0, "conso_100km": 14.5},
    "Custom":                     {"capacite_utile": 60.0,  "puissance_charge_max": 7.4,  "puissance_v2h_max": 7.4,  "conso_100km": 16.0}
}

# ─────────────────────────────────────────────────────────────────
# EFFICIENCY CONSTANTS
# η_chg: fraction of AC energy actually stored in the battery
# η_v2h: fraction of battery energy actually delivered to the house
# Source: IEC 62196 / Yilmaz & Krein (2013) · CHAdeMO (2022)
# ─────────────────────────────────────────────────────────────────
ETA_CHG = 0.92   # AC → battery charge efficiency  (92%)
ETA_V2H = 0.93   # battery → AC V2H discharge efficiency  (93%)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — SIMULATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
# Core function: runs the 24-slot hourly heuristic simulation.
# Decorated with @st.cache_data so Streamlit only recomputes when
# input parameters actually change (avoids rerunning on every UI interaction).
# ───────────────────────────────────────────────────────────────────────────────
@st.cache_data
def calculer_simulation(profil_maison, solaire, pv_rated_power, modele_choisi,
                         puissance_borne, part_en_journee, h_retour, choix_depart,
                         soc_plug_in, soc_plug_out, soc_sec, mon_tarif,
                         distance_km, feed_in_tariff,
                         cap_utile, p_chg_max, p_v2h_max, conso_100km, mois):

    # ── Physical limits ──────────────────────────────────────────────────────
    cap   = cap_utile                        # usable battery capacity [kWh]
    p_chg = min(p_chg_max, puissance_borne)  # effective charge power = min(EV max, charger) [kW]
    p_v2h = min(p_v2h_max, puissance_borne)  # effective V2H power = min(EV max, charger) [kW]
    SLOT  = 1.0                              # time resolution: 1 hour per slot [h]

    # ── Solar irradiance data ────────────────────────────────────────────────
    # G(i) in W/m² — PVGIS SARAH3, Ljubljana (46.056°N, 14.506°E)
    # Slope 35°, Azimuth 0° (south-facing), monthly averages
    # Source: European Commission Joint Research Centre
    irr_data = {
        "June":     [0,0,0,0,32.28,95.44,242.87,412.28,578.53,695.03,
                     744.62,738.06,700.37,595.92,474.22,353.08,209.94,78.13,24.72,0,0,0,0,0],
        "March":    [0,0,0,0,0,1.36,40.52,183.53,386.34,510.78,
                     570.86,610.59,561.86,494.98,388.31,252.24,110.67,0.68,0,0,0,0,0,0],
        "December": [0,0,0,0,0,0,0,16.26,59.38,223.14,
                     247.85,268.58,249.8,221.37,140.93,0.57,0,0,0,0,0,0,0,0],
    }
    irr = irr_data[mois]  # select the active month's irradiance profile

    # ── Household consumption profiles ───────────────────────────────────────
    # Hourly demand in kW for each of the 24 hours of the day.
    # Archetypes based on Fraunhofer ISE (2023) and Eurostat (2022).
    cb = {
        "Standard Family (Morning and evening peaks)":
            [0.2,0.15,0.15,0.15,0.2,0.3,0.59,0.74,0.39,0.3,0.25,0.35,0.49,0.35,0.25,0.3,0.39,0.74,1.08,1.23,0.89,0.59,0.39,0.25],
        "Remote Worker (Continuous consumption)":
            [0.23,0.17,0.17,0.17,0.23,0.28,0.45,0.56,0.68,0.68,0.73,0.79,0.84,0.79,0.68,0.56,0.51,0.68,0.84,0.84,0.68,0.45,0.28,0.23],
        "Thrifty (Low baseline)":
            [0.2,0.2,0.2,0.2,0.2,0.3,0.5,0.6,0.4,0.3,0.3,0.4,0.6,0.4,0.3,0.3,0.4,0.8,1.2,1.2,0.8,0.5,0.3,0.2],
    }
    conso_base = cb.get(profil_maison, cb["Standard Family (Morning and evening peaks)"])

    # ── Plug-out time options ────────────────────────────────────────────────
    # List of valid plug-out times (every hour from plug-in + 1h to plug-in + 24h)
    if part_en_journee:
        opts = [f"{(h_retour+i)%24:02d}:00" + (" D+1" if (h_retour+i)>=24 else "") for i in range(1,25)]
    else:
        opts = ["N/A"]

    # ── Reindex arrays to start from plug-in hour ────────────────────────────
    # The simulation window starts at h_retour (plug-in hour) and runs 24 slots.
    # idx_gl maps simulation slot index → real clock hour.
    idx_gl   = [(h_retour+i)%24 for i in range(24)]

    # Solar production per slot [kWh]:
    # P_pv = (G_i / 1000) × panel_area × panel_efficiency × rated_power
    # Simplified: (irr/1000) × 4.75 m² × 0.205 efficiency × kWp rated
    # NOTE: 4.75 m² and 0.205 are the EV4EU project's standard reference-module
    # constants (EV4EU methodology, ev4eu.eu) — not the physical area of the
    # user's own installation. Their product (~0.974) acts as a fixed system
    # performance ratio applied on top of the user-defined Prated [kWp].
    prod_sol = [((irr[i]/1000)*4.75*0.205*pv_rated_power) if solaire else 0.0 for i in idx_gl]

    # House consumption reindexed to simulation window [kWh per slot]
    conso_m  = [conso_base[i] for i in idx_gl]

    # ── Trip energy deduction ────────────────────────────────────────────────
    # Total energy consumed during the round trip [kWh]
    # e_trajet = distance_km × 2 × consumption_per_100km / 100
    e_trajet = (distance_km * 2 * conso_100km) / 100

    # ── GEN-I electricity tariffs (Slovenia, valid 06 February 2026, 22% VAT incl.) ─
    # Price per kWh for each clock hour [€/kWh]
    p_fixe = [0.139]*24                                                      # Fixed (ET): constant all day
    p_bi   = [0.152 if 6<=h<22 else 0.125 for h in range(24)]              # Dual-Tariff: day / night
    p_low  = [0.04258 if 9<=h<16 else 0.21948 if 18<=h<21 else 0.14384 for h in range(24)]   # Dynamic Low Season  (Mar–Oct): solar / peak / base
    p_high = [0.10968 if 9<=h<16 else 0.21948 if 18<=h<21 else 0.14384 for h in range(24)]   # Dynamic High Season (Nov–Feb): solar / peak / base
    tm     = {"Fixed (ET)":p_fixe,"Dual-Tariff (VT/MT)":p_bi,
              "Dynamic (Low Season)":p_low,"Dynamic (High Season)":p_high}
    prices = [tm[mon_tarif][i] for i in idx_gl]  # active tariff reindexed to simulation window

    # ── Connection schedule ──────────────────────────────────────────────────
    # idx_dep: index of the last slot where the EV is still connected
    # +1 offset so the plug-out slot itself counts as connected
    idx_dep   = opts.index(choix_depart) + 1 if part_en_journee else 23
    # connected[t] = 1.0 if EV is at home at slot t, 0.0 if away
    connected = [1.0 if (idx<=idx_dep if part_en_journee else True) else 0.0 for idx in range(24)]

    # ── Initial SOC values [kWh] ─────────────────────────────────────────────
    soc_init   = (soc_plug_in  / 100) * cap   # battery level when EV arrives home
    soc_target = (soc_plug_out / 100) * cap   # required battery level at departure
    soc_floor  = (soc_sec      / 100) * cap   # minimum allowed SOC (safety reserve)

    # ── Result arrays (filled slot by slot) ─────────────────────────────────
    flux, soc_ev, v2h_d = [], [], []    # grid flow [kW], SOC [%], V2H discharge [kWh]
    chg_e, sol_d, ev_fl = [], [], []    # EV charge [kWh], solar direct [kWh], connected flag
    # ── NEW: track grid draw for EV charging separately ─────────────────────
    # ce_draw_grid[t] = kWh actually drawn from the grid to charge the EV at slot t
    # This is needed for the correct savings formula (see POST-SIMULATION section).
    ce_draw_grid = []
    soc = soc_init   # current SOC [kWh], initialised at plug-in level
    td  = False       # trip deduction flag (ensure it happens only once)

    # ═════════════════════════════════════════════════════════════════════════
    # MAIN SIMULATION LOOP  —  t = 0 to 23
    # ═════════════════════════════════════════════════════════════════════════
    for idx, h in enumerate(idx_gl):
        cns = conso_m[idx]    # house consumption this slot [kWh]
        prd = prod_sol[idx]   # solar production this slot [kWh]
        ve  = bool(connected[idx])   # True if EV is plugged in
        ev_fl.append(1.0 if ve else 0.0)   # record connection status

        # ── Trip energy deduction ────────────────────────────────────────────
        # Applied at the first slot after departure (ve=False, td=False).
        # SOC drops by the energy consumed during the round trip.
        if part_en_journee and not ve and not td:
            soc = max(0, soc - e_trajet)  # SOC_new = SOC - e_trajet [kWh]
            td = True                      # flag: deduction already done

        # Reset per-slot variables
        dv = ce = tg = dp = 0.0
        cg_draw = 0.0   # kWh drawn from grid for EV charging this slot (tracked separately)
        tr = 0          # slots remaining before departure (default 0 avoids NameError when part=False)

        # ── Urgency calculation ──────────────────────────────────────────────
        # Urgency = True when there are not enough slots left to reach soc_target
        # by charging at maximum power.
        # Formula: tr ≤ ceil(need / (P_chg × η_chg))
        #   tr   = slots remaining after this slot
        #   need = energy still needed to reach target [kWh]
        #   trq  = minimum slots needed to charge that energy
        if ve:
            if part_en_journee:
                tr   = idx_dep - idx                           # slots remaining after current slot
                need = max(0, soc_target - soc)               # energy deficit [kWh]
                trq  = (need / (p_chg * ETA_CHG)) if p_chg > 0 else 0   # slots needed to charge
                import math
                urg  = (tr <= math.ceil(trq) - 1) and (need > 0.01)    # urgency flag
            else:
                urg = soc < soc_target   # if EV stays home: urgent when below target
        else:
            urg = False   # EV not connected: no charging possible

        # ── V2H SOC floor ────────────────────────────────────────────────────
        # Normally V2H is allowed down to soc_floor (safety reserve).
        # Exception: at the last slot before departure (tr ≤ 1), block V2H
        # entirely so the urgency charger can run without being counteracted.
        if ve and part_en_journee and tr <= 1:
            soc_v2h_floor = cap   # effectively blocks any V2H (avail = 0)
        else:
            soc_v2h_floor = soc_floor   # normal: discharge down to safety floor

        # ── Binary charge/discharge decision  (β ∈ {0, 1}) ──────────────────
        # β = 1 → charging mode   (no V2H this slot)
        # β = 0 → discharging / idle mode   (no charging this slot)
        # This enforces the no-simultaneous-charge-and-discharge constraint.
        if not ve:
            beta = 0   # EV absent: no action possible
        elif urg:
            beta = 1   # urgency: must charge, overrides everything
        elif prd > 0 and (prd - cns) > 0.01:
            beta = 1   # free solar surplus available: charge EV at no cost
        else:
            beta = 0   # default: V2H or idle

        # ═════════════════════════════════════════════════════════════════════
        # ENERGY FLOWS — SOLAR PRODUCTION PRESENT THIS SLOT
        # ═════════════════════════════════════════════════════════════════════
        if prd > 0:
            dp  = min(prd, cns)          # solar directly covers house [kWh] (priority 1)
            sur = max(0, prd - cns)      # solar surplus after covering house [kWh]
            bes = max(0, cns - prd)      # remaining house demand after solar [kWh]

            if ve:
                if beta == 1:
                    # ── CHARGING MODE ────────────────────────────────────────
                    if urg:
                        # Urgent: use solar surplus first, then draw from grid
                        # ce_solar = kWh stored from surplus  (surplus × η_chg, capped by capacity and charger)
                        ce_solar  = min(sur * ETA_CHG, cap - soc, p_chg * SLOT)
                        # Additional grid draw to cover remaining deficit
                        need_grid = max(0, soc_target - soc - ce_solar)
                        cg_draw   = min(need_grid / ETA_CHG, p_chg * SLOT)  # grid kWh drawn
                        ce  = ce_solar + cg_draw * ETA_CHG   # total kWh stored in battery
                    else:
                        # Not urgent: charge only from free solar surplus
                        ce_solar = min(sur * ETA_CHG, cap - soc, p_chg * SLOT)
                        ce = ce_solar
                        cg_draw = 0.0   # no grid draw when not urgent
                    soc = max(0, min(soc + ce, cap))   # update SOC [kWh], clamp to [0, cap]
                    tg  = bes + cg_draw                # net grid draw: house deficit + EV grid charge
                else:
                    # ── V2H MODE ─────────────────────────────────────────────
                    # avail = max kWh deliverable to house, respecting floor and power limit
                    avail = max(0, (soc - soc_v2h_floor) * ETA_V2H)
                    if avail > 0.01:
                        # Discharge limited by: house need, available energy, V2H power rating
                        dv_h = min(bes, avail, p_v2h * SLOT)
                        soc  = max(0, min(soc - dv_h / ETA_V2H, cap))  # SOC drops by dv_h/η_v2h
                        dv   = dv_h                        # kWh delivered to house by V2H
                        tg   = bes - dv - sur              # grid = remaining deficit − solar export
                    else:
                        tg = bes - sur   # V2H not possible: grid covers house deficit, surplus exported
            else:
                # EV absent: house gets solar, surplus exported to grid
                tg = bes - sur

        # ═════════════════════════════════════════════════════════════════════
        # ENERGY FLOWS — NO SOLAR PRODUCTION THIS SLOT (night / overcast)
        # ═════════════════════════════════════════════════════════════════════
        else:
            if ve:
                bes = cns   # full house demand must be covered by EV or grid
                if beta == 1:
                    # ── CHARGING MODE (grid only) ─────────────────────────────
                    # Charge exactly up to soc_target (just-in-time, no over-charging)
                    need_kwh  = max(0, soc_target - soc)                # energy deficit [kWh]
                    ce_stored = min(need_kwh, cap - soc, p_chg * SLOT * ETA_CHG)   # kWh stored
                    cg_draw   = ce_stored / ETA_CHG                     # kWh drawn from grid
                    ce  = ce_stored
                    soc = max(0, min(soc + ce, cap))   # update SOC
                    tg  = bes + cg_draw                # house demand + EV grid charge
                else:
                    # ── V2H MODE ─────────────────────────────────────────────
                    avail = max(0, (soc - soc_v2h_floor) * ETA_V2H)
                    if avail > 0.01:
                        dv_h = min(bes, avail, p_v2h * SLOT)
                        soc  = max(0, min(soc - dv_h / ETA_V2H, cap))
                        dv   = dv_h
                        tg   = bes - dv   # grid covers remaining house demand after V2H
                    else:
                        tg = bes   # battery at floor: grid covers all house demand
            else:
                tg = cns   # EV absent, no solar: grid covers 100% of house demand

        # ── Grid export rule ─────────────────────────────────────────────────
        # EV cannot inject energy into the grid — only PV surplus can export.
        # If tg < 0 with no solar production, it would mean EV is exporting: forbidden.
        if tg < 0 and prd == 0:
            tg = 0.0

        # ── Record this slot's results ───────────────────────────────────────
        soc_ev.append((soc/cap)*100)   # SOC as percentage [%]
        v2h_d.append(dv)               # V2H energy delivered to house [kWh]
        chg_e.append(ce)               # energy charged into battery [kWh]
        flux.append(tg)                # net grid flow (+ = import, − = export) [kWh]
        sol_d.append(dp)               # solar energy used directly by house [kWh]
        ce_draw_grid.append(cg_draw)   # kWh drawn from grid for EV charging [kWh]

    # ═════════════════════════════════════════════════════════════════════════
    # POST-SIMULATION KPI CALCULATIONS
    # ═════════════════════════════════════════════════════════════════════════

    # ── Time axis and display labels ─────────────────────────────────────────
    hl  = [f"{(h_retour+i)%24:02d}h"+(" (D+1)" if (h_retour+i)>=24 else "")+" " for i in range(24)]
    hld = hl+[hl[-1]]   # duplicated last label for step-plot rendering
    xa  = list(range(25))  # x-axis: 0 to 24 (25 points for step chart)

    # ── EV net power for chart (positive = V2H, negative = charging) ─────────
    ev_c = [v - c for v, c in zip(v2h_d, chg_e)]

    # ── Self-sufficiency rate (SSR) ──────────────────────────────────────────
    # SSR = (solar_direct + V2H_discharged) / total_house_consumption
    # Measures what fraction of house demand was covered without the grid.
    # Source: EV4EU project definition
    total_solar_direct = sum(sol_d)          # kWh from solar to house
    total_v2h          = max(0, sum(v2h_d))  # kWh from battery to house
    total_house        = sum(conso_m)         # total house demand [kWh]
    # Grid share used for house only (excludes EV charging from grid)
    grid_for_house = sum([max(0, c - ps - v) for c, ps, v in zip(conso_m, prod_sol, v2h_d)])

    # ── SSR without V2H (solar only, Scenario D baseline) ────────────────────
    # If V2H were disabled, the EV would only charge — solar_direct stays identical,
    # but no V2H discharge occurs. SSR_no_v2h = solar_direct / total_house.
    ssr_no_v2h = (total_solar_direct / total_house) if total_house > 0 else 0.0

    # ── Daily electricity cost WITH V2H ──────────────────────────────────────
    # cr = Σ max(0, flux[t]) × price[t]   — total grid import cost (house + EV charging)
    cr   = sum([max(0,n)*p for n,p in zip(flux,prices)])
    # Feed-in revenue: energy exported × feed-in tariff
    exkw = sum([abs(n) for n in flux if n < 0])   # total exported kWh
    fir  = exkw * feed_in_tariff                   # feed-in revenue [€]
    cr   = max(0, cr - fir)                        # net daily cost [€]

    # ── Daily electricity cost WITHOUT V2H (reference baseline) ─────────────
    # cne = cost if the EV did not exist: only solar + grid covers the house
    # cne = Σ max(0, conso[t] - prod_sol[t]) × price[t]
    cne  = sum([max(0,c-ps)*p for c,ps,p in zip(conso_m,prod_sol,prices)])

    # ── Daily savings — CORRECTED FORMULA ────────────────────────────────────
    # ISSUE with (cne - cr): cr includes EV grid charging cost which cne does not,
    # so savings appear negative whenever the EV charges from the grid at night.
    #
    # CORRECT approach — measure the VALUE of V2H independently:
    #   value_v2h  = electricity bill avoided thanks to V2H discharge
    #              = Σ v2h_d[t] × price[t]   (kWh V2H supplied × tariff at that hour)
    #   cost_grid_charge = extra grid cost to recharge the EV
    #              = Σ ce_draw_grid[t] × price[t]
    #   savings = value_v2h - cost_grid_charge
    #
    # This correctly isolates the net financial benefit of the V2H function,
    # independent of how much the EV costs to charge.
    value_v2h       = sum([v * p for v, p in zip(v2h_d, prices)])
    cost_grid_charge = sum([cg * p for cg, p in zip(ce_draw_grid, prices)])
    sav = value_v2h - cost_grid_charge

    tv2h = total_v2h   # total V2H energy discharged today [kWh]

    # ── Return all computed data to the dashboard ─────────────────────────────
    return dict(
        prod_sol=prod_sol, conso_m=conso_m, flux=flux, soc_ev=soc_ev,
        v2h_d=v2h_d, chg_e=chg_e, sol_d=sol_d, ev_fl=ev_fl, ev_c=ev_c,
        opts=opts, idx_gl=idx_gl,
        hl=hl, hld=hld, xa=xa,
        psd=prod_sol+[prod_sol[-1]], cmd=conso_m+[conso_m[-1]],
        evd=ev_c+[ev_c[-1]], grd=flux+[flux[-1]], socd=soc_ev+[soc_ev[-1]],
        p_fixe=p_fixe, p_bi=p_bi, p_low=p_low, p_high=p_high, prices=prices,
        cr=cr, cne=cne, sav=sav, tv2h=tv2h, e_trajet=e_trajet,
        fir=fir, exkw=exkw,
        total_solar_direct=total_solar_direct,
        total_v2h=total_v2h,
        total_house=total_house,
        grid_for_house=grid_for_house,
        ssr_no_v2h=ssr_no_v2h,
        value_v2h=value_v2h,
        cost_grid_charge=cost_grid_charge,
    )



# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — USER INPUTS  (Streamlit Sidebar)
# ═══════════════════════════════════════════════════════════════════════════════
# All parameters are collected here via interactive widgets.
# Any change triggers a full recompute of the simulation (cache invalidated).
# ───────────────────────────────────────────────────────────────────────────────

# Label → internal key mappings for display-friendly sidebar labels
pm = {"Standard Family":"Standard Family (Morning and evening peaks)",
      "Remote Worker":"Remote Worker (Continuous consumption)",
      "Thrifty":"Thrifty (Low baseline)"}
tm = {"Fixed (ET)":"Fixed (ET)","Dual-Tariff":"Dual-Tariff (VT/MT)",
      "Dynamic (Low)":"Dynamic (Low Season)","Dynamic (High)":"Dynamic (High Season)"}

st.sidebar.markdown("<div style='font-size:12px;font-weight:700;color:#1BB87F;text-transform:uppercase;letter-spacing:0.03em;margin:8px 0 4px 0;'>1 — Home Profile</div>", unsafe_allow_html=True)
profil_maison = pm[st.sidebar.selectbox("P", list(pm.keys()), label_visibility="collapsed")]

st.sidebar.markdown("<div style='font-size:12px;font-weight:700;color:#1BB87F;text-transform:uppercase;letter-spacing:0.03em;margin:8px 0 4px 0;'>2 — Solar · Ljubljana</div>", unsafe_allow_html=True)
mois = st.sidebar.select_slider("Month", options=["December", "March", "June"], value="June")
sc1, sc2 = st.sidebar.columns([0.3, 0.7])
with sc1: solaire = st.toggle("☀️", value=True, label_visibility="collapsed")
with sc2: pv = st.number_input("kWp", min_value=0.0, value=6.0, step=0.5, label_visibility="collapsed")
st.sidebar.caption(f"{'Solar ON' if solaire else 'Solar OFF'} · {pv} kWp · {mois}")

st.sidebar.markdown("<div style='font-size:12px;font-weight:700;color:#1BB87F;text-transform:uppercase;letter-spacing:0.03em;margin:8px 0 4px 0;'>3 — Electric Vehicle</div>", unsafe_allow_html=True)
modele = st.sidebar.selectbox("V", list(db_voitures.keys()), label_visibility="collapsed")
if modele == "Custom":
    cc1,cc2 = st.sidebar.columns(2)
    with cc1:
        cust_cap = st.number_input("Bat. kWh",5.0,200.0,60.0,1.0)
        cust_v2h = st.number_input("V2H kW",1.0,50.0,7.4,0.1)
    with cc2:
        cust_chg = st.number_input("Chg kW",1.0,50.0,7.4,0.1)
        cust_cns = st.number_input("kWh/100km",5.0,50.0,16.0,0.5)
    db_voitures["Custom"] = {"capacite_utile":cust_cap,"puissance_charge_max":cust_chg,
                              "puissance_v2h_max":cust_v2h,"conso_100km":cust_cns}
borne = st.sidebar.select_slider("Home charger (kW)", options=[2.3,3.7,7.4,11.0,22.0], value=7.4)

st.sidebar.markdown("<div style='font-size:12px;font-weight:700;color:#1BB87F;text-transform:uppercase;letter-spacing:0.03em;margin:8px 0 4px 0;'>4 — Mobility & SOC</div>", unsafe_allow_html=True)
part = st.sidebar.toggle("EV leaves during day", value=True)
if part:
    h_ret = st.sidebar.slider("Plug-in hour", 0, 23, 18)
    opts_s = [f"{(h_ret+i)%24:02d}:00"+(" D+1" if (h_ret+i)>=24 else "") for i in range(1,25)]
    ch_dep = st.sidebar.selectbox("Plug-out time", opts_s, index=13)
    st.sidebar.caption(f"Connected {h_ret:02d}h → {ch_dep}")
    soc_in  = st.sidebar.slider("SOC at plug-in (%)", 0, 100, 50)
    soc_out = st.sidebar.slider("Target SOC at departure (%)", 10, 100, 80)
    dist    = st.sidebar.slider("One-way distance (km)", 0, 150, 30, step=5)
    st.sidebar.caption(f"Round trip {dist*2} km — ~{dist*2*db_voitures[modele]['conso_100km']/100:.1f} kWh")
else:
    h_ret=0; ch_dep="N/A"; dist=0
    soc_in  = st.sidebar.slider("SOC start (%)", 0, 100, 70)
    soc_out = st.sidebar.slider("Target SOC (%)", 10, 100, 80)
soc_sec = st.sidebar.slider("Safety SOC (%)", 10, 50, 20)

st.sidebar.markdown("<div style='font-size:12px;font-weight:700;color:#1BB87F;text-transform:uppercase;letter-spacing:0.03em;margin:8px 0 4px 0;'>5 — Tariff · GEN-I</div>", unsafe_allow_html=True)
mon_tarif = tm[st.sidebar.selectbox("T", list(tm.keys()), label_visibility="collapsed")]
feed_in   = st.sidebar.slider("Feed-in tariff (€/kWh)", 0.0, 0.15, 0.0, 0.01)
if feed_in > 0: st.sidebar.caption(f"Export @ {feed_in:.2f} €/kWh")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — OUTPUT  (Dashboard)
# ═══════════════════════════════════════════════════════════════════════════════
# Unpack simulation results and compute derived display metrics.
# ───────────────────────────────────────────────────────────────────────────────

# ── Run simulation with current sidebar parameters ───────────────────────────
ci  = db_voitures[modele].copy()   # vehicle specs for the selected model
sim = calculer_simulation(
    profil_maison, solaire, pv, modele, borne, part, h_ret, ch_dep,
    soc_in, soc_out, soc_sec, mon_tarif, dist, feed_in,
    ci["capacite_utile"], ci["puissance_charge_max"],
    ci["puissance_v2h_max"], ci["conso_100km"], mois)

ps=sim["prod_sol"]; cm=sim["conso_m"]; fl=sim["flux"]
sv=sim["soc_ev"];   vd=sim["v2h_d"];   ce=sim["chg_e"]
sd=sim["sol_d"];    ef=sim["ev_fl"];    ec=sim["ev_c"]
og=sim["idx_gl"];   op=sim["opts"]
hl=sim["hl"];       hd=sim["hld"];      xa=sim["xa"]
psd=sim["psd"];     cmd=sim["cmd"];     evd=sim["evd"]
grd=sim["grd"];     socd=sim["socd"]
pf=sim["p_fixe"];   pb=sim["p_bi"];     pl=sim["p_low"]; ph2=sim["p_high"]
prices=sim["prices"]
cr=sim["cr"];       cne=sim["cne"];     sav=sim["sav"]
tv2h=sim["tv2h"];   etr=sim["e_trajet"]
fir=sim["fir"];     exkw=sim["exkw"]

# ef_display: connection flag shifted 1 slot earlier for graph label alignment
# (shows "Away" one hour before actual departure for visual clarity)
ef_display = ef[1:] + [ef[-1]] if part else ef

ts=sim["total_solar_direct"]; tv=sim["total_v2h"]
tg_house=sim["grid_for_house"]; total_house=sim["total_house"]
ssr_no_v2h=sim["ssr_no_v2h"]
tg=sum([max(0,x) for x in fl])   # total grid draw including EV charging [kWh]

# ── Self-sufficiency rate ────────────────────────────────────────────────────
# SSR = (solar_direct + V2H) / total_house_demand
# Fraction of house energy covered without the grid, capped at 100%
ss = min((ts + tv) / total_house, 1.0) if total_house > 0 else 0

# ── Environmental impact ─────────────────────────────────────────────────────
# ea: total clean energy used by house (solar + V2H) [kWh]
# co2: CO₂ avoided vs pure grid supply [kg]   K_res = 1.043 kg/kWh (EV4EU)
# coal: hard coal equivalent avoided [kg tce]   factor = 0.1229 kg tce/kWh
#       Source: IEA (2023) "Glossary of Energy Units" — 1 tce = 29.3 GJ
ea=ts+tv; co2=ea*1.043; coal=ea*0.1229

# ─────────────────────────────────────────────────────────────────
# 5.1 — PAGE HEADER
# ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style='display:flex;align-items:center;justify-content:space-between;
     padding:12px 0 14px;border-bottom:1.5px solid #E5E7EB;margin-bottom:14px;'>
  <div>
    <div style='font-family:Outfit,sans-serif;font-size:22px;font-weight:700;
         color:#111827;letter-spacing:-0.02em;'>V2H Energy Simulator</div>
    <div style='font-family:IBM Plex Mono,monospace;font-size:10px;color:#9CA3AF;
         letter-spacing:0.1em;margin-top:3px;text-transform:uppercase;'>
      Vehicle-to-Home &nbsp;·&nbsp; Ljubljana {mois} &nbsp;·&nbsp; EV4EU Project
    </div>
  </div>
  <div style='text-align:right;font-family:IBM Plex Mono,monospace;font-size:11px;color:#6B7280;'>
    <div style='color:#1BB87F;font-weight:500;margin-bottom:2px;'>Live Simulation</div>
    <div>{modele.split("(")[0].strip()}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# 5.2 — PLOTLY THEME & SESSION STATE
# Shared chart styling applied to all Plotly figures.
# ─────────────────────────────────────────────────────────────────
PB = dict(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(248,249,251,0.8)',
          font=dict(family='IBM Plex Mono,monospace',size=10,color='#9CA3AF'))

if "current_hour_idx" not in st.session_state:
    st.session_state.current_hour_idx = 0

# ─────────────────────────────────────────────────────────────────
# 5.3 — MAIN LAYOUT  (Left 68% | Right 32%)
# Left  : Energy flow graph + Tariff chart
# Right : Energy mix pie + KPIs + Battery degradation
# ─────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([0.68, 0.32])

with col_left:
    with st.container(border=True):
        st.markdown(f"<div class='sec-title'>Energy Flow (kW) + Battery SOC &nbsp;<span style='color:#9CA3AF;font-weight:400;font-size:10px;'>plug-in {h_ret:02d}h · {mois} · Ljubljana</span></div>", unsafe_allow_html=True)
        fig = go.Figure()
        segs=[]; sv2,ss2=ef_display[0],0
        for i in range(1,24):
            if ef_display[i]!=sv2: segs.append((ss2,i,sv2)); ss2,sv2=i,ef_display[i]
        segs.append((ss2,24,sv2))
        for s,e,conn in segs:
            fc="rgba(27,184,127,0.08)" if conn else "rgba(239,68,68,0.07)"
            bc="rgba(27,184,127,0.4)"  if conn else "rgba(239,68,68,0.5)"
            fig.add_vrect(x0=s,x1=e,fillcolor=fc,layer="below",line_width=1,line_color=bc,
                annotation_text="Connected" if conn else "Away",annotation_position="top left",
                annotation=dict(font_size=9,font_color=bc))
        for y,fc,lc,nm in [
            (psd,'rgba(249,115,22,0.38)','#F97316','Solar'),
            (cmd,'rgba(148,163,184,0.38)','#94A3B8','House Load'),
            (evd,'rgba(20,184,166,0.42)','#14B8A6','EV (V2H / Charge)'),
            (grd,'rgba(139,92,246,0.38)','#8B5CF6','Grid (Import / Export)'),
        ]:
            fig.add_trace(go.Scatter(x=xa,y=y,fill='tozeroy',mode='lines',name=nm,
                fillcolor=fc,line=dict(color=lc,width=1.8),yaxis='y',
                hovertemplate=f'%{{text}}<br>{nm}: %{{y:.2f}} kW<extra></extra>',text=hd))
        fig.add_trace(go.Scatter(x=xa,y=socd,mode='lines+markers',name='Battery SOC',
            line=dict(color='#3B82F6',width=1.8,dash='dot'),
            marker=dict(size=4,color='#3B82F6'),yaxis='y2',
            hovertemplate='%{text}<br>SOC: %{y:.1f}%<extra></extra>',text=hd))
        fig.add_hline(y=soc_sec,line_dash="dot",line_color="#EF4444",line_width=1,yref='y2',
            annotation_text=f"Safety {soc_sec}%",annotation_font_size=9,
            annotation_font_color="#EF4444",annotation_position="top right")
        fig.update_layout(height=300,margin=dict(l=8,r=56,t=8,b=32),
            legend=dict(orientation='h',yanchor='bottom',y=1.02,font=dict(size=10),bgcolor='rgba(0,0,0,0)'),
            xaxis=dict(tickmode='array',tickvals=xa,ticktext=hd,tickangle=-45,tickfont=dict(size=8),
                       showline=True,linewidth=1.5,linecolor='#D1D5DB',mirror=False,
                       zeroline=True,zerolinecolor='#E5E7EB',zerolinewidth=1,
                       gridcolor='#F0F1F3',tickcolor='#D1D5DB'),
            yaxis=dict(title=dict(text='kW',font=dict(size=10)),tickfont=dict(size=8),
                       showline=True,linewidth=1.5,linecolor='#D1D5DB',mirror=False,
                       zeroline=True,zerolinecolor='#CBD5E1',zerolinewidth=1.5,
                       gridcolor='#F0F1F3',tickcolor='#D1D5DB'),
            yaxis2=dict(title=dict(text='SOC %',font=dict(size=10)),tickfont=dict(size=8),
                        overlaying='y',side='right',range=[0,105],ticksuffix='%',showgrid=False,
                        showline=True,linewidth=1.5,linecolor='#D1D5DB'),**PB)
        st.plotly_chart(fig,use_container_width=True)

    with st.container(border=True):
        st.markdown("<div class='sec-title'>GEN-I Tariff Overview (€/kWh)</div>", unsafe_allow_html=True)
        ft=go.Figure()
        for y,c,n in [
            ([pf[i] for i in og]+[pf[og[-1]]],'#10B981','Fixed (ET)'),
            ([pb[i] for i in og]+[pb[og[-1]]],'#6366F1','Dual-Tariff'),
            ([pl[i] for i in og]+[pl[og[-1]]],'#F59E0B','Dynamic Low'),
            ([ph2[i] for i in og]+[ph2[og[-1]]],'#EF4444','Dynamic High'),
        ]:
            ft.add_trace(go.Scatter(x=xa,y=y,mode='lines',name=n,line=dict(color=c,width=1.8)))
        ft.update_layout(height=200,margin=dict(l=8,r=8,t=4,b=32),
            legend=dict(orientation='h',yanchor='bottom',y=1.02,font=dict(size=10),bgcolor='rgba(0,0,0,0)'),
            xaxis=dict(tickmode='array',tickvals=xa,ticktext=hd,tickangle=-45,tickfont=dict(size=8),
                       showline=True,linewidth=1.5,linecolor='#D1D5DB',
                       zeroline=False,gridcolor='#F0F1F3',tickcolor='#D1D5DB'),
            yaxis=dict(ticksuffix=' €',tickfont=dict(size=8),
                       showline=True,linewidth=1.5,linecolor='#D1D5DB',
                       gridcolor='#F0F1F3',tickcolor='#D1D5DB'),**PB)
        st.plotly_chart(ft,use_container_width=True)

with col_right:
    with st.container(border=True):
        st.markdown("<div class='sec-title'>Energy Mix</div>", unsafe_allow_html=True)
        fp=go.Figure(data=[go.Pie(
            values=[ts, tv, tg_house],hole=0.54,
            marker=dict(colors=['#F97316','#14B8A6','#8B5CF6'],line=dict(color='#fff',width=2)),
            textinfo='percent',textfont=dict(size=11,family='IBM Plex Mono'),showlegend=False)])
        fp.update_layout(height=170,margin=dict(l=0,r=0,t=4,b=4),paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fp,use_container_width=True)
        st.markdown(f"""
        <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;'>
          <div style='text-align:center;background:#FFF7ED;border-radius:7px;padding:5px 3px;'>
            <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#C2410C;font-weight:600;'>SOLAR</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:12px;font-weight:500;color:#111827;'>{ts:.1f}</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#9CA3AF;'>kWh</div>
          </div>
          <div style='text-align:center;background:#F0FDFA;border-radius:7px;padding:5px 3px;'>
            <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#0F766E;font-weight:600;'>V2H</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:12px;font-weight:500;color:#111827;'>{tv:.1f}</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#9CA3AF;'>kWh</div>
          </div>
          <div style='text-align:center;background:#F5F3FF;border-radius:7px;padding:5px 3px;'>
            <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#6D28D9;font-weight:600;'>GRID</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:12px;font-weight:500;color:#111827;'>{tg_house:.1f}</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#9CA3AF;'>kWh</div>
          </div>
        </div>
        <div style='margin-top:6px;padding:6px 10px;background:#F0FDF4;border-radius:8px;border:1px solid #BBF7D0;text-align:center;'>
          <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#6B7280;text-transform:uppercase;letter-spacing:0.06em;'>Self-sufficiency</div>
          <div style='font-family:IBM Plex Mono,monospace;font-size:22px;font-weight:600;color:#1BB87F;line-height:1.1;'>{ss:.1%}</div>
          <div style='background:#D1FAE5;border-radius:99px;height:3px;margin-top:4px;'>
            <div style='background:#1BB87F;border-radius:99px;height:3px;width:{ss*100:.1f}%;'></div>
          </div>
        </div>
        <div style='margin-top:5px;padding:5px 10px;background:#EFF6FF;border-radius:8px;border:1px solid #BFDBFE;display:flex;justify-content:space-between;align-items:center;'>
          <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#6B7280;text-transform:uppercase;'>SSR without V2H</div>
          <div style='font-family:IBM Plex Mono,monospace;font-size:13px;font-weight:600;color:#1D4ED8;'>{ssr_no_v2h:.1%}</div>
        </div>
        <div style='margin-top:3px;padding:3px 10px;background:#F0FDF4;border-radius:8px;border:1px solid #BBF7D0;display:flex;justify-content:space-between;align-items:center;'>
          <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#6B7280;text-transform:uppercase;'>V2H contribution</div>
          <div style='font-family:IBM Plex Mono,monospace;font-size:13px;font-weight:600;color:#1BB87F;'>+{(ss-ssr_no_v2h):.1%}</div>
        </div>
        """, unsafe_allow_html=True)

    with st.container(border=True):
        sav_positive = sav >= 0
        sav_color  = "#1BB87F" if sav_positive else "#EF4444"
        sav_bg     = "linear-gradient(135deg,#F0FDF4,#DCFCE7)" if sav_positive else "linear-gradient(135deg,#FEF2F2,#FEE2E2)"
        sav_border = "#86EFAC" if sav_positive else "#FCA5A5"
        sav_arrow  = "↓" if sav_positive else "▲"
        pills = "<div style='display:flex;gap:4px;flex-wrap:wrap;margin-bottom:6px;'>"
        pills += f"<span class='kpi-pill pill-green' style='font-size:10px;padding:3px 7px;'>V2H {tv2h:.2f} kWh</span>"
        if part and dist>0:
            pills += f"<span class='kpi-pill pill-red' style='font-size:10px;padding:3px 7px;'>Trip {etr:.2f} kWh</span>"
        if fir>0:
            pills += f"<span class='kpi-pill pill-amber' style='font-size:10px;padding:3px 7px;'>Export {fir:.2f}€</span>"
        pills += "</div>"
        st.markdown(pills, unsafe_allow_html=True)
        st.markdown(f"""
        <div style='display:grid;grid-template-columns:1fr 1fr 1fr;gap:5px;margin-bottom:6px;'>
          <div style='background:#F9FAFB;border:1px solid #E5E7EB;border-top:3px solid #6B7280;border-radius:8px;padding:8px 10px;'>
            <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#9CA3AF;text-transform:uppercase;letter-spacing:0.05em;'>Without EV</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:17px;font-weight:600;color:#374151;margin-top:2px;'>{cne:.2f}<span style='font-size:10px;color:#9CA3AF;'> €</span></div>
          </div>
          <div style='background:#EFF6FF;border:1px solid #BFDBFE;border-top:3px solid #3B82F6;border-radius:8px;padding:8px 10px;'>
            <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#9CA3AF;text-transform:uppercase;letter-spacing:0.05em;'>With V2H</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:17px;font-weight:600;color:#1D4ED8;margin-top:2px;'>{cr:.2f}<span style='font-size:10px;color:#9CA3AF;'> €</span></div>
          </div>
          <div style='background:{sav_bg};border:1px solid {sav_border};border-top:3px solid {sav_color};border-radius:8px;padding:8px 10px;'>
            <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#9CA3AF;text-transform:uppercase;letter-spacing:0.05em;'>V2H Savings</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:17px;font-weight:700;color:{sav_color};margin-top:2px;'>{sav_arrow} {abs(sav):.2f}<span style='font-size:10px;'> €</span></div>
          </div>
        </div>
        <div style='display:grid;grid-template-columns:1fr 1fr;gap:5px;'>
          <div style='background:linear-gradient(135deg,#ECFDF5,#D1FAE5);border:1px solid #6EE7B7;border-radius:8px;padding:7px 4px;text-align:center;'>
            <div style='font-size:15px;'>🌿</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:13px;font-weight:700;color:#065F46;'>{co2:.1f}</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:7px;color:#059669;text-transform:uppercase;'>kg CO₂ avoided</div>
          </div>
          <div style='background:linear-gradient(135deg,#FFFBEB,#FEF3C7);border:1px solid #FCD34D;border-radius:8px;padding:7px 4px;text-align:center;'>
            <div style='font-size:15px;'>⛏️</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:13px;font-weight:700;color:#78350F;'>{coal:.2f}</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:7px;color:#92400E;text-transform:uppercase;'>kg coal eq. (tce)</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # Battery degradation
    degradation_db = {
        "Nissan Leaf (40 kWh)":      {"prix_batterie": 8500,  "cycles_vie": 1500},
        "Renault 5 E-Tech (52 kWh)": {"prix_batterie": 9000,  "cycles_vie": 1500},
        "Tesla Model 3 (57.5 kWh)":  {"prix_batterie": 13000, "cycles_vie": 1500},
        "Custom":                     {"prix_batterie": 10000, "cycles_vie": 1500},
    }
    # ── Battery degradation cost ─────────────────────────────────────────────
    # Linear cost-per-cycle model: Source: Xu et al. (2018), Energy & Environ. Sci.
    # cost_per_kWh = replacement_price / (lifetime_cycles × usable_capacity)
    # daily_cost   = cost_per_kWh × kWh_discharged_via_V2H_today
    deg          = degradation_db.get(modele, degradation_db["Custom"])
    cout_par_kwh = deg["prix_batterie"] / (deg["cycles_vie"] * ci["capacite_utile"])  # €/kWh cycled
    cout_deg     = max(0, cout_par_kwh * tv2h)   # daily degradation cost [€]
    # Net savings = V2H savings − battery wear cost
    net_sav      = sav - cout_deg
    net_col      = "#1BB87F" if net_sav >= 0 else "#EF4444"
    net_arr      = "▼" if net_sav >= 0 else "▲"

    st.markdown(f"""
    <div style='background:#FAFAFA;border:1px solid #E5E7EB;border-left:4px solid #F59E0B;
         border-radius:10px;padding:10px 14px;margin-top:0px;'>
      <div style='display:flex;justify-content:space-between;align-items:flex-start;'>
        <div>
          <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#9CA3AF;
               text-transform:uppercase;letter-spacing:0.06em;margin-bottom:2px;'>⚡ Battery Degradation</div>
          <div style='font-family:IBM Plex Mono,monospace;font-size:16px;font-weight:600;color:#B45309;'>
            +{cout_deg:.3f} <span style='font-size:10px;font-weight:400;color:#9CA3AF;'>€/day</span>
          </div>
          <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#9CA3AF;margin-top:2px;'>
            {tv2h:.2f} kWh × {cout_par_kwh:.4f} €/kWh
          </div>
        </div>
        <div style='text-align:right;'>
          <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#9CA3AF;margin-bottom:2px;'>Net savings</div>
          <div style='font-family:IBM Plex Mono,monospace;font-size:14px;font-weight:700;color:{net_col};'>
            {net_arr} {abs(net_sav):.3f} €
          </div>
          <div style='font-family:IBM Plex Mono,monospace;font-size:7px;color:#9CA3AF;'>V2H savings − degradation</div>
        </div>
      </div>
      <div style='font-family:IBM Plex Mono,monospace;font-size:7px;color:#B8B8B8;margin-top:6px;
           border-top:1px solid #F0F0F0;padding-top:4px;'>
        Xu et al. (2018) Energy &amp; Environ. Sci. · {modele.split("(")[0].strip()}: {deg["prix_batterie"]:,}€ / {deg["cycles_vie"]} cycles
        · η_chg={int(ETA_CHG*100)}% · η_v2h={int(ETA_V2H*100)}%
      </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# 5.4 — SCENARIO COMPARISON
# Automatically reruns the simulation for Dec/Mar/Jun with the same
# sidebar parameters, then displays the 3 results side by side.
# ─────────────────────────────────────────────────────────────────
st.markdown("""
  <div style='font-family:IBM Plex Mono,monospace;font-size:9px;color:#9CA3AF;text-transform:uppercase;letter-spacing:0.06em;'>Same parameters · 3 solar seasons · Ljubljana</div>
</div>
""", unsafe_allow_html=True)

scenarios = [
    ("December", "Worst Case",   "#EF4444", "#FEF2F2", "#FECACA"),
    ("March",    "Average Case", "#F59E0B", "#FFFBEB", "#FDE68A"),
    ("June",     "Best Case",    "#1BB87F", "#F0FDF4", "#BBF7D0"),
]
sc_cols = st.columns(3)
for col, (sc_mois, sc_label, sc_color, sc_bg, sc_border) in zip(sc_cols, scenarios):
    sc_sim = calculer_simulation(
        profil_maison, solaire, pv, modele, borne, part, h_ret, ch_dep,
        soc_in, soc_out, soc_sec, mon_tarif, dist, feed_in,
        ci["capacite_utile"], ci["puissance_charge_max"],
        ci["puissance_v2h_max"], ci["conso_100km"], sc_mois)
    sc_ts  = sum(sc_sim["sol_d"]); sc_tv = sum(sc_sim["v2h_d"])
    sc_tg  = sum([max(0,x) for x in sc_sim["flux"]])
    sc_total_conso = sum(sc_sim["conso_m"])
    sc_ss  = min((sc_ts + sc_tv) / sc_total_conso, 1.0) if sc_total_conso > 0 else 0
    sc_sav = sc_sim["sav"]; sc_cr = sc_sim["cr"]; sc_cne = sc_sim["cne"]
    sc_tv2h= sc_sim["tv2h"]; sc_co2 = (sc_ts + sc_tv) * 1.043
    sc_arr = "▼" if sc_sav >= 0 else "▲"
    sc_col2= "#1BB87F" if sc_sav >= 0 else "#EF4444"
    with col:
        st.markdown(f"""
        <div style='background:{sc_bg};border:1.5px solid {sc_border};border-top:4px solid {sc_color};border-radius:12px;padding:14px;'>
          <div style='display:flex;align-items:center;gap:6px;margin-bottom:10px;'>
            <div style='width:8px;height:8px;border-radius:50%;background:{sc_color};flex-shrink:0;'></div>
            <div>
              <div style='font-family:Outfit,sans-serif;font-size:13px;font-weight:700;color:#111827;'>{sc_label}</div>
              <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#9CA3AF;text-transform:uppercase;'>{sc_mois} · Ljubljana</div>
            </div>
          </div>
          <div style='display:flex;justify-content:space-between;margin-bottom:3px;'>
            <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#6B7280;text-transform:uppercase;'>Self-sufficiency</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:13px;font-weight:700;color:{sc_color};'>{sc_ss:.1%}</div>
          </div>
          <div style='background:#E5E7EB;border-radius:99px;height:4px;margin-bottom:10px;'>
            <div style='background:{sc_color};border-radius:99px;height:4px;width:{sc_ss*100:.1f}%;'></div>
          </div>
          <div style='border-top:1px solid {sc_border};margin:8px 0;'></div>
          <div style='display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-bottom:8px;font-family:IBM Plex Mono,monospace;'>
            <div><div style='font-size:8px;color:#9CA3AF;text-transform:uppercase;'>Solar</div><div style='font-size:12px;font-weight:600;color:#111827;'>{sc_ts:.1f} kWh</div></div>
            <div><div style='font-size:8px;color:#9CA3AF;text-transform:uppercase;'>V2H</div><div style='font-size:12px;font-weight:600;color:#111827;'>{sc_tv2h:.1f} kWh</div></div>
            <div><div style='font-size:8px;color:#9CA3AF;text-transform:uppercase;'>Without EV</div><div style='font-size:12px;font-weight:600;color:#111827;'>{sc_cne:.2f}€</div></div>
            <div><div style='font-size:8px;color:#9CA3AF;text-transform:uppercase;'>With V2H</div><div style='font-size:12px;font-weight:600;color:#111827;'>{sc_cr:.2f}€</div></div>
          </div>
          <div style='background:white;border-radius:8px;padding:7px 10px;border:1px solid {sc_border};display:flex;justify-content:space-between;align-items:center;'>
            <div style='font-family:IBM Plex Mono,monospace;font-size:8px;color:#9CA3AF;text-transform:uppercase;'>V2H Savings</div>
            <div style='font-family:IBM Plex Mono,monospace;font-size:16px;font-weight:700;color:{sc_col2};'>{sc_arr} {abs(sc_sav):.2f}€</div>
          </div>
          <div style='margin-top:6px;font-family:IBM Plex Mono,monospace;font-size:10px;color:#6B7280;'>
            🌿 <b style='color:{sc_color};'>{sc_co2:.1f} kg</b> CO₂ avoided &nbsp;·&nbsp; {sc_co2*0.1229:.2f} kg tce
          </div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# 5.5 — EXPANDERS  (collapsible info panels)
# ─────────────────────────────────────────────────────────────────
st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)

with st.expander("📖  How to use this simulator"):
    st.markdown("""
    <div style='font-family:IBM Plex Mono,monospace;font-size:11px;color:#374151;line-height:2.0;'>
    <b style='font-size:12px;color:#111827;'>Step 1 — Configure your home</b><br>
    Select your household consumption profile: <b>Standard Family</b>, <b>Remote Worker</b>, or <b>Thrifty</b>.<br><br>
    <b style='font-size:12px;color:#111827;'>Step 2 — Set up solar panels</b><br>
    Choose the simulation month and set your installed PV power in kWp. Toggle panels ON/OFF to compare.<br><br>
    <b style='font-size:12px;color:#111827;'>Step 3 — Choose your EV</b><br>
    Select your vehicle model or use <b>Custom</b> to enter your own battery specs. Set the home charger power.<br><br>
    <b style='font-size:12px;color:#111827;'>Step 4 — Set mobility parameters</b><br>
    If your EV leaves during the day: set plug-in hour, plug-out time, SOC targets, and one-way distance.<br><br>
    <b style='font-size:12px;color:#111827;'>Step 5 — Choose your electricity tariff</b><br>
    Select your GEN-I contract type. Dynamic tariffs show larger V2H savings due to price differences.<br><br>
    <b style='font-size:12px;color:#111827;'>Step 6 — Read the results</b><br>
    · <b>Energy Flow graph</b> — solar, house load, EV charge/V2H, and grid over 24h.<br>
    · <b>Energy Mix pie</b> — proportion from each source.<br>
    · <b>V2H Savings</b> — value of electricity supplied by V2H minus cost of grid recharging.<br>
    · <b>Scenario Comparison</b> — automatically runs all 3 seasons with your parameters.
    </div>
    """, unsafe_allow_html=True)

with st.expander("ℹ️  About this simulation & References"):
    st.markdown(f"""
    <div style='font-family:IBM Plex Mono,monospace;font-size:11px;color:#374151;line-height:2.0;'>
    <b style='font-size:12px;color:#111827;'>Model constraints</b><br>
    · No simultaneous charge and discharge (enforced per slot).<br>
    · EV cannot export to grid — only PV surplus can be exported (grid export rule).<br>
    · SOC bounded between safety floor and maximum capacity at every slot.<br>
    · SOC target must be reached before departure time.<br>
    · Charging efficiency η={int(ETA_CHG*100)}% · V2H discharge efficiency η={int(ETA_V2H*100)}%.<br><br>
    <b style='font-size:12px;color:#111827;'>Savings formula</b><br>
    · V2H savings = Σ V2H_discharged[t] × price[t] − Σ grid_charge_draw[t] × price[t]<br>
    · Measures the net financial benefit of V2H independently of total EV charging cost.<br><br>
    <b style='font-size:12px;color:#111827;'>Data sources</b><br>
    · Solar irradiance — PVGIS SARAH3, Ljubljana (46.056°N, 14.506°E), slope 35°, azimuth 0°.<br>
    · Electricity tariffs — GEN-I Slovenia official rates (valid 06 Feb. 2026).<br>
    · CO₂ factor — K_res = 1043 g/kWh (EV4EU project).<br>
    · Coal equivalent — 0.1229 kg tce/kWh (IEA, 2023 — Glossary of Energy Units; 1 tce = 29.3 GJ).<br>
    · Battery degradation — Xu et al. (2018), Energy &amp; Environ. Sci.<br>
    · Consumption profiles — Fraunhofer ISE (2023); Eurostat (2022).<br><br>
    <b style='font-size:12px;color:#111827;'>References</b><br>
    · Kempton &amp; Tomić (2005) — J. Power Sources, 144(1), 268–279.<br>
    · EV4EU Project (2022–2025) — <a href='https://ev4eu.eu' style='color:#1BB87F;'>ev4eu.eu</a><br>
    · Xu, B. et al. (2018) — Energy &amp; Environ. Sci., 11, 3585–3600.<br>
    · PVGIS — <a href='https://re.jrc.ec.europa.eu/pvgis/' style='color:#1BB87F;'>re.jrc.ec.europa.eu</a><br>
    · Yilmaz &amp; Krein (2013) — IEEE Trans. Power Electron.<br><br>
    <b style='font-size:12px;color:#111827;'>Limitations</b><br>
    · Solar data = monthly averages (real production varies day-to-day).<br>
    · Consumption profiles are archetypes, not measured data.<br>
    · 24h simulation only — no multi-day battery state carryover.<br>
    · Linear degradation model (actual aging is non-linear).
    </div>
    """, unsafe_allow_html=True)