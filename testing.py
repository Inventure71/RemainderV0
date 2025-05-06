import sqlite3
import os

db_name = "Databases/messages.db"
db_path = os.path.join(os.getcwd(), db_name) # Ensure correct path

print(f"Attempting to connect to database at: {db_path}")

if not os.path.exists(db_path):
    print(f"Database file not found at {db_path}. Nothing to do.")
else:
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print("Successfully connected to the database.")

        # Drop the message_images table if it exists
        cursor.execute("DROP TABLE IF EXISTS message_images;")
        conn.commit()
        print("'message_images' table has been dropped. It will be recreated on next app start.")

    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        if conn:
            conn.close()
            print("Database connection closed.")