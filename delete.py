import sqlite3

def clear_table(table_name):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute(f"DELETE FROM {table_name}")  # delete all rows
    conn.commit()
    conn.close()
    print(f"All data deleted from {table_name}.")

if __name__ == "__main__":
    clear_table("users")           # clear users
    clear_table("appointments")    # clear appointments
    clear_table("consultations")   # clear consultations
    clear_table("messages")        # clear messages
