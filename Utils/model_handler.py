# pip install -q -U google-genai

import base64
import os
from google import genai
from google.genai import types

from Utils.prompts import sys_prompt_0, sys_prompt_1, sys_prompt_2


class ModelClient:
    def __init__(self, mode="gemini", model="gemini-2.5-flash-preview-04-17"):
        self.mode = mode
        self.model = model

        if mode == "gemini":
            # load key from json file
            with open("API_keys/gemini_api_key.json", "rb") as f:
                self.api_key = f.read().decode("utf-8")

            self.gemini_client = genai.Client(
                api_key=self.api_key,
            )
        else:
            print("Implement mode", mode)


    def generate_with_gemini(self, prompt, json=0, history=None):
        # json 0 == false, 1 is message select mode

        if history is None:
            history = []

        history.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=prompt),
                ],
            )
        )

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
                        text=sys_prompt_1),
                ],
            )
        else:
            generate_content_config = types.GenerateContentConfig(
                response_mime_type="text/plain",
                system_instruction=[
                    types.Part.from_text(
                        text=sys_prompt_0),
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

    def generate(self, prompt, json=False):

        if self.mode == "gemini":
            return self.generate_with_gemini(prompt)
        else:
            print("Implement mode", self.mode)


if __name__ == "__main__":
    generate()
