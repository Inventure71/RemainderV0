import google.generativeai as genai
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class GeminiClient:
    """
    A client class to interact with the Google Gemini API.

    Provides methods to get standard text responses and structured JSON responses.
    """
    def __init__(self, api_key=None, model_name="gemini-1.5-flash-latest"):
        """
        Initializes the GeminiClient.

        Args:
            api_key (str, optional): Your Google API key. If None, it attempts
                                     to read from the 'GOOGLE_API_KEY' environment variable.
                                     Defaults to None.
            model_name (str, optional): The name of the Gemini model to use.
                                        Defaults to "gemini-1.5-flash-latest".

        Raises:
            ValueError: If the API key is not provided and cannot be found in
                        the environment variables.
        """
        if api_key is None:
            api_key = os.getenv("GOOGLE_API_KEY")

        if not api_key:
            raise ValueError("API key not provided. Please set the GOOGLE_API_KEY environment variable or pass the key during initialization.")

        try:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            logging.info(f"GeminiClient initialized with model: {model_name}")
        except Exception as e:
            logging.error(f"Failed to configure Generative AI or initialize model: {e}")
            raise

    def generate_text_response(self, prompt: str) -> str | None:
        """
        Generates a standard text response from the Gemini model.

        Args:
            prompt (str): The input prompt for the model.

        Returns:
            str | None: The generated text response, or None if an error occurs.
        """
        logging.info(f"Generating text response for prompt: '{prompt[:50]}...'")
        try:
            response = self.model.generate_content(prompt)
            # Accessing the text part of the response
            # Check if parts exist and have text
            if response.parts:
                 # Concatenate text from all parts, handling potential non-text parts gracefully
                text_response = "".join(part.text for part in response.parts if hasattr(part, 'text'))
                if not text_response:
                    # Fallback if parts exist but contain no text (e.g., blocked content)
                    logging.warning("Response received but contained no text parts. Check safety ratings or prompt issues.")
                    # You might want to inspect response.prompt_feedback here
                    return f"Received response with no text content. Prompt feedback: {response.prompt_feedback}"
                logging.info("Text response generated successfully.")
                return text_response
            else:
                 # Handle cases where the response might be blocked or empty
                 logging.warning(f"Received an empty or blocked response. Feedback: {response.prompt_feedback}")
                 return f"Received empty or blocked response. Feedback: {response.prompt_feedback}"

        except Exception as e:
            logging.error(f"Error during text generation: {e}")
            # You might want to inspect the specific exception type for more details
            # For example: except genai.types.generation_types.StopCandidateException
            return None

    def generate_json_response(self, prompt: str) -> dict | list | None:
        """
        Generates a response from the Gemini model, instructing it to format
        the output as JSON, and attempts to parse it.

        Note: This relies on the model's ability to follow instructions.
              For more robust JSON output, especially for complex schemas,
              consider exploring Function Calling features if available/applicable.

        Args:
            prompt (str): The input prompt for the model. The method will wrap
                          this prompt with instructions to return JSON.

        Returns:
            dict | list | None: The parsed JSON object (as a Python dict or list),
                                or None if the response wasn't valid JSON or an
                                error occurred.
        """
        json_instruction = (
            "IMPORTANT: Respond ONLY with a valid JSON object or array based on the following request. "
            "Do not include any text, explanation, or markdown formatting before or after the JSON structure. "
            "Your entire response must be parseable by a standard JSON parser.\n\n"
            "Request: "
        )
        full_prompt = json_instruction + prompt
        logging.info(f"Generating JSON response for prompt: '{prompt[:50]}...'")

        try:
            # Using the text generation method first
            response_text = self.generate_text_response(full_prompt)

            if not response_text:
                 logging.error("Failed to get any response from the model for JSON request.")
                 return None

            # Attempt to parse the response text as JSON
            try:
                # Basic cleaning: remove potential markdown code fences
                cleaned_text = response_text.strip().strip('```json').strip('```').strip()
                json_output = json.loads(cleaned_text)
                logging.info("JSON response generated and parsed successfully.")
                return json_output
            except json.JSONDecodeError as json_err:
                logging.error(f"Failed to decode JSON response: {json_err}")
                logging.error(f"Received text was: {response_text}")
                return None # Indicate failure to parse as JSON

        except Exception as e:
            # Catch errors from the underlying generate_text_response call if they weren't handled there
            logging.error(f"An unexpected error occurred during JSON generation: {e}")
            return None

# --- Example Usage ---
if __name__ == "__main__":
    try:
        # Initialize the client (assumes GOOGLE_API_KEY is set in environment)
        client = GeminiClient()

        # --- Example 1: Standard Text Response ---
        print("-" * 20)
        print("Example 1: Standard Text Response")
        text_prompt = "Explain the concept of recursion in programming in simple terms."
        text_response = client.generate_text_response(text_prompt)

        if text_response:
            print("\nPrompt:", text_prompt)
            print("Gemini Response:\n", text_response)
        else:
            print("\nFailed to get a text response.")

        # --- Example 2: JSON Response ---
        print("\n" + "-" * 20)
        print("Example 2: JSON Response")
        json_prompt = "List 3 major cities in Italy and their approximate populations. Format as a JSON array of objects, each object having 'city' and 'population' keys."
        json_response = client.generate_json_response(json_prompt)

        if json_response:
            print("\nPrompt:", json_prompt)
            print("Gemini JSON Response:")
            # Pretty print the JSON
            print(json.dumps(json_response, indent=2))

            # You can now work with the Python object:
            if isinstance(json_response, list) and len(json_response) > 0:
                 print(f"\nFirst city from JSON: {json_response[0].get('city')}")

        else:
            print("\nFailed to get a valid JSON response.")

        # --- Example 3: More complex JSON ---
        print("\n" + "-" * 20)
        print("Example 3: More complex JSON structure")
        json_prompt_2 = "Create a JSON object describing a fictional book with fields: title (string), author (string), year_published (integer), genres (array of strings)."
        json_response_2 = client.generate_json_response(json_prompt_2)

        if json_response_2:
             print("\nPrompt:", json_prompt_2)
             print("Gemini JSON Response:")
             print(json.dumps(json_response_2, indent=2))
        else:
             print("\nFailed to get a valid JSON response.")


    except ValueError as ve:
        print(f"Initialization Error: {ve}")
    except Exception as ex:
        print(f"An unexpected error occurred: {ex}")