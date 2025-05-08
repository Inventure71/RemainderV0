import base64
import os
import sys
from google import genai
from google.genai import types
import json as _json

from Utils.prompts import sys_prompt_answer_question, sys_prompt_create_projects, sys_prompt_select_projects, sys_prompt_select_messages


class ModelClient:
    def __init__(self, mode="gemini", model="gemini-2.5-flash-preview-04-17", model_context_window=500000):
        self.mode = mode
        self.model = model
        self.model_context_window = model_context_window

        if mode == "gemini":
            # Determine base path for data files
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                # Running in a PyInstaller bundle
                base_path = sys._MEIPASS
            else:
                # Running in a normal Python environment
                # Assuming model_handler.py is in Utils/ and API_keys is at the project root
                base_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

            api_key_path = os.path.join(base_path, "API_keys", "gemini_api_key.json")

            # load key from json file
            with open(api_key_path, "rb") as f:
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

    def handle_length(self, prompt, messages="", overlap_words=50):
        """
        Ensure that the combined size of `messages` + `prompt` never exceeds
        85 % of the model context window. When it does, split `messages` into
        successive chunks with overlap.
        Returns a list of (messages_chunk, prompt) pairs.
        """
        # Hard limit per request (85 % of the full context window)
        max_ctx = int(self.model_context_window * 0.85)

        prompt_tokens = self._count_tokens(prompt)

        if prompt_tokens >= max_ctx:
            raise ValueError(
                f"Prompt alone occupies {prompt_tokens} tokens, which exceeds "
                f"the 85 % context-window budget of {max_ctx} tokens."
            )

        words = messages.split()
        total_message_words = len(words)
        # Estimate token budget per chunk based on *average* word count per chunk needed
        # This is rough, as prompt is constant but word count varies.
        num_chunks_needed = (self._count_tokens(messages) + prompt_tokens + max_ctx -1) // max_ctx # Ceiling division
        
        if num_chunks_needed <= 1:
            # No splitting needed, return the original message
             if prompt_tokens + self._count_tokens(messages) <= max_ctx:
                  return [(messages, prompt)]
             else:
                  # This case should ideally not happen if prompt_tokens < max_ctx, but as safeguard:
                  print("Warning: Message likely too large even for a single chunk. Truncating.")
                  token_budget = max_ctx - prompt_tokens
                  truncated_message = " ".join(words[:token_budget]) # Simple truncation by word count
                  return [(truncated_message, prompt)]

        # Calculate token budget per chunk, accounting for overlap slightly
        # Reduce budget slightly to make room for potential overlap additions
        # This is still an approximation.
        token_budget = max_ctx - prompt_tokens - overlap_words 
        if token_budget <= 0:
             raise ValueError("Prompt and overlap requirement exceed context limit.")

        chunks_data = [] # Store tuples of (start_word_index, end_word_index)
        current_word_index = 0
        last_chunk_end_index = 0

        while current_word_index < total_message_words:
            start_index = current_word_index
            # Estimate end index based on token budget
            # This is approximate because we count words not exact tokens
            estimated_end_index = min(start_index + token_budget, total_message_words)
            
            # Refine end index by actually counting tokens (if a precise tokenizer were available)
            # For now, we stick to the word count approximation
            actual_end_index = estimated_end_index 
            
            # Ensure we don't create empty chunks
            if start_index >= actual_end_index:
                # This might happen if token budget is extremely small; advance minimally
                 actual_end_index = min(start_index + 1, total_message_words)
            
            chunks_data.append((start_index, actual_end_index))
            last_chunk_end_index = actual_end_index
            current_word_index = actual_end_index
            
            # Break if we somehow overshoot (safety)
            if current_word_index >= total_message_words: 
                break

        # Construct final chunks with overlap
        final_chunks = []
        for i, (start, end) in enumerate(chunks_data):
            actual_start = start
            if i > 0 and overlap_words > 0:
                # Prepend overlap from the *previous* chunk's original words
                prev_chunk_start, prev_chunk_end = chunks_data[i-1]
                overlap_start_index = max(prev_chunk_start, prev_chunk_end - overlap_words)
                # Use words from the original list to get overlap
                overlap_words_list = words[overlap_start_index:prev_chunk_end]
                current_chunk_words = words[start:end]
                chunk_text = " ".join(overlap_words_list + current_chunk_words)
                # Recalculate tokens and truncate if overlap made it too long
                current_tokens = self._count_tokens(chunk_text)
                if prompt_tokens + current_tokens > max_ctx:
                    excess_tokens = (prompt_tokens + current_tokens) - max_ctx
                    # Truncate from the *end* of the combined chunk words
                    combined_words = overlap_words_list + current_chunk_words
                    chunk_text = " ".join(combined_words[:-excess_tokens]) # Remove words from end
            else:
                # First chunk or no overlap
                chunk_text = " ".join(words[start:end])

            final_chunks.append((chunk_text, prompt))

        return final_chunks

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

        conversation_history.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            )
        )

        # Append the prompt
        history.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=f"{prompt}\nContext:\n{messages}"),
                ],
            )
        )

        print("Generating content with prompt:", prompt)
        print("json used", json)
        print("using history", history)

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
                                required=["id", "first_words", "explanation"],
                                properties={
                                    "id": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                        description="The ID of the message (can be string or int-as-string)."
                                    ),
                                    "first_words": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                        description="The first few (up to 5) words of the message content."
                                    ),
                                    "explanation": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                        description="Brief justification for why this message is relevant."
                                    ),
                                },
                            ),
                        ),
                    },
                    required=["messages"]
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
                                properties={
                                    "id": genai.types.Schema(
                                        type=genai.types.Type.INTEGER,
                                        description="The ID of the message being processed."
                                    ),
                                    "project": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                        description="The project name to assign the message to, or empty string if none."
                                    ),
                                    "why": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                        description="Brief justification for project assignment (max 10 words)."
                                    ),
                                    "when": genai.types.Schema(
                                        type=genai.types.Type.STRING,
                                        description="Reminder time in YYYY-MM-DD-HH:MM format, if applicable."
                                    ),
                                    "importance": genai.types.Schema(
                                        type=genai.types.Type.STRING, # Keep as string for flexibility, parse later if needed
                                        description="Importance score (1-10) or 0/omit if not a reminder."
                                    ),
                                    "reoccurence": genai.types.Schema(
                                        type=genai.types.Type.OBJECT,
                                        description="Optional. JSON object describing recurrence rule.",
                                        properties={
                                            "type": genai.types.Schema(type=genai.types.Type.STRING, description="'daily' or 'weekly'", enum=["daily", "weekly"]),
                                            "days": genai.types.Schema(type=genai.types.Type.ARRAY, items=genai.types.Schema(type=genai.types.Type.INTEGER), description="Array of day numbers (1-7) for weekly recurrence.")
                                        },
                                        required=["type"] # Type is required if reoccurence object exists
                                    )
                                },
                                required=["id"] # Only ID is strictly required in the response item
                            ),
                        ),
                    },
                    required=["messages"] # The top-level 'messages' array is required
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
            print("using prompt answering")
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
            contents=history,
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

    def select_messages(self, user_text, project=None, use_history=False, history=None, context_string=None):
        """
        Implements the logic for selecting related messages to a user query, as in the original widget_model_chat.py.
        Returns (response, history)
        """
        # If a pre-built context string is provided (including image descriptions), use it
        if context_string:
            print(f"Using provided context string with length {len(context_string)}")
            cleared_messages_str = context_string
        else:
            # Legacy code path - build a simple context string without image descriptions
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
            print("WARNING: Using legacy context builder without image descriptions")
        
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
        Includes message timestamps and current time in the prompt.
        """
        from datetime import datetime
        # Format messages to include timestamps
        cleared_messages_str_list = []
        for msg in batch:
            # Basic check for timestamp existence and format
            ts_str = msg.get('timestamp', 'Unknown Timestamp')
            try:
                # Attempt to parse for potential re-formatting or just keep original
                # parsed_ts = datetime.fromisoformat(ts_str)
                # formatted_ts = parsed_ts.strftime("%Y-%m-%d %H:%M") # Example format
                formatted_ts = ts_str # Keep original for now
            except (ValueError, TypeError):
                formatted_ts = ts_str # Keep original if parsing fails
            cleared_messages_str_list.append(f"ID: {msg['id']}, Timestamp: {formatted_ts}, Content: {msg['content']}")
        
        cleared_messages_str = "\n".join(cleared_messages_str_list)
        
        # Get current time
        current_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Add current time and instructions about timestamps to the prompt
        prompt = f"Current Time: {current_time_str}\n\nPROJECTS CONTEXT:\n{projects_prompt}\n\nMESSAGES TO PROCESS (max {len(batch)}):\n(Note: Use the message timestamp and current time to determine reminder dates accurately, especially relative ones like 'tomorrow'. Default reminder time is 23:00 of the message's day if unspecified.)\n{cleared_messages_str}"
        
        print("Processing messages with prompt including timestamps and current time:")
        # print(prompt) # Uncomment for debugging the full prompt
        print(cleared_messages_str)
        
        # Pass the modified prompt and the original message string (or the timestamped one?) to generate.
        # The `messages` argument in generate is primarily for length calculation/splitting. 
        # The full context including timestamps is now in the `prompt` argument.
        # Let's pass the timestamped string to `messages` as well for consistency in splitting.
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
                resp_item = response_by_id[msg_id_str]
                new_project = resp_item.get("project", None)
                remind = resp_item.get("when", None)
                importance = resp_item.get("importance", None)
                reoccurence_data = resp_item.get("reoccurence", None)
                reoccurence_json = _json.dumps(reoccurence_data) if reoccurence_data else None

                print(f"Message ID: {msg_id_str}, Project: {new_project}, Reminder: {remind}, Importance: {importance}, Reoccurence: {reoccurence_json}")
                message_db.update_message(msg["id"], processed=True, project=new_project, remind=remind, importance=importance, reoccurences=reoccurence_json)
            else:
                print(f"Message ID: {msg_id_str} not processed by model, marking done.")
                message_db.update_message(msg["id"], processed=True)

if __name__ == "__main__":
    None