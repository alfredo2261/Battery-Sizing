import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def degradation_profile(year):
    health = [
        (97.4+97.8)/2,
        (93.49+93.5)/2,
        (90.75+90)/2,
        (88.11+88)/2,
        (85.95+86)/2,
        (83.7+84.5)/2,
        (81.81+82.5)/2,
        (80.01+80.5)/2,
        (78.05+79)/2,
        (76.39+77.5)/2,
        (74.78+76)/2,
        (73+74.5)/2,
        (71.48+73)/2,
        (70+72)/2,
        (68.34+71)/2,
        (66.93+70)/2
    ]
    return health[year]

# def degradation_profile(year):
#     health = [
#         98,
#         98*.98,
#         98*.98**2,
#         98*.98**3,
#         98*.98**4,
#         98*.98**5,
#         98*.98**6,
#         98*.98**7,
#         98*.98**8,
#         98*.98**9,
#         98*.98**10,
#         98*.98**11,
#         98*.98**12,
#         98*.98**13,
#         98*.98**14,
#         98*.98**15
#     ]
#     return health[year]


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

    required_power = np.round(required_power/1000, decimals=2)
    required_energy = np.round(required_energy/1000, decimals=2)

    output = "Minimum Power: " + str(required_power) + "MW, Minimum Energy: " + str(required_energy) + "MWh"
    
    return required_power, required_energy, output


def charging_cycle(load, kw, kwh, upper_threshold, timestep, rte):
    lower_threshold = upper_threshold - kw
    battery_remaining_life = kwh
    battery_kw = []
    battery_kwh = []
    
    for i in load.values:
        upper_difference = i[0] - upper_threshold
        lower_difference = i[0] - lower_threshold
        if upper_difference > 0: #discharging
            upper_difference = min(upper_difference, kw)*rte # go through math/units, change to new variable
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


st.title("BESS-SP: Battery Energy Storage System Sizing Planner")

load = st.file_uploader("Upload the transformer load as a csv", type="csv")

if load is not None:
    load = pd.read_csv(load, header=None, names=['Total load (kW)'])
    timestep = st.number_input("Enter the time interval of the transformer load (in minutes): ", value = 0)
    threshold = st.number_input("Enter the transformer normal thermal rating (in kVa): ", value = 0)
    year = st.number_input("Enter the number of years the traditional solution will be deferred (from 0-15): ", value = 0)
    dod = st.number_input("Enter the depth of discharge of the battery (from 0-1): ", value = 0.0, step=0.1)
    rte = st.number_input("Enter the round-trip efficiency of the battery (from 0-1): ", value = 0.0, step=0.1)
    
    start = st.number_input("Enter the charging plot's starting hour (use 0 to start plot at the first time interval of your load csv): ", value = 0)
    end = st.number_input("Enter the charging plot's ending hour (use -1 to end plot at the last time interval of your load csv): ", value = -1)
    
    kw, kwh, output = batt_size(load, threshold, year, dod, rte, timestep)
    output_kw, output_kwh = charging_cycle(load, kw, kwh, threshold, timestep, rte)
    
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

    # st.write(output_kw)
    # st.write(load.values)
    # st.write(np.subtract(existing_load_new, output_kw[start:end]))
    
    # data = pd.DataFrame({
    #     'Battery':np.array(output_kw),
    #     'Transformer Load':load.values.ravel(),
    #     'Net Load':np.subtract(existing_load_new, output_kw[start:end]).ravel()
    # })
    
    # st.dataframe(data)
    
    # csv = data.to_csv(index=False).encode("utf-8")
    
    # st.download_button(
    #     "Download CSV",
    #     csv,
    #     "charging_discharging_profile.csv",
    #     "text/csv"
    # )

