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
        # Split into (messages_chunk, prompt) pairs
        pairs = self.handle_length(prompt, messages)

        if json > 0:
            if json == 3:  # Project creation
                combined_projects = []
                for msg_chunk, prmpt in pairs:
                    if self.mode == "gemini":
                        resp_text, history = self.generate_with_gemini(prmpt, msg_chunk, json=json, history=None)
                    else:
                        print("Implement mode", self.mode)
                        raise ValueError("Invalid mode")

                    data = _json.loads(resp_text)
                    combined_projects.extend(data.get("projects", []))
                combined = {"projects": combined_projects}
                return _json.dumps(combined), history
            else:  # Other JSON responses (messages)
                combined_messages = []
                for msg_chunk, prmpt in pairs:
                    if self.mode == "gemini":
                        resp_text, history = self.generate_with_gemini(prmpt, msg_chunk, json=json, history=None)
                    else:
                        print("Implement mode", self.mode)
                        raise ValueError("Invalid mode")

                    data = _json.loads(resp_text)
                    combined_messages.extend(data.get("messages", []))
                combined = {"messages": combined_messages}
                return _json.dumps(combined), history
        pairs = self.handle_length(prompt, messages)

        if json > 0:
            if json == 3:  # Project creation
                combined_projects = []
                for msg_chunk, prmpt in pairs:
                    if self.mode == "gemini":
                        resp_text, history = self.generate_with_gemini(prmpt, msg_chunk, json=json, history=None)
                    else:
                        print("Implement mode", self.mode)
                        raise ValueError("Invalid mode")

                    data = _json.loads(resp_text)
                    combined_projects.extend(data.get("projects", []))
                combined = {"projects": combined_projects}
                return _json.dumps(combined), history
            else:  # Other JSON responses (messages)
                combined_messages = []
                for msg_chunk, prmpt in pairs:
                    if self.mode == "gemini":
                        resp_text, history = self.generate_with_gemini(prmpt, msg_chunk, json=json, history=None)
                    else:
                        print("Implement mode", self.mode)
                        raise ValueError("Invalid mode")

                    data = _json.loads(resp_text)
                    combined_messages.extend(data.get("messages", []))
                combined = {"messages": combined_messages}
                return _json.dumps(combined), history
        else:
            responses = []
            for idx, (msg_chunk, prmpt) in enumerate(pairs, start=1):
                if self.mode == "gemini":
                    resp_text, history = self.generate_with_gemini(prmpt, msg_chunk, json=0, history=None)

                else:
                    print("Implement mode", self.mode)
                    raise ValueError("Invalid mode")

                if len(pairs) > 1:
                    responses.append(f"--- Response {idx} ---\n{resp_text}")
                else:
                    responses.append(resp_text)
            combined_text = "\n\n".join(responses)
            return combined_text, history

    def generate_with_gemini(self, prompt, messages, json=0, history=None):
        if history is None:
            history = []

        # Inject message chunk into history before the prompt
        if messages:
            history.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=messages),
                    ],
                )
            )

        # Append the prompt
        history.append(
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
            contents=history,
            config=generate_content_config,
        ).text

        # add response to history
        history.append(
            types.Content(
                role="model",
                parts=[
                    types.Part.from_text(text=response),
                ],
            ),
        )

        return response, history

if __name__ == "__main__":
    None