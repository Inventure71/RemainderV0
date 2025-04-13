import sqlite3
import os

class MessageDatabaseHandler:
    def __init__(self, db_name="messages.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self._connect()
        self._create_table()

    def _connect(self):
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()

    def _create_table(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                project TEXT NOT NULL,
                files TEXT NOT NULL,
                extra TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def add_message(self, message):
        self.cursor.execute("INSERT INTO messages (content, timestamp, project, files, extra) VALUES (?, ?, ?, ?, ?)",
                            (message['content'], message['timestamp'], message['project'], message['files'], message['extra']))
        self.conn.commit()

    def update_message(self, task_id, new_content): # only modifies text
        self.cursor.execute("UPDATE messages SET content = ? WHERE id = ?", (new_content, task_id))
        self.conn.commit()

    def delete_message(self, task_id):
        self.cursor.execute("DELETE FROM messages WHERE id = ?", (task_id,))
        self.conn.commit()

    def get_all_messages(self):
        self.cursor.execute("SELECT id, category, description FROM messages")
        return self.cursor.fetchall()

    def close(self):
        if self.conn:
            self.conn.close()
