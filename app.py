import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def degradation_profile(year):
    health = [
        97.4,
        93.49,
        90.75,
        88.11,
        85.95,
        83.7,
        81.81,
        80.01,
        78.05,
        76.39,
        74.78,
        73,
        71.48,
        70,
        68.34,
        66.93
    ]
    return health[year]


def batt_size(load, max_allowable_load, year, dod, rte, timestep):
    timestep = timestep / 60
    
    battery_need = load - max_allowable_load
    
    battery_need = battery_need.clip(lower=0)
    degradation = degradation_profile(year)/100
    
    dfs = [battery_need for _, battery_need in battery_need.groupby((battery_need['Total load (kW)'] == 0).cumsum())]
    
    sums = []
    for i in dfs:
        sums.append(np.sum(i.values))

    required_power = np.max(battery_need)
    required_power = required_power/degradation/dod
    
    required_energy = np.max(sums)*timestep
    required_energy = required_energy/degradation/dod/rte

    output = "Minimum Power: " + str(required_power) + "kW, Minimum Energy: " + str(required_energy) + "kWh"
    
    return required_power, required_energy, output


def charging_cycle(load, kw, kwh, upper_threshold, timestep):
    lower_threshold = upper_threshold - kw
    battery_remaining_life = kwh
    battery_kw = []
    battery_kwh = []
    
    for i in load.values:
        upper_difference = i[0] - upper_threshold
        lower_difference = i[0] - lower_threshold
        if upper_difference > 0: #discharging
            upper_difference = min(upper_difference, kw) # go through math/units, change to new variable
            battery_remaining_life -= upper_difference*(timestep/60)
            if battery_remaining_life > 0:
                battery_kw.append(upper_difference)
                battery_kwh.append(battery_remaining_life)
            else:
                battery_kw.append(0)
                battery_kwh.append(0)
                battery_remaining_life = 0
        elif lower_difference <= 0: #charging
            lower_difference = max(lower_difference, -kw)
            battery_remaining_life -= lower_difference*(timestep/60)
            if battery_remaining_life > 0 and battery_remaining_life <= kwh:
                battery_kw.append(lower_difference)
                battery_kwh.append(battery_remaining_life)
            else:
                battery_kw.append(0)
                battery_kwh.append(kwh)
                battery_remaining_life = kwh
    
        else:
            battery_kw.append(0)
            battery_kwh.append(battery_remaining_life)
    return battery_kw, battery_kwh


st.title("CEP Energy Storage: Custom Battery Sizing")

load = st.file_uploader("Upload the transformer load as a csv", type="csv")
load = pd.read_csv(load, header=None, names=['Total load (kW)'])
timestep = st.number_input("Enter the timestep of the transformer load (in minutes): ", value = 0)
threshold = st.number_input("Enter the rated transformer capacity (in kW): ", value = 0)
year = st.number_input("Enter the number of years the battery has degraded (from 0-15): ", value = 0)
dod = st.number_input("Enter the depth of discharge (from 0-1): ", value = 0)
rte = st.number_input("Enter the round-trip efficiency (from 0-1): ", value = 0)

start = st.number_input("Enter the charging plot's starting hour (use 0 to start plot at the beginning of the transformer load csv): ", value = 0)
end = st.number_input("Enter the charging plot's ending hour (use -1 to end plot at the end of the transformer load csv): ", value = -1)

st.write(load)

kw, kwh, output = batt_size(load, threshold, year, dod, rte, timestep)
output_kw, output_kwh = charging_cycle(load, kw, kwh, threshold, timestep)

st.subheader("Suggested battery size")
st.write(output)

st.subheader("Battery Charging/Discharging Profile")
existing_load_new = [i[0] for i in load.values[start:end]]

fig, ax = plt.subplots()

ax.plot(output_kw[start:end], label = "Battery")
ax.plot(load.values[start:end], label = "Transformer Load")
ax.plot(np.subtract(existing_load_new, output_kw[start:end]), label = "Net Load")
# ax.plot([threshold]*len(load), '--', label = "")
# ax.plot([threshold - kw]*len(load), '--', label = "")
# ax.plot([kw]*len(load), '--', label = "")
# ax.plot([-kw]*len(load), '--', label = "")

ax.set_xlabel("Hour")
ax.set_ylabel("Load (kW)")
ax.legend()

st.pyplot(fig)
