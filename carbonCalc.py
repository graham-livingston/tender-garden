import time
total_co2_emissions = 0.0
total_energy_kwh = 0.0

# enquire with electrical company
emission_factor = 0.42 #kg Co2e per kWh

def get_current_load() -> float: 
    
    #api call to get load roughly 204 W
    
    return 204

def monitor_energy_usage():
    global total_co2_emissions, total_energy_kwh
    
    while True:
        
        power_in_total = get_current_load()
    