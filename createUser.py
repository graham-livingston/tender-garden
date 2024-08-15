import sqlite3

# Connect to the SQLite database (or create it if it doesn't exist)
conn = sqlite3.connect('example.db')

# Create a cursor object using the cursor() method
cursor = conn.cursor()

# Insert a user with username "hello" and password "world"
cursor.execute('''
INSERT INTO users (username, password) VALUES (?, ?)
''', ('hello', 'world'))

# Commit the transaction
conn.commit()

# Close the connection
conn.close()

print("User 'hello' added successfully.")
