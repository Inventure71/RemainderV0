import tkinter as tk
from datetime import datetime

from UI.widget_model_chat import WidgetModelChat
from UI.components.widget_top_nav_bar import TopBar
from UI.components.scrollable_messages_box import ScrollableMessageArea

from DatabaseUtils.database_messages import MessageDatabaseHandler


class MainChatWindow(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#23272e")  # unified dark bg

        self.controller = controller
        self.message_db = MessageDatabaseHandler()

        # Configure the main layout to stretch
        self.grid_rowconfigure(1, weight=1)  # Scrollable area
        self.grid_columnconfigure(0, weight=5)  # Give more weight to the main chat area
        self.grid_columnconfigure(10, weight=1)  # Make model chat column narrower

        # --- Top Bar ---
        TopBar(self, controller).grid(row=0, column=0, sticky="ew", columnspan=2)

        # --- Scrollable Chat Area ---
        self.scrollable_area = ScrollableMessageArea(self, db_manager=self.message_db)
        self.scrollable_area.grid(row=1, column=0, sticky="nsew", padx=18, pady=(12, 6))

        # --- Bottom Input Bar ---
        self.input_frame = tk.Frame(self, bg="#303441", padx=16, pady=8)
        self.input_frame.grid(row=2, column=0, sticky="ew", columnspan=2)
        self.input_frame.grid_columnconfigure(0, weight=1)

        self.message_entry = tk.Entry(self.input_frame, font=("Arial", 13), bg="#23272e", fg="#f7f7f7", insertbackground="#f7f7f7", bd=1, relief="flat", highlightthickness=1, highlightbackground="#44495a")
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 12), pady=2)

        send_button = tk.Button(self.input_frame, text="Send", command=self.send_message, font=("Arial", 12, "bold"), bg="#3578e5", fg="black", activebackground="#2851a3", activeforeground="black", bd=0, padx=18, pady=8, relief="flat")
        send_button.grid(row=0, column=1, pady=2)

        self.messages = None
        self.refresh()

        self.model_chat = WidgetModelChat(self)

    def refresh(self):
        # --- Load Messages from Database ---
        self.messages = self.message_db.get_project_messages()
        print(self.messages)

        self.populate_chat_area(self.messages)

    def send_message(self, project_name=None):
        text = self.message_entry.get().strip()
        if text:
            index = self.message_db.add_message({'content': text, 'project': project_name, 'timestamp': datetime.now(), 'files': None, 'extra': None, 'remind':None, 'importance':None})
            self.scrollable_area.add_message(text, message_id=index, assigned_project=project_name)
            self.message_entry.delete(0, tk.END)

    def populate_chat_area(self, messages):
        """Populate the chat area with messages from the database"""
        self.scrollable_area = ScrollableMessageArea(self, db_manager=self.message_db)
        self.scrollable_area.grid(row=1, column=0, sticky="nsew", padx=18, pady=(12, 6))

        for message in messages:
            self.scrollable_area.add_message(message['content'], message_id=message["id"] ,assigned_project=message.get('project'), project_list=[])
