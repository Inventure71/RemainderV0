import sqlite3
import os

class MessageDatabaseHandler:
    def __init__(self, db_name="Databases/projects.db"):
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
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                extra TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def add_project(self, message):
        self.cursor.execute("INSERT INTO projects (name, description, timestamp, extra) VALUES (?, ?, ?, ?)",
                            (message['name'], message['description'], message['timestamp'], message['extra']))
        self.conn.commit()

    def update_project(self, task_id , new_name=None, new_description=None): # only modifies text
        if new_name:
            self.cursor.execute("UPDATE projects SET name = ? WHERE id = ?", (new_name, task_id))
        if new_description:
            self.cursor.execute("UPDATE projects SET description = ? WHERE id = ?", (new_description, task_id))
        self.conn.commit()

    def delete_project(self, task_id):
        self.cursor.execute("DELETE FROM projects WHERE id = ?", (task_id,))
        self.conn.commit()

    def get_all_projects(self):
        self.cursor.execute("SELECT id, category, description FROM projects")
        return self.cursor.fetchall()

    def close(self):
        if self.conn:
            self.conn.close()
