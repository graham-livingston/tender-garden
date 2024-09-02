import sqlite3

def get_db_connection():
    conn = sqlite3.connect('example.db')
    conn.row_factory = sqlite3.Row
    return conn

def reset_Energy_log():
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()


    # Delete all existing records from the table
    cursor.execute('DELETE FROM energyRecords')

    # Add a new record with hardcoded values
    new_datetime = '2024-08-16 15:00:00'  # Hardcoded datetime
    total_co2_emissions = 0.0             # Hardcoded CO2 emissions
    total_energy_kwh = 0.0                # Hardcoded energy usage

    cursor.execute('''INSERT INTO energyRecords (datetime, total_co2_emissions, total_energy_kwh)
                    VALUES (?, ?, ?)''', (new_datetime, total_co2_emissions, total_energy_kwh))

    # Commit the transaction
    conn.commit()

    # Close the connection
    conn.close()

    print("Energy records have been cleared and a new record added successfully.")

if __name__ == "__main__":
    reset_Energy_log()
