import requests
import json
import time

# Constants
co2_per_kwh = 22.301  # g CO2 per kWh

# Global variables
total_co2_emissions = 0.0
total_energy_kwh = 0.0

def get_netio_data(ip_address):
    """
    Retrieves the JSON data from a Netio PowerBox at the specified IP address.

    Args:
        ip_address (str): The IP address of the Netio PowerBox.

    Returns:
        dict: The JSON data retrieved from the Netio PowerBox.
    """
    endpoint = f"http://{ip_address}/netio.json"

    try:
        # Make the API call
        response = requests.get(endpoint)
        response.raise_for_status()  # Check if the request was successful (status code 200)

        # Parse the JSON response
        data = response.json()

        return data

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None

def get_current_load(ip_address) -> float:
    """
    Retrieves the current load in watts from the Netio PowerBox.

    Args:
        ip_address (str): The IP address of the Netio PowerBox.

    Returns:
        float: The current power load in watts.
    """
    data = get_netio_data(ip_address)
    if data and 'Outputs' in data:
        # Assuming we are interested in the second object in the Outputs list
        power_in_watts = data['Outputs'][1]['Load']
        return power_in_watts
    else:
        return 0.0

def monitor_energy_usage(ip_address):
    global total_co2_emissions, total_energy_kwh
    
    while True:
        power_in_watts = get_current_load(ip_address)

        # Convert power to energy in kWh (Watt to kW is divided by 1000, then multiplied by the time in hours)
        energy_kwh = power_in_watts / 1000.0 * (1 / 3600)  # power in kW * time in hours (assuming 1 second intervals)

        # Update total energy and CO2 emissions
        total_energy_kwh += energy_kwh
        co2_emissions = energy_kwh * co2_per_kwh / 1000.0  # Convert g to kg
        total_co2_emissions += co2_emissions

        # Print the current status
        print(f"Current power: {power_in_watts} W")
        print(f"Total energy used: {total_energy_kwh:.6f} kWh")
        print(f"Total CO2 emissions: {total_co2_emissions:.6f} kg")

        # Wait for 1 second before the next measurement
        time.sleep(1)

# Example usage
if __name__ == "__main__":
    ip_address = "192.168.1.89"
    monitor_energy_usage(ip_address)
