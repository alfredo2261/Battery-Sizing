import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# def degradation_profile(year):
#     health = [
#         (97.4+97.8)/2,
#         (93.49+93.5)/2,
#         (90.75+90)/2,
#         (88.11+88)/2,
#         (85.95+86)/2,
#         (83.7+84.5)/2,
#         (81.81+82.5)/2,
#         (80.01+80.5)/2,
#         (78.05+79)/2,
#         (76.39+77.5)/2,
#         (74.78+76)/2,
#         (73+74.5)/2,
#         (71.48+73)/2,
#         (70+72)/2,
#         (68.34+71)/2,
#         (66.93+70)/2
#     ]
#     return health[year]

# def degradation_profile(year):
#     health = [
#         100,
#         100*.985,
#         100*.985**2,
#         100*.985**3,
#         100*.985**4,
#         100*.985**5,
#         100*.985**6,
#         100*.985**7,
#         100*.985**8,
#         100*.985**9,
#         100*.985**10,
#         100*.985**11,
#         100*.985**12,
#         100*.985**13,
#         100*.985**14,
#         100*.985**15,
#         100*.985**16,
#         100*.985**17,
#         100*.985**18,
#         100*.985**19,
#         100*.985**20,
#         100*.985**21
#     ]
#     return health[year]

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

# def degradation_profile(year):
#     health = [
#         100,
#         100*.99,
#         100*.99**2,
#         100*.99**3,
#         100*.99**4,
#         100*.99**5,
#         100*.99**6,
#         100*.99**7,
#         100*.99**8,
#         100*.99**9,
#         100*.99**10,
#         100*.99**11,
#         100*.99**12,
#         100*.99**13,
#         100*.99**14,
#         100*.99**15,
#         100*.99**16,
#         100*.99**17,
#         100*.99**18,
#         100*.99**19,
#         100*.99**20,
#         100*.99**21,
#     ]
#     return health[year]


def batt_size(load, max_allowable_load, year, dod, rte, timestep, growth_rate, degradation):
    load = load*(1+growth_rate)**year
    timestep = timestep / 60
    
    battery_need = load - max_allowable_load
    
    battery_need = battery_need.clip(lower=0)
    #degradation = degradation_profile(year)/100
    degradation = 100*(1-degradation)**year
    
    dfs = [battery_need for _, battery_need in battery_need.groupby((battery_need == 0).cumsum())]
    
    sums = []
    for i in dfs:
        sums.append(np.sum(i.values))

    required_power = np.max(battery_need)
    required_power = required_power/dod
    
    required_energy = np.max(sums)*timestep
    required_energy = required_energy/degradation/dod/rte

    required_power_output = np.round(required_power/1000, decimals=2)
    required_energy_output = np.round(required_energy/1000, decimals=2)

    output = "Minimum Power: " + str(required_power_output) + "MW, Minimum Energy: " + str(required_energy_output) + "MWh"
    
    return required_power, required_energy, output


def charging_cycle(load, kw, kwh, upper_threshold, timestep, rte):
    lower_threshold = upper_threshold - kw
    battery_remaining_life = kwh
    battery_kw = []
    battery_kwh = []
    for i in load.values:
        
        upper_difference = i - upper_threshold
        lower_difference = i - lower_threshold
        if upper_difference > 0: #discharging
            upper_difference = min(upper_difference, kw)#*rte # go through math/units, change to new variable
            battery_remaining_life -= upper_difference*(timestep/60)
            if battery_remaining_life > 0:
                battery_kw.append(upper_difference)
                battery_kwh.append(battery_remaining_life)
            else:
                battery_kw.append(0)
                battery_kwh.append(0)
                battery_remaining_life = 0
        elif lower_difference <= 0: #charging
            lower_difference = max(lower_difference, -kw)/rte
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
    load = pd.read_csv(load, header=None, names=['Date', 'Total load (kW)'])
    total_load = load['Total load (kW)']
    date = pd.to_datetime(load['Date'])
    
    timestep = st.number_input("Enter the time interval of the transformer load (in minutes): ", value = 0)
    threshold = st.number_input("Enter the transformer normal thermal rating (in kVa): ", value = 0)
    year = st.number_input("Enter the number of years the traditional solution will be deferred (from 0-15): ", value = 0)
    growth_rate = st.number_input("Enter the annual load growth rate (from 0-1): ", value = 0.0, step=0.1)
    degradation = st.number_input("Enter the annual degradation rate (from 0-1): ", value = 0.0, step=0.1)
    dod = st.number_input("Enter the depth of discharge of the battery (from 0-1): ", value = 0.0, step=0.1)
    rte = st.number_input("Enter the round-trip efficiency of the battery (from 0-1): ", value = 0.0, step=0.1)
    
    #start = st.number_input("Enter the charging plot's starting hour (use 0 to start plot at the first time interval of your load csv): ", value = 0)
    #end = st.number_input("Enter the charging plot's ending hour (use -1 to end plot at the last time interval of your load csv): ", value = -1)
    
    kw, kwh, output = batt_size(total_load, threshold, year, dod, rte, timestep, growth_rate, degradation)
    output_kw, output_kwh = charging_cycle(total_load, kw, kwh, threshold, timestep, rte)
    
    st.subheader("Suggested battery size")
    st.markdown(
        f"<p style='text-align: center; font-size: 28px;'>{output}</p>",
        unsafe_allow_html=True
    )
    
    st.subheader("Battery Charging/Discharging Profile")
    #existing_load_new = [i[0] for i in total_load.values]
    
    fig, ax = plt.subplots()
    
    ax.plot(date, output_kw, label = "Battery")
    ax.plot(date, total_load.values, label = "Transformer Load")
    ax.plot(date, np.subtract(total_load, output_kw), label = "Net Load")
    
    # ax.plot([threshold]*len(load), '--', label = "")
    # ax.plot([threshold - kw]*len(load), '--', label = "")
    # ax.plot([kw]*len(load), '--', label = "")
    # ax.plot([-kw]*len(load), '--', label = "")

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
    ax.set_xlabel("Date")
    ax.set_ylabel("Load (kW)")
    ax.tick_params(axis='x', labelrotation=45)
    ax.legend()
    
    st.pyplot(fig)
    
    data = pd.DataFrame({
        'Date':date,
        'Battery':np.array(output_kw),
        'Transformer Load':total_load.values.ravel(),
        'Net Load':np.subtract(total_load, output_kw).ravel()
    })
    
    st.dataframe(data)
    
    csv = data.to_csv(index=False).encode("utf-8")
    
    st.download_button(
        "Download Charging/Discharging Profile as CSV",
        csv,
        "charging_discharging_profile.csv",
        "text/csv"
    )

