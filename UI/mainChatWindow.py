import tkinter as tk
from UI.topBar import TopBar
from UI.scrollableMessageBox import ScrollableMessageArea

class MainChatWindow(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#2c2c2c")  # dark bg if you want like in screenshot
        self.controller = controller

        # Configure the main layout to stretch
        self.grid_rowconfigure(1, weight=1)  # Scrollable area
        self.grid_columnconfigure(0, weight=1)

        # --- Top Bar ---
        TopBar(self, controller).grid(row=0, column=0, sticky="ew")

        # --- Scrollable Chat Area ---
        self.scrollable_area = ScrollableMessageArea(self)
        self.scrollable_area.grid(row=1, column=0, sticky="nsew")

        # --- Bottom Input Bar ---
        input_frame = tk.Frame(self, bg="lightgray", padx=10, pady=10)
        input_frame.grid(row=2, column=0, sticky="ew")

        input_frame.grid_columnconfigure(0, weight=1)

        self.message_entry = tk.Entry(input_frame, font=("Arial", 12))
        self.message_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        send_button = tk.Button(input_frame, text="Send", command=self.send_message)
        send_button.grid(row=0, column=1)

    def send_message(self):
        text = self.message_entry.get().strip()
        if text:
            self.scrollable_area.add_message(text, assigned_project=None, project_list=["Project Alpha", "BetaTeam", "Notes"])
            self.message_entry.delete(0, tk.END)

    def populate_chat_area(self, messages):
        """Populate the chat area with messages from the database"""
        for message in messages:
            self.scrollable_area.add_message(message['text'], assigned_project=message.get('project'), project_list=["Project Alpha", "BetaTeam", "Notes"])