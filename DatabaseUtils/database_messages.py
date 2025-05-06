import sqlite3
import os
import sys # Import sys

class MessageDatabaseHandler:
    def __init__(self, db_name=None):
        if db_name is None:
            # Determine base path for data files
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                # Running in a PyInstaller bundle or similar
                # For writable data, always use a user-specific directory
                app_support_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'RemainderApp')
            else:
                # Running in a normal Python environment, still good practice to define
                # a clear data directory, perhaps relative to project for dev,
                # but for consistency let's use App Support here too, or a local "Databases" for dev.
                # For simplicity in this refactor, we'll point to a local "Databases" dir for dev.
                # If you want dev to also use App Support, uncomment the line above.
                # app_support_dir = os.path.join(os.path.expanduser('~'), 'Library', 'Application Support', 'RemainderApp')
                # Using local "Databases" for non-frozen (dev) mode:
                app_support_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Databases")


            os.makedirs(app_support_dir, exist_ok=True) # Ensure the directory exists
            self.db_name = os.path.join(app_support_dir, "messages.db")
        else:
            # If a db_name is explicitly passed, use it (e.g., for tests with in-memory DB)
            self.db_name = db_name
            # Ensure directory for explicitly passed db_name also exists if it's a file path
            db_dir = os.path.dirname(self.db_name)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)


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
                importance TEXT,
                reoccurences TEXT,
                done INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

        # New table for message images
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS message_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (message_id) REFERENCES messages (id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def add_message(self, message):
        self.cursor.execute("INSERT INTO messages (content, timestamp, project, files, extra, processed, remind, importance, reoccurences, done) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (message['content'], message['timestamp'], message['project'], message['files'], message['extra'], message['processed'], message['remind'], message['importance'], message.get('reoccurences', None), message.get('done', 0)))
        self.conn.commit()

        # Get the last inserted ID
        self.cursor.execute("SELECT last_insert_rowid()")
        last_id = self.cursor.fetchone()[0]
        return last_id

    def add_message_image(self, message_id, file_path, created_at):
        self.cursor.execute("INSERT INTO message_images (message_id, file_path, created_at) VALUES (?, ?, ?)",
                            (message_id, file_path, created_at))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_message_images(self, message_id):
        self.cursor.execute("SELECT id, file_path, description, created_at FROM message_images WHERE message_id = ?", (message_id,))
        rows = self.cursor.fetchall()
        images = []
        for row in rows:
            images.append({
                "id": row[0],
                "file_path": row[1],
                "description": row[2],
                "created_at": row[3]
            })
        return images

    def update_message(self, task_id, content=None, timestamp=None, project=None, files=None, extra=None, processed=None, remind=None, importance=None, reoccurences=None, done=None):
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
        - remind: New remind value (optional)
        - importance: New importance value (optional)
        - reoccurences: New reoccurences value (optional)
        - done: New done value (optional)
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

        if reoccurences is not None:
            update_parts.append("reoccurences = ?")
            values.append(reoccurences)

        if done is not None:
            update_parts.append("done = ?")
            values.append(int(done))

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
                self.cursor.execute("SELECT id, content, timestamp, project, files, extra, processed, remind, importance, reoccurences, done FROM messages WHERE project = ? AND processed = 0", (project_name,))
            else:
                self.cursor.execute("SELECT id, content, timestamp, project, files, extra, processed, remind, importance, reoccurences, done FROM messages WHERE project = ?", (project_name,))
        else:
            if only_unprocessed:
                self.cursor.execute("SELECT id, content, timestamp, project, files, extra, processed, remind, importance, reoccurences, done FROM messages WHERE processed = 0")
            else:
                self.cursor.execute("SELECT id, content, timestamp, project, files, extra, processed, remind, importance, reoccurences, done FROM messages")

        rows = self.cursor.fetchall()
        messages = []
        for row in rows:
            messages.append({
                "id": row[0],
                "content": row[1],
                "timestamp": row[2],
                "project": row[3],
                "files": row[4],
                "extra": row[5],
                "processed": bool(row[6]),
                "remind": row[7],
                "importance": row[8],
                "reoccurences": row[9] if len(row) > 9 else None,
                "done": bool(row[10]) if len(row) > 10 else False
            })
        return messages

    def get_reminder_messages(self):
        """Fetches all messages that have a reminder set (done or not done)."""
        self.cursor.execute("""
            SELECT id, content, timestamp, project, files, extra, processed, remind, importance, reoccurences, done
            FROM messages
            WHERE remind IS NOT NULL AND remind != ''
            ORDER BY done ASC, remind ASC  -- Show active first, then ordered by time
        """)
        rows = self.cursor.fetchall()
        messages = []
        for row in rows:
            messages.append({
                "id": row[0],
                "content": row[1],
                "timestamp": row[2],
                "project": row[3],
                "files": row[4],
                "extra": row[5],
                "processed": bool(row[6]),
                "remind": row[7],
                "importance": row[8],
                "reoccurences": row[9],
                "done": bool(row[10])
            })
        return messages

    def close(self):
        if self.conn:
            self.conn.close()
