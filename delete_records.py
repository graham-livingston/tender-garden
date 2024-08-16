import sqlite3

def get_db_connection():
    conn = sqlite3.connect('example.db')
    conn.row_factory = sqlite3.Row
    return conn

def delete_all_records():
    # Connect to the database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Delete all records in the 'records' table
    cursor.execute("DELETE FROM records")

    # Commit the changes and close the connection
    conn.commit()
    conn.close()

    print("All records have been deleted successfully.")

# Call the function to delete all records
delete_all_records()
