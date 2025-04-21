import re
import tkinter as tk
import time
from datetime import datetime

from UI.components.scrollable_messages_box import ScrollableMessageArea
from DatabaseUtils.database_messages import MessageDatabaseHandler
from DatabaseUtils.database_projects import ProjectsDatabaseHandler
from Utils.model_handler import ModelClient

class WidgetModelChat:
    def __init__(self, parent):
        self.parent = parent
        self.project = None
        self.projects_db = ProjectsDatabaseHandler()
        self.message_db = MessageDatabaseHandler()
        self.model_handler = ModelClient(mode="gemini", model_context_window=500000)
        self.history = None

        self.max_batch_size = 20  # You can make this configurable

        # --- Top Button Bar ---
        top_button_frame = tk.Frame(parent, bg="lightgray", padx=10, pady=5)
        top_button_frame.grid(row=0, column=10, sticky="ew")
        process_all_button = tk.Button(top_button_frame, text="Process Messages", command=self.process_all_main_chat_messages)
        process_all_button.pack(side="left", padx=5)

        self.check_projects_toggle_var = tk.BooleanVar(value=False)
        check_projects_toggle = tk.Checkbutton(
            top_button_frame,
            text="Check New Projects",
            variable=self.check_projects_toggle_var,
            onvalue=True,
            offvalue=False
        )
        check_projects_toggle.pack(side="left", padx=5)

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
        # If the check_projects toggle is on, run the model with json=3 to check for new projects first
        if self.check_projects_toggle_var.get():
            self._check_for_new_projects()
        
        # Proceed as before
        # Get all unprocessed messages from main chat (project=None)
        unprocessed = self.message_db.get_project_messages(project_name=None, only_unprocessed=True)
        if not unprocessed:
            print("No unprocessed messages found.")
            return
        projects = self.projects_db.get_all_projects()
        project_contexts = []
        for project in projects:
            project_name = project['name']
            project_desc = project.get('description', '')
            messages = self.message_db.get_project_messages(project_name=project_name)
            first_5 = messages[:5]
            first_5_str = "\n".join([f"{m['content']}" for m in first_5])
            project_contexts.append(f"Project: {project_name}\nDescription: {project_desc}\nFirst 5 Messages Of Project:\n{first_5_str}")
        projects_prompt = "\n\n".join(project_contexts)
        batch = []
        batch_count = 0
        for msg in unprocessed:
            if msg['project'] == "" or msg['project'] is None:
                batch.append(msg)
                if len(batch) == self.max_batch_size:
                    self._process_message_batch(batch, projects_prompt)
                    batch_count += 1
                    batch = []
        if batch:
            self._process_message_batch(batch, projects_prompt)
            batch_count += 1
        print(f"Processed {batch_count} batches of messages.")
        if hasattr(self.parent, 'refresh'):
            self.parent.refresh()

    def _check_for_new_projects(self):
        # Gather all main chat unprocessed messages
        unprocessed = self.message_db.get_project_messages(project_name=None, only_unprocessed=True)
        if not unprocessed:
            print("No unprocessed messages for project check.")
            return
        projects = self.projects_db.get_all_projects()
        project_contexts = []
        for project in projects:
            project_name = project['name']
            project_desc = project.get('description', '')
            messages = self.message_db.get_project_messages(project_name=project_name)
            first_5 = messages[:5]
            first_5_str = "\n".join([f"{m['content']}" for m in first_5])
            project_contexts.append(f"Project: {project_name}\nDescription: {project_desc}\nFirst 5 Messages Of Project:\n{first_5_str}")
        projects_prompt = "\n\n".join(project_contexts)
        cleared_messages_str = "\n".join([f"ID: {msg['id']}, Content: {msg['content']}" for msg in unprocessed if msg['project'] == "" or msg['project'] is None])
        prompt = f"Already existing projects and some messages in them:\n{projects_prompt}\n\nMessages with no project yet:\n{cleared_messages_str}"
        print("Checking for new projects with prompt:", prompt)

        response, _ = self.model_handler.generate(prompt=prompt, messages=cleared_messages_str, json=3, history=None)
        print("Project check response:", response)

        # implement json parsing in the answer and creation of new projects
        try:
            import json
            response_data = json.loads(response)
            if "projects" in response_data:
                for project in response_data["projects"]:
                    if "name" in project and "description" in project:
                        self.projects_db.add_project(project["name"], datetime.now(), project["description"], user_created=0)
        except Exception as e:
            print(f"Error parsing response or creating new projects: {e}")

    def _process_message_batch(self, batch, projects_prompt):
        cleared_messages_str = "\n".join([f"ID: {msg['id']}, Content: {msg['content']}" for msg in batch])
        prompt = f"PROJECTS CONTEXT:\n{projects_prompt}\n\nMESSAGES TO PROCESS (max {len(batch)}):\n{cleared_messages_str}"
        print("Processing messages:", cleared_messages_str)
        response, self.history = self.model_handler.generate(prompt=prompt, messages=cleared_messages_str, json=2, history=None)
        print("Response:", response)
        try:
            import json
            response_data = json.loads(response)
            response_messages = response_data.get("messages", [])
            response_by_id = {str(msg.get("id")): msg for msg in response_messages}
        except Exception as e:
            print(f"Error parsing response JSON: {e}")
            response_by_id = {}
        for msg in batch:
            msg_id_str = str(msg["id"])
            if msg_id_str in response_by_id:
                new_project = response_by_id[msg_id_str].get("project", msg.get("project"))
                self.message_db.update_message(msg["id"], processed=True, project=new_project)
            else:
                self.message_db.update_message(msg["id"], processed=True)