import time
import tkinter as tk
from UI.components.widget_top_nav_bar import TopBar
from UI.components.scrollable_messages_box import ScrollableMessageArea

from DatabaseUtils.database_messages import MessageDatabaseHandler
from DatabaseUtils.database_projects import ProjectsDatabaseHandler

class MainChatWindow(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#2c2c2c")  # dark bg if you want like in screenshot

        self.controller = controller
        self.message_db = MessageDatabaseHandler()


        # Configure the main layout to stretch
        self.grid_rowconfigure(1, weight=1)  # Scrollable area
        self.grid_columnconfigure(0, weight=1)

        # --- Top Bar ---
        TopBar(self, controller).grid(row=0, column=0, sticky="ew")

        # --- Scrollable Chat Area ---
        self.scrollable_area = ScrollableMessageArea(self, db_manager=self.message_db)
        self.scrollable_area.grid(row=1, column=0, sticky="nsew")

        # --- Bottom Input Bar ---
        input_frame = tk.Frame(self, bg="lightgray", padx=10, pady=10)
        input_frame.grid(row=2, column=0, sticky="ew")

        input_frame.grid_columnconfigure(0, weight=1)

        self.message_entry = tk.Entry(input_frame, font=("Arial", 12))
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        send_button = tk.Button(input_frame, text="Send", command=self.send_message)
        send_button.grid(row=0, column=1)


        # --- Load Messages from Database ---
        self.messages = self.message_db.get_all_messages()
        print(self.messages)

        self.populate_chat_area(self.messages)


    def send_message(self):
        text = self.message_entry.get().strip()
        if text:
            self.scrollable_area.add_message(text, assigned_project=None, project_list=["Project Alpha", "BetaTeam", "Notes"])
            self.message_db.add_message({'content': text, 'project': None, 'timestamp': time.time(), 'files': None, 'extra': None})
            self.message_entry.delete(0, tk.END)

    def populate_chat_area(self, messages):
        """Populate the chat area with messages from the database"""
        for message in messages:
            self.scrollable_area.add_message(message['content'], message_id=message["id"] ,assigned_project=message.get('project'), project_list=["Project Alpha", "BetaTeam", "Notes"])