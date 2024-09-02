import sqlite3

# Connect to the SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('example.db')

# Create a cursor object using the cursor() method
cursor = conn.cursor()

cursor.execute('''CREATE TABLE IF NOT EXISTS energyRecords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    datetime TEXT NOT NULL,
    total_co2_emissions REAL NOT NULL,
    total_energy_kwh REAL NOT NULL
);''')

# Commit the transaction
conn.commit()

# Close the connection
conn.close()

print("energyRecords table created sucessfully.")
