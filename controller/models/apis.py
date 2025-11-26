import json
import os
import time
import traceback
import base64
from io import BytesIO
from PIL import Image

import ollama
from ultralytics import YOLO

from operate.config import Config
from operate.models.prompts import (
    get_user_first_message_prompt,
    get_user_prompt,
    get_system_prompt,
)
from operate.utils.screenshot import capture_screen_with_cursor
from operate.utils.label import add_labels
from operate.utils.style import ANSI_BRIGHT_MAGENTA, ANSI_GREEN, ANSI_RED, ANSI_RESET

# Load configuration
config = Config()


async def get_next_action(model, messages, objective, session_id):
    """
    Route to Ollama for any model request.
    Supports any Ollama model (llava, gemma3, mistral, etc.)
    """
    # All models are handled by Ollama
    operation = call_ollama_llava(messages, model)
    return operation, None


def call_ollama_llava(messages, model="llava"):
    """
    Call any Ollama model (llava, gemma3, mistral, etc.)
    For gemma3, uses YOLO object detection to add labeled bounding boxes
    
    Args:
        messages: The conversation history
        model: The Ollama model name (default: llava)
    """
    time.sleep(1)
    try:
        ollama_client = config.initialize_ollama()
        screenshots_dir = "screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

        screenshot_filename = os.path.join(screenshots_dir, "screenshot.png")
        # Call the function to capture the screen with the cursor
        capture_screen_with_cursor(screenshot_filename)

        # Check if we should use YOLO labeling
        # Only use for models that were designed with YOLO support
        # Gemma models are text-only and don't support vision
        use_labeling = False  # Disabled YOLO for now
        label_coordinates = None
        
        if use_labeling:
            # Load YOLO model for object detection
            try:
                yolo_model_path = os.path.join(
                    os.path.dirname(__file__),
                    "weights",
                    "best.pt"
                )
                yolo_model = YOLO(yolo_model_path)
                
                # Read the screenshot and convert to base64
                with open(screenshot_filename, "rb") as image_file:
                    image_data = image_file.read()
                    base64_image = base64.b64encode(image_data).decode('utf-8')
                
                # Add labels using YOLO - returns base64 string and label coordinates
                labeled_image_base64, label_coordinates = add_labels(base64_image, yolo_model)
                
                # Decode the base64 back to image and save it
                labeled_image_bytes = base64.b64decode(labeled_image_base64)
                labeled_image = Image.open(BytesIO(labeled_image_bytes))
                labeled_image.save(screenshot_filename)
                
            except Exception as e:
                if config.verbose:
                    print(f"{ANSI_RED}[Warning] YOLO labeling failed, falling back to standard mode: {e}{ANSI_RESET}")
                use_labeling = False

        if len(messages) == 1:
            user_prompt = get_user_first_message_prompt()
        else:
            user_prompt = get_user_prompt()

        vision_message = {
            "role": "user",
            "content": user_prompt,
            "images": [screenshot_filename],
        }
        messages.append(vision_message)

        response = ollama_client.chat(
            model=model,
            messages=messages,
        )

        # Important: Remove the image path from the message history.
        # Ollama will attempt to load each image reference and will
        # eventually timeout.
        messages[-1]["images"] = None

        content = response["message"]["content"].strip()

        content = clean_json(content)

        assistant_message = {"role": "assistant", "content": content}
        content = json.loads(content)

        messages.append(assistant_message)

        return content

    except ollama.ResponseError as e:
        print(
            f"{ANSI_GREEN}[giri-prasad]{ANSI_RED}[Operate] Couldn't connect to Ollama. With Ollama installed, run `ollama pull {model}` then `ollama serve`{ANSI_RESET}"
        )
        if config.verbose:
            print(e)

    except Exception as e:
        print(
            f"{ANSI_GREEN}[giri-prasad]{ANSI_BRIGHT_MAGENTA}[{model}] That did not work. Trying again {ANSI_RESET}"
        )
        if config.verbose:
            print(f"{ANSI_GREEN}[giri-prasad]{ANSI_RED}[Error] AI response was {ANSI_RESET}", content)
            print(e)
            traceback.print_exc()
        return call_ollama_llava(messages, model)

def get_last_assistant_message(messages):
    """
    Retrieve the last message from the assistant in the messages array.
    If the last assistant message is the first message in the array, return None.
    """
    for index in reversed(range(len(messages))):
        if messages[index]["role"] == "assistant":
            if index == 0:  # Check if the assistant message is the first in the array
                return None
            else:
                return messages[index]
    return None  # Return None if no assistant message is found

def confirm_system_prompt(messages, objective, model):
    """
    On `Exception` we default to `call_gpt_4_vision_preview` so we have this function to reassign system prompt in case of a previous failure
    """
    if config.verbose:
        print("[confirm_system_prompt] model", model)

    system_prompt = get_system_prompt(model, objective)
    new_system_message = {"role": "system", "content": system_prompt}
    # remove and replace the first message in `messages` with `new_system_message`

    messages[0] = new_system_message

    if config.verbose:
        print("[confirm_system_prompt]")
        print("[confirm_system_prompt] len(messages)", len(messages))
        for m in messages:
            if m["role"] != "user":
                print("--------------------[message]--------------------")
                print("[confirm_system_prompt][message] role", m["role"])
                print("[confirm_system_prompt][message] content", m["content"])
                print("------------------[end message]------------------")

def clean_json(content):
    if config.verbose:
        print("\n\n[clean_json] content before cleaning", content)
    if content.startswith("```json"):
        content = content[
            len("```json") :
        ].strip()  # Remove starting ```json and trim whitespace
    elif content.startswith("```"):
        content = content[
            len("```") :
        ].strip()  # Remove starting ``` and trim whitespace
    if content.endswith("```"):
        content = content[
            : -len("```")
        ].strip()  # Remove ending ``` and trim whitespace

    # Normalize line breaks and remove any unwanted characters
    content = "\n".join(line.strip() for line in content.splitlines())

    if config.verbose:
        print("\n\n[clean_json] content after cleaning", content)

    return content
