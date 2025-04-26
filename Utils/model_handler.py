import base64
import os
from google import genai
from google.genai import types
import json as _json

from Utils.prompts import sys_prompt_answer_question, sys_prompt_create_projects, sys_prompt_select_projects, sys_prompt_select_messages


class ModelClient:
    def __init__(self, mode="gemini", model="gemini-2.5-flash-preview-04-17", model_context_window=100000):
        self.mode = mode
        self.model = model
        self.model_context_window = model_context_window

        if mode == "gemini":
            # load key from json file
            with open("API_keys/gemini_api_key.json", "rb") as f:
                self.api_key = f.read().decode("utf-8")

            self.gemini_client = genai.Client(
                api_key=self.api_key,
            )
        else:
            print("Implement mode", mode)

    def _count_tokens(self, text: str) -> int:
        """
        Rough token estimation. One whitespace‑separated word is treated as one
        token. Replace with the official Gemini tokenizer if/when it is
        exposed by the SDK.
        """
        return len(text.split())

    def handle_length(self, prompt, messages=""):
        """
        Ensure that the combined size of `messages` + `prompt` never exceeds
        85 % of the model context window.  When it does, split `messages` into
        successive chunks so that each chunk, together with `prompt`, stays
        within the limit.

        Returns
        -------
        list[tuple[str, str]]
            A list of (messages_chunk, prompt) pairs ready to be fed to the
            model one after another.
        """
        # Hard limit per request (85 % of the full context window)
        max_ctx = int(self.model_context_window * 0.85)

        prompt_tokens = self._count_tokens(prompt)

        if prompt_tokens >= max_ctx:
            raise ValueError(
                f"Prompt alone occupies {prompt_tokens} tokens, which exceeds "
                f"the 85 % context‑window budget of {max_ctx} tokens."
            )

        total_tokens = prompt_tokens + self._count_tokens(messages)
        # Fast path: everything fits.
        if total_tokens <= max_ctx:
            return [(messages, prompt)]

        # We need to split `messages`.
        token_budget = max_ctx - prompt_tokens
        words = messages.split()
        chunks = []
        current_words = []
        current_tokens = 0

        for word in words:
            current_tokens += 1  # naïve 1‑to‑1 mapping word→token
            if current_tokens > token_budget:
                # Close off the current chunk and start a new one.
                chunks.append(" ".join(current_words))
                current_words = [word]
                current_tokens = 1
            else:
                current_words.append(word)

        if current_words:  # add the final chunk
            chunks.append(" ".join(current_words))

        # Return list of (messages_chunk, prompt) pairs
        return [(chunk, prompt) for chunk in chunks]

    def generate(self, prompt, messages="", json=0, history=None):
        """
        Generate content, automatically splitting messages+prompt if needed.
        Combines multiple chunk responses into one output.
        """
        pairs = self.handle_length(prompt, messages)

        def make_serializable(obj):
            # Recursively convert Content or other custom objects to dicts
            if hasattr(obj, "to_dict"):
                return obj.to_dict()
            elif hasattr(obj, "__dict__"):
                return {k: make_serializable(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
            elif isinstance(obj, list):
                return [make_serializable(i) for i in obj]
            elif isinstance(obj, dict):
                return {k: make_serializable(v) for k, v in obj.items()}
            else:
                return obj

        if json > 0:
            if json == 3:  # Project creation
                combined_projects = []
                all_history = []
                current_history = history
                for msg_chunk, prmpt in pairs:
                    if self.mode == "gemini":
                        resp_text, new_history = self.generate_with_gemini(prmpt, msg_chunk, json=json, history=current_history)
                        # Update history for next chunk if needed
                        if len(pairs) > 1:
                            current_history = new_history
                    else:
                        print("Implement mode", self.mode)
                        raise ValueError("Invalid mode")

                    data = _json.loads(resp_text)
                    combined_projects.extend(data.get("projects", []))
                    if new_history:
                        all_history = make_serializable(new_history)
                combined = {"projects": combined_projects}
                return _json.dumps(combined), all_history
            else:  # Other JSON responses (messages)
                combined_messages = []
                all_history = []
                current_history = history
                for msg_chunk, prmpt in pairs:
                    if self.mode == "gemini":
                        resp_text, new_history = self.generate_with_gemini(prmpt, msg_chunk, json=json, history=current_history)
                        # Update history for next chunk if needed
                        if len(pairs) > 1:
                            current_history = new_history
                    else:
                        print("Implement mode", self.mode)
                        raise ValueError("Invalid mode")

                    data = _json.loads(resp_text)
                    combined_messages.extend(data.get("messages", []))
                    if new_history:
                        all_history = make_serializable(new_history)
                combined = {"messages": combined_messages}
                return _json.dumps(combined), all_history
        else:
            responses = []
            all_history = []
            current_history = history
            for idx, (msg_chunk, prmpt) in enumerate(pairs, start=1):
                if self.mode == "gemini":
                    resp_text, new_history = self.generate_with_gemini(prmpt, msg_chunk, json=0, history=current_history)
                    # Update history for next chunk if needed
                    if len(pairs) > 1:
                        current_history = new_history
                else:
                    print("Implement mode", self.mode)
                    raise ValueError("Invalid mode")

                if len(pairs) > 1:
                    responses.append(f"--- Response {idx} ---\n{resp_text}")
                else:
                    responses.append(resp_text)
                if new_history:
                    all_history = make_serializable(new_history)
            combined_text = "\n\n".join(responses)
            return combined_text, all_history

    def generate_with_gemini(self, prompt, messages, json=0, history=None):
        # Initialize history if not provided
        if history is None:
            history = []
        
        # Create a new history list for this conversation
        conversation_history = []
        
        # If we have a history from previous interactions, add it to our conversation history
        # This should only include the actual user-model conversation, not the context messages
        if history and isinstance(history, list):
            conversation_history.extend(history)
        
        # Inject message chunk (context messages) into history before the prompt
        # This is only added for this specific request, not saved in the conversation history
        if messages:
            conversation_history.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=messages),
                    ],
                )
            )

        # Append the prompt
        conversation_history.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            )
        )

        print("Generating content with prompt:", prompt)

        # find messages
        if json == 1:
            generate_content_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    properties={
                        "messages": genai.types.Schema(
                            type=genai.types.Type.ARRAY,
                            items=genai.types.Schema(
                                type=genai.types.Type.OBJECT,
                                required=["id", "why"],
                                properties={
                                    "id": genai.types.Schema(
                                        type=genai.types.Type.INTEGER,
                                    ),
                                    "content": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                    ),
                                    "why": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                    ),
                                },
                            ),
                        ),
                    },
                ),
                system_instruction=[
                    types.Part.from_text(
                        text=sys_prompt_select_messages),
                ],
            )

        # assign messages to projects
        elif json == 2:
            generate_content_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    properties={
                        "messages": genai.types.Schema(
                            type=genai.types.Type.ARRAY,
                            items=genai.types.Schema(
                                type=genai.types.Type.OBJECT,
                                required=["id", "project", "why"],
                                properties={
                                    "id": genai.types.Schema(
                                        type=genai.types.Type.INTEGER,
                                    ),
                                    "project": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                    ),
                                    "why": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                    ),
                                    "when": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                    ),
                                    "importance": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                    ),
                                },
                            ),
                        ),
                    },
                ),
                system_instruction=[
                    types.Part.from_text(
                        text=sys_prompt_select_projects),
                ],
            )
        
        # create new projects
        elif json == 3:
            print("Creating new projects")
            generate_content_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    properties={
                        "projects": genai.types.Schema(
                            type=genai.types.Type.ARRAY,
                            items=genai.types.Schema(
                                type=genai.types.Type.OBJECT,
                                required=["name", "description"],
                                properties={
                                    "name": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                    ),
                                    "description": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                    ),
                                },
                            ),
                        ),
                    },
                ),
                system_instruction=[
                    types.Part.from_text(
                        text=sys_prompt_create_projects),
                ],
            )

        
        else:
            generate_content_config = types.GenerateContentConfig(
                response_mime_type="text/plain",
                system_instruction=[
                    types.Part.from_text(
                        text=sys_prompt_answer_question),
                ],
            )

        # prompt model
        response = self.gemini_client.models.generate_content(
            model=self.model,
            contents=conversation_history,
            config=generate_content_config,
        ).text

        # add response to history
        conversation_history.append(
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(text=response),
                ],
            ),
        )

        return response, conversation_history

    def select_messages(self, user_text, project=None, use_history=False, history=None):
        """
        Implements the logic for selecting related messages to a user query, as in the original widget_model_chat.py.
        Returns (response, history)
        """
        from DatabaseUtils.database_messages import MessageDatabaseHandler
        message_db = MessageDatabaseHandler()
        if project is not None:
            messages = message_db.get_project_messages(project)
        else:
            messages = message_db.get_project_messages(None)
        cleared_messages = []
        cleared_messages_str = ""
        for message in messages:
            cleared_messages.append({"id": message["id"], "content": message["content"], "project": message["project"]})
            cleared_messages_str += f"ID: {message['id']}, Content: {message['content']}, Project: {message['project']}\n"
        if use_history:
            hist = history
        else:
            hist = None
        response, new_history = self.generate(prompt=user_text, messages=cleared_messages_str, json=1, history=hist)
        return response, new_history

    def generic_chat(self, user_text, project=None, use_history=False, history=None):
        """
        Implements the generic chat logic (Gemini model, not select messages mode), as in widget_model_chat.py.
        Returns (response, history)
        """
        from DatabaseUtils.database_messages import MessageDatabaseHandler
        message_db = MessageDatabaseHandler()
        if project is not None:
            messages = message_db.get_project_messages(project)
        else:
            messages = message_db.get_project_messages(None)
        cleared_messages_str = ""
        for message in messages:
            cleared_messages_str += f"ID: {message['id']}, Content: {message['content']}, Project: {message['project']}\n"
        if use_history:
            hist = history
        else:
            hist = None
        response, new_history = self.generate(prompt=user_text, messages=cleared_messages_str, history=hist)
        return response, new_history

    def process_all_main_chat_messages(self, check_for_new_projects=False, max_batch_size=20):
        """
        Processes all unprocessed messages in the main chat, optionally first checking for new projects.
        Implements the logic from widget_model_chat.py's process_all_main_chat_messages.
        """
        from DatabaseUtils.database_messages import MessageDatabaseHandler
        from DatabaseUtils.database_projects import ProjectsDatabaseHandler
        from datetime import datetime
        message_db = MessageDatabaseHandler()
        projects_db = ProjectsDatabaseHandler()
        if check_for_new_projects:
            self.check_for_new_projects(message_db, projects_db)
        unprocessed = message_db.get_project_messages(project_name=None, only_unprocessed=True)
        if not unprocessed:
            print("No unprocessed messages found.")
            return
        projects = projects_db.get_all_projects()
        project_contexts = []
        for project in projects:
            project_name = project['name']
            project_desc = project.get('description', '')
            messages = message_db.get_project_messages(project_name=project_name)
            first_5 = messages[:5]
            first_5_str = "\n".join([f"{m['content']}" for m in first_5])
            project_contexts.append(f"Project: {project_name}\nDescription: {project_desc}\nFirst 5 Messages Of Project:\n{first_5_str}")
        projects_prompt = "\n\n".join(project_contexts)
        batch = []
        batch_count = 0
        for msg in unprocessed:
            if msg['project'] == "" or msg['project'] is None:
                batch.append(msg)
                if len(batch) == max_batch_size:
                    self._process_message_batch(batch, projects_prompt, message_db)
                    batch_count += 1
                    batch = []
        if batch:
            self._process_message_batch(batch, projects_prompt, message_db)
            batch_count += 1
        print(f"Processed {batch_count} batches of messages.")

    def check_for_new_projects(self, message_db, projects_db):
        """
        Checks for new projects based on unassigned messages, as in widget_model_chat.py.
        """
        from datetime import datetime
        unprocessed = message_db.get_project_messages(project_name=None, only_unprocessed=True)
        if not unprocessed:
            print("No unprocessed messages for project check.")
            return
        projects = projects_db.get_all_projects()
        project_contexts = []
        for project in projects:
            project_name = project['name']
            project_desc = project.get('description', '')
            messages = message_db.get_project_messages(project_name=project_name)
            first_5 = messages[:5]
            first_5_str = "\n".join([f"{m['content']}" for m in first_5])
            project_contexts.append(f"Project: {project_name}\nDescription: {project_desc}\nFirst 5 Messages Of Project:\n{first_5_str}")
        projects_prompt = "\n\n".join(project_contexts)
        cleared_messages_str = "\n".join([f"ID: {msg['id']}, Content: {msg['content']}" for msg in unprocessed if msg['project'] == "" or msg['project'] is None])
        prompt = f"Already existing projects and some messages in them:\n{projects_prompt}\n\nMessages with no project yet:\n{cleared_messages_str}"
        print("Checking for new projects with prompt:", prompt)
        response, _ = self.generate(prompt=prompt, messages=cleared_messages_str, json=3, history=None)
        print("Project check response:", response)
        try:
            import json
            response_data = json.loads(response)
            if "projects" in response_data:
                for project in response_data["projects"]:
                    if "name" in project and "description" in project:
                        projects_db.add_project(project["name"], datetime.now(), project["description"], user_created=0)
        except Exception as e:
            print(f"Error parsing response or creating new projects: {e}")

    def _process_message_batch(self, batch, projects_prompt, message_db):
        """
        Processes a batch of messages, assigning them to projects and extracting reminders, as in widget_model_chat.py.
        """
        cleared_messages_str = "\n".join([f"ID: {msg['id']}, Content: {msg['content']}" for msg in batch])
        prompt = f"PROJECTS CONTEXT:\n{projects_prompt}\n\nMESSAGES TO PROCESS (max {len(batch)}):\n{cleared_messages_str}"
        print("Processing messages:", cleared_messages_str)
        response, _ = self.generate(prompt=prompt, messages=cleared_messages_str, json=2, history=None)
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
                new_project = response_by_id[msg_id_str].get("project", None)
                remind = response_by_id[msg_id_str].get("when", None)
                importance = response_by_id[msg_id_str].get("importance", None)
                print(f"Message with ID: {msg_id_str}, was added to project: {new_project} is a reminder: {remind} {importance}")
                message_db.update_message(msg["id"], processed=True, project=new_project, remind=remind, importance=importance)
            else:
                message_db.update_message(msg["id"], processed=True)

if __name__ == "__main__":
    None