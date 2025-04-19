import tkinter as tk

from UI.components.scrollable_messages_box import ScrollableMessageArea
from DatabaseUtils.database_messages import MessageDatabaseHandler
from Utils.model_handler import ModelClient

class WidgetModelChat:
    def __init__(self, parent):
        self.parent = parent
        self.project = None
        self.message_db = MessageDatabaseHandler()
        self.model_handler = ModelClient(mode="gemini", model_context_window=500000)

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
        # Toggle Buttons
        self.toggle1_var = tk.BooleanVar(value=False)
        toggle1_button = tk.Checkbutton(
            input_frame,
            text="Toggle 1",
            variable=self.toggle1_var,
            onvalue=True,
            offvalue=False
        )
        toggle1_button.grid(row=0, column=12, padx=(10, 0))

        self.toggle2_var = tk.BooleanVar(value=False)
        toggle2_button = tk.Checkbutton(
            input_frame,
            text="Toggle 2",
            variable=self.toggle2_var,
            onvalue=True,
            offvalue=False
        )
        toggle2_button.grid(row=0, column=13, padx=(10, 0))

    def send_message_to_model(self):
        user_text = self.description_entry.get().strip()

        if user_text:
            # get current project for context
            try:
                self.project = self.parent.project_dictionary["name"]
                print(self.project)

                self.scrollable_area.add_message(f"{user_text} ({self.project} Context)", message_id=99999999, assigned_project="", alignment="right")

            except:
                print("Maybe it is not a project but it is main chat, just in case the context is now set to GLOBAL")
                self.project = None
                self.scrollable_area.add_message(f"{user_text} (Global Context)", message_id=99999999, assigned_project="", alignment="right")


            messages = self.message_db.get_project_messages(
                self.project)

            cleared_messages = []
            cleared_messages_str = ""
            for message in messages:
                # only save the content and project of each message
                cleared_messages.append({"id": message["id"], "content": message["content"], "project": message["project"]})
                cleared_messages_str += f"ID: {message['id']}, Content: {message['content']}, Project: {message['project']}\n"


            print(cleared_messages_str)

            print("implement send message to model")

            response = self.model_handler.generate(prompt=user_text, messages=cleared_messages_str)
            self.scrollable_area.add_message(response, message_id=0, assigned_project="")
            self.description_entry.delete(0, tk.END)


        else:
            print("No text in text field")