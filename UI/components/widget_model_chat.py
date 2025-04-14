import tkinter as tk

from UI.components.scrollable_messages_box import ScrollableMessageArea


class WidgetModelChat:
    def __init__(self, parent):
        self.parent = parent

        # --- Scrollable Chat Area ---
        self.scrollable_area = ScrollableMessageArea(parent, db_manager=None)
        self.scrollable_area.grid(row=1, column=10, sticky="nsew")

        # --- Bottom Input Bar ---
        input_frame = tk.Frame(parent, bg="lightgray", padx=10, pady=10)
        input_frame.grid(row=2, column=10, sticky="ew")

        input_frame.grid_columnconfigure(0, weight=1)

        self.description_entry = tk.Entry(input_frame, font=("Arial", 12))
        self.description_entry.grid(row=0, column=10, sticky="ew", padx=(0, 10))

        send_button = tk.Button(input_frame, text="Send", command=self.send_message_to_model)
        send_button.grid(row=0, column=11)

        # get current project
        try:
            self.project = parent.project_dictionary
            print(parent.project_dictionary)
        except:
            print("Maybe it is not a project but it is main chat, just in case the context is now set to GLOBAL")
            self.project = None

    def send_message_to_model(self):
        print("implement send message to model")
        text = self.description_entry.get().strip()
        if text:

            self.scrollable_area.add_message(text, message_id=0, assigned_project="")
            self.description_entry.delete(0, tk.END)
