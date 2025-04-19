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
        self.history = None

        # --- Top Button Bar ---
        top_button_frame = tk.Frame(parent, bg="lightgray", padx=10, pady=5)
        top_button_frame.grid(row=0, column=10, sticky="ew")
        process_all_button = tk.Button(top_button_frame, text="Process Messages", command=self.process_all_main_chat_messages)
        process_all_button.pack(side="left", padx=5)

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
        self.select_messages_toggle_var = tk.BooleanVar(value=False)
        toggle1_button = tk.Checkbutton(
            input_frame,
            text="Select Message",
            variable=self.select_messages_toggle_var,
            onvalue=True,
            offvalue=False
        )
        toggle1_button.grid(row=0, column=12, padx=(10, 0))

        self.use_history_toggle_var = tk.BooleanVar(value=False)
        toggle2_button = tk.Checkbutton(
            input_frame,
            text="Use history",
            variable=self.use_history_toggle_var,
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

            if self.use_history_toggle_var.get():
                history = self.history
            else:
                history = None

            if self.select_messages_toggle_var.get():
                print("Trying to select messages", f"Using history: {self.use_history_toggle_var.get()}")
                response, self.history = self.model_handler.generate(prompt=user_text, messages=cleared_messages_str,
                                                                     json=1, history=history)
                print(response)

                #self.scrollable_area.add_message(response, message_id=0, assigned_project="")

                # Extract message IDs from the response
                try:
                    import json
                    response_data = json.loads(response)

                    if "messages" in response_data:
                        # Process each mentioned message
                        for mentioned_msg in response_data["messages"]:
                            if "id" in mentioned_msg:
                                msg_id = mentioned_msg["id"]
                                reason = mentioned_msg.get("why", "No reason provided")

                                # Find the full message that matches the ID
                                matching_messages = [msg for msg in messages if msg["id"] == msg_id]

                                if matching_messages:
                                    message = matching_messages[0]
                                    # Add each mentioned message to the chat widget with the reason, clickable
                                    def jump_to_main_chat(mid=msg_id):
                                        try:
                                            if hasattr(self.parent, 'scrollable_area'):
                                                self.parent.scrollable_area.jump_to_message(mid)
                                        except Exception as e:
                                            print(f"Jump to message failed: {e}")
                                    self.scrollable_area.add_message(
                                        f"{message['content']}\n\nReason: {reason}\nReferenced message N{msg_id}",
                                        message_id=msg_id,
                                        assigned_project=message.get('project', ""),
                                        alignment="left",
                                        on_click=jump_to_main_chat
                                    )
                except Exception as e:
                    print(f"Error parsing response or extracting messages: {e}")


            else:
                print("Generic message", f"Using history: {self.use_history_toggle_var.get()}")
                response, self.history = self.model_handler.generate(prompt=user_text, messages=cleared_messages_str, history=history)
                self.scrollable_area.add_message(response, message_id=0, assigned_project="")

            self.description_entry.delete(0, tk.END)


        else:
            print("No text in text field")

    def process_all_main_chat_messages(self):
        # Get all unprocessed messages from main chat (project=None)
        unprocessed = self.message_db.get_project_messages(project_name=None, only_unprocessed=True)
        
        cleared_messages_str = ""
        for msg in unprocessed:
            if msg['project'] == "" or msg['project'] == None:
                cleared_messages_str += f"ID: {msg['id']}, Content: {msg['content']}\n"
                self.message_db.update_message(msg["id"], processed=True)
            else: 
                print("Skipping project message", msg['project'])

        response, self.history = self.model_handler.generate(prompt="", messages=cleared_messages_str, json=2, history=None)
        print(response)

        # Optionally, refresh the main chat window if needed
        if hasattr(self.parent, 'refresh'):
            self.parent.refresh()