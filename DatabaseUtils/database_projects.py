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
        # Run migrations
        self._migrate_add_column('color', 'TEXT DEFAULT "#dddddd"')
        self._migrate_add_column('emoji', 'TEXT DEFAULT "📁"') # Default emoji

    def _migrate_add_column(self, column_name, column_type):
        """Adds a column to the projects table if it doesn't exist."""
        self.cursor.execute(f"PRAGMA table_info(projects)")
        columns = [info[1] for info in self.cursor.fetchall()]
        if column_name not in columns:
            try:
                self.cursor.execute(f"ALTER TABLE projects ADD COLUMN {column_name} {column_type}")
                self.conn.commit()
                print(f"Successfully added column '{column_name}' to projects table.")
            except sqlite3.Error as e:
                print(f"Failed to add column '{column_name}': {e}")
                # Consider rolling back if necessary, though commit might have already happened
                self.conn.rollback() 

    def add_project(self, project_name, timestamp, project_description=None, extra=None, user_created=1, color="#dddddd", emoji="📁"):
        if project_description is None:
            project_description = ""
        if extra is None:
            extra = ""
        if emoji is None or not isinstance(emoji, str) or len(emoji) > 2: # Basic emoji validation
             emoji = "📁" # Fallback to default if invalid

        self.cursor.execute("INSERT INTO projects (name, description, timestamp, extra, user_created, color, emoji) VALUES (?, ?, ?, ?, ?, ?, ?)",
                            (project_name, project_description, timestamp, extra, user_created, color, emoji))

        self.conn.commit()

    def update_project(self, task_id , new_name=None, new_description=None, user_created=None, color=None, emoji=None):
        # Start building the update query dynamically
        update_parts = []
        values = []

        if new_name is not None:
            update_parts.append("name = ?")
            values.append(new_name)
        if new_description is not None:
            update_parts.append("description = ?")
            values.append(new_description)
        if user_created is not None:
            update_parts.append("user_created = ?")
            values.append(user_created)
        if color is not None:
            update_parts.append("color = ?")
            values.append(color)
        if emoji is not None:
            # Basic validation for emoji input
            if isinstance(emoji, str) and len(emoji) < 3: # Allow single char or empty string
                update_parts.append("emoji = ?")
                values.append(emoji)
            else:
                print(f"[Warning] Invalid emoji provided for project {task_id}: {emoji}")

        if not update_parts:
            print("No valid fields provided for project update.")
            return # Nothing to update

        sql = f"UPDATE projects SET {', '.join(update_parts)} WHERE id = ?"
        values.append(task_id)

        try:
            self.cursor.execute(sql, values)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Error updating project {task_id}: {e}")
            self.conn.rollback()

    def delete_project(self, task_id):
        self.cursor.execute("DELETE FROM projects WHERE id = ?", (task_id,))
        self.conn.commit()

    def get_all_projects(self):
        # Ensure all expected columns are selected
        self.cursor.execute("SELECT id, name, description, timestamp, extra, user_created, color, emoji FROM projects")
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
                "color": row[6] if row[6] else "#dddddd",
                "emoji": row[7] if len(row) > 7 and row[7] else "📁" # Add emoji with default
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
