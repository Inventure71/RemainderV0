import sqlite3
import os

class MessageDatabaseHandler:
    def __init__(self, db_name="Databases/messages.db"):
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
                project TEXT,
                files TEXT,
                extra TEXT,
                processed INTEGER DEFAULT 0,
                remind TEXT,
                importance TEXT
            )
        """)
        self.conn.commit()

    def add_message(self, message):
        self.cursor.execute("INSERT INTO messages (content, timestamp, project, files, extra, processed, remind, importance) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                            (message['content'], message['timestamp'], message['project'], message['files'], message['extra'], message['remind'], message['importance'], message.get('processed', False)))
        self.conn.commit()

        # Get the last inserted ID
        self.cursor.execute("SELECT last_insert_rowid()")
        last_id = self.cursor.fetchone()[0]
        return last_id

    def update_message(self, task_id, content=None, timestamp=None, project=None, files=None, extra=None, processed=None, remind=None, importance=None):
        """
        Update any component of a message by its ID.
        Only the provided parameters will be updated.

        Parameters:
        - task_id: ID of the message to update
        - content: New content text (optional)
        - timestamp: New timestamp (optional)
        - project: New project name (optional)
        - files: New files data (optional)
        - extra: New extra data (optional)
        - processed: New processed value (optional)
        """
        # Start building the update query
        update_parts = []
        values = []

        # Add each parameter that is not None to the update query
        if content is not None:
            update_parts.append("content = ?")
            values.append(content)

        if timestamp is not None:
            update_parts.append("timestamp = ?")
            values.append(timestamp)

        if project is not None:
            update_parts.append("project = ?")
            values.append(project)

        if remind is not None:
            update_parts.append("remind = ?")
            values.append(remind)

        if importance is not None:
            update_parts.append("importance = ?")
            values.append(importance)

        if files is not None:
            update_parts.append("files = ?")
            values.append(files)

        if extra is not None:
            update_parts.append("extra = ?")
            values.append(extra)

        if processed is not None:
            update_parts.append("processed = ?")
            values.append(int(processed))

        # If no updates are provided, just return
        if not update_parts:
            return

        # Combine the SQL parts and add the task_id
        sql = f"UPDATE messages SET {', '.join(update_parts)} WHERE id = ?"
        values.append(task_id)

        # Execute the update
        self.cursor.execute(sql, values)
        self.conn.commit()

    def delete_message(self, message_id):
        self.cursor.execute("DELETE FROM messages WHERE id = ?", (message_id,))
        self.conn.commit()

    def get_project_messages(self, project_name=None, only_unprocessed=False):
        # gets all messages if no name is specified
        if project_name:
            if only_unprocessed:
                self.cursor.execute("SELECT id, content, timestamp, project, files, processed, remind, importance FROM messages WHERE project = ? AND processed = 0", (project_name,))
            else:
                self.cursor.execute("SELECT id, content, timestamp, project, files, processed, remind, importance FROM messages WHERE project = ?", (project_name,))
        else:
            if only_unprocessed:
                self.cursor.execute("SELECT id, content, timestamp, project, files, processed, remind, importance FROM messages WHERE processed = 0")
            else:
                self.cursor.execute("SELECT id, content, timestamp, project, files, processed, remind, importance FROM messages")

        rows = self.cursor.fetchall()
        messages = []
        for row in rows:
            messages.append({
                "id": row[0],
                "content": row[1],
                "timestamp": row[2],
                "project": row[3],
                "files": row[4],
                "processed": bool(row[5]),
                "remind": row[6],
                "importance": row[7]
            })
        return messages

    def close(self):
        if self.conn:
            self.conn.close()
