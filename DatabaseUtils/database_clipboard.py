import sqlite3
import os
import sys
from datetime import datetime

class ClipboardMessagesDatabaseHandler:
    def __init__(self, db_name=None):
        if db_name is None:
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                app_support_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'RemainderApp')
            else:
                # Using local "Databases" for non-frozen (dev) mode:
                # Corrected path to be relative to the project root, assuming DatabaseUtils is a top-level sibling of Databases
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # This should go up to RemainderV0 directory
                app_support_dir = os.path.join(base_dir, "Databases")

            os.makedirs(app_support_dir, exist_ok=True)
            self.db_name = os.path.join(app_support_dir, "clipboard_messages.db")
        else:
            self.db_name = db_name
            db_dir = os.path.dirname(self.db_name)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)

        self.conn = None
        self.cursor = None
        self._connect()
        self._create_table()

    def _connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.conn.row_factory = sqlite3.Row # Access columns by name
        self.cursor = self.conn.cursor()

    def _create_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS clipboard_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error creating clipboard_messages table: {e}")

    def add_message(self, content, timestamp):
        try:
            self.cursor.execute("INSERT INTO clipboard_messages (content, timestamp) VALUES (?, ?)",
                                (content, timestamp))
            self.conn.commit()
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            print(f"Error adding clipboard message: {e}")
            return None

    def get_all_messages(self, limit=None, offset=0, sort_by='timestamp', sort_order='DESC'):
        try:
            # Basic validation for sort_by and sort_order to prevent SQL injection
            if sort_by not in ['id', 'content', 'timestamp']:
                sort_by = 'timestamp'
            if sort_order.upper() not in ['ASC', 'DESC']:
                sort_order = 'DESC'

            query = f"SELECT id, content, timestamp FROM clipboard_messages ORDER BY {sort_by} {sort_order}"
            
            if limit is not None:
                query += f" LIMIT {int(limit)} OFFSET {int(offset)}"
            
            self.cursor.execute(query)
            rows = self.cursor.fetchall()
            return [dict(row) for row in rows] # Convert rows to dictionaries
        except sqlite3.Error as e:
            print(f"Error getting all clipboard messages: {e}")
            return []
            
    def get_message_count(self):
        try:
            self.cursor.execute("SELECT COUNT(*) FROM clipboard_messages")
            count = self.cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            print(f"Error getting clipboard message count: {e}")
            return 0

    def delete_message(self, message_id):
        """Deletes a specific message by its ID."""
        try:
            self.cursor.execute("DELETE FROM clipboard_messages WHERE id = ?", (message_id,))
            self.conn.commit()
            return self.cursor.rowcount > 0 # Returns True if a row was deleted
        except sqlite3.Error as e:
            print(f"Error deleting clipboard message with ID {message_id}: {e}")
            return False

    def close(self):
        if self.conn:
            self.conn.close()

if __name__ == '__main__':
    # Example Usage
    # Correct path for direct script execution for testing
    db_path_test = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Databases', 'clipboard_messages_test.db')
    if os.path.exists(db_path_test):
        os.remove(db_path_test)
        
    db_handler = ClipboardMessagesDatabaseHandler(db_name=db_path_test)
    
    print(f"Database created at: {db_handler.db_name}")

    ts1 = datetime.now().isoformat()
    time.sleep(0.1)
    ts2 = datetime.now().isoformat()

    msg_id1 = db_handler.add_message("First clipboard message", ts1)
    msg_id2 = db_handler.add_message("Second clipboard message, longer content here.", ts2)
    
    print(f"Added messages with IDs: {msg_id1}, {msg_id2}")
    
    all_msgs = db_handler.get_all_messages()
    print("\nAll clipboard messages (DESC by timestamp):")
    for msg in all_msgs:
        print(f"  ID: {msg['id']}, Timestamp: {msg['timestamp']}, Content: '{msg['content'][:30]}...'")

    all_msgs_asc = db_handler.get_all_messages(sort_order='ASC')
    print("\nAll clipboard messages (ASC by timestamp):")
    for msg in all_msgs_asc:
        print(f"  ID: {msg['id']}, Timestamp: {msg['timestamp']}, Content: '{msg['content'][:30]}...'")

    print(f"\nTotal clipboard messages: {db_handler.get_message_count()}")
    
    db_handler.close()
    # Clean up test db
    if os.path.exists(db_path_test):
        os.remove(db_path_test)
        print(f"Cleaned up test database: {db_path_test}") 