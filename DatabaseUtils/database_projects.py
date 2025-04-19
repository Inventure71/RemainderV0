import sqlite3
import os

class ProjectsDatabaseHandler:
    _projects = None

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
                extra TEXT NOT NULL,
                user_created INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()
        # Migration: add 'color' column if it doesn't exist
        self._migrate_add_color_column()

    def _migrate_add_color_column(self):
        self.cursor.execute("PRAGMA table_info(projects)")
        columns = [info[1] for info in self.cursor.fetchall()]
        if 'color' not in columns:
            self.cursor.execute("ALTER TABLE projects ADD COLUMN color TEXT DEFAULT '#dddddd'")
            self.conn.commit()

    def add_project(self, project_name, timestamp, project_description=None, extra=None, user_created=1, color="#dddddd"):
        if project_description is None:
            project_description = ""

        if extra is None:
            extra = ""

        self.cursor.execute("INSERT INTO projects (name, description, timestamp, extra, user_created, color) VALUES (?, ?, ?, ?, ?, ?)",
                            (project_name, project_description, timestamp, extra, user_created, color))

        self.conn.commit()

    def update_project(self, task_id , new_name=None, new_description=None, user_created=None, color=None): # only modifies text
        if new_name:
            self.cursor.execute("UPDATE projects SET name = ? WHERE id = ?", (new_name, task_id))
        if new_description:
            self.cursor.execute("UPDATE projects SET description = ? WHERE id = ?", (new_description, task_id))
        if user_created is not None:
            self.cursor.execute("UPDATE projects SET user_created = ? WHERE id = ?", (user_created, task_id))
        if color:
            self.cursor.execute("UPDATE projects SET color = ? WHERE id = ?", (color, task_id))
        self.conn.commit()

    def delete_project(self, task_id):
        self.cursor.execute("DELETE FROM projects WHERE id = ?", (task_id,))
        self.conn.commit()

    def get_all_projects(self):
        self.cursor.execute("SELECT id, name, description, timestamp, extra, user_created, color FROM projects")
        rows = self.cursor.fetchall()
        projects = []

        for row in rows:
            project = {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "timestamp": row[3],
                "extra": row[4],
                "user_created": row[5],
                "color": row[6] if row[6] else "#dddddd"
            }
            projects.append(project)

        ProjectsDatabaseHandler._projects = projects
        return projects

    @classmethod
    def get_projects(cls):
        return cls._projects

    def close(self):
        if self.conn:
            self.conn.close()
