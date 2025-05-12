import openai
from openai import OpenAI
import os
import requests
import json
from dotenv import load_dotenv
from typing import List, Dict, Any
# Import loggers
from .logging_config import api_logger, error_logger

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    # Use error_logger for critical setup issues
    error_logger.error("OPENAI_API_KEY not found in environment variables.")
    raise ValueError(
        "OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")

# Initialize the new client
client = OpenAI(api_key=OPENAI_API_KEY)

# As per PRD: FR7 JSON format from ChatGPT includes title, pages, and image prompts with keys: Title, Page, Image_description.
# Example Page: {"text": "Once upon a time...", "Image_description": "A castle in the clouds"}

EXPECTED_CHATGPT_RESPONSE_KEYS = ["Title", "Pages"]  # Pages is a list of dicts
# Page_number, Text from PRD example, Image_description from FR7
EXPECTED_PAGE_KEYS = ["Page_number", "Text", "Image_description"]


def generate_story_from_chatgpt(story_input: dict) -> Dict[str, Any]:
    """
    Generates a story using OpenAI's ChatGPT API based on user inputs.
    story_input should contain: genre, story_outline, main_characters, num_pages, tone, setting.
    """
    # Construct the prompt based on PRD section 5
    characters_description = "\n".join([
        f"- {char['name']}: {char['description']}. Personality: {char.get('personality', 'N/A')}. Background: {char.get('background', 'N/A')}."
        for char in story_input['main_characters']
    ])

    prompt = f"""Please generate a story that meets the following requirements. The story will be of a specific length in pages. Each page of the story will need an image description that is appropriate for use as a prompt to generate an AI-created image. The image description should be relevant to the story content on that page and consistent in visual style.

Instructions:
- The story genre is: {story_input['genre']}.
- Story outline: {story_input['story_outline']}.
- Main characters:
{characters_description}
- The story must be {story_input['num_pages']} pages long.
- Optional tone: {story_input.get('tone', 'N/A')}.
- Optional setting: {story_input.get('setting', 'N/A')}.

Requirements:
- The story should start with a title.
- For each page, provide the page number, the story text for that page, and a detailed image prompt (Image_description).
- For each "Image_description", ensure it vividly describes the scene based on the "Text" of the page.
- Crucially, if main characters (as defined in the 'Main characters' section above) are present or implied in the scene for a page, their "Image_description" MUST include their key visual details (e.g., 'a young girl with bright red pigtails and freckles') to ensure visual consistency across all story images. Reiterate these character details in each relevant image description. For example, if a character 'ZARA' is described as 'a young girl with bright red pigtails and freckles', and she is in a scene, the Image_description should include this (e.g., 'ZARA, the young girl with bright red pigtails and freckles, looks at the mysterious map.').
- Each page's content (page number, text, image description) should be structured.
- Return the entire response as a single valid JSON object.
- The JSON object must have a top-level key "Title" for the story title.
- The JSON object must have a top-level key "Pages" which is a list of page objects.
- Each page object in the "Pages" list must have the keys: "Page_number" (integer), "Text" (string), and "Image_description" (string for DALL-E prompt).

Example of a page object within the "Pages" list:
{{
  "Page_number": 1,
  "Text": "Once upon a time, in a land far away...",
  "Image_description": "A mystical forest with glowing mushrooms and a hidden path, fantasy art style."
}}

Ensure the JSON is well-formed and complete.
"""
    api_logger.debug(
        # Log a snippet
        f"Prompt sent to ChatGPT for story generation: {prompt[:500]}...")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Or "gpt-4"
            messages=[
                {"role": "system", "content": "You are a creative story writer that outputs structured JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,  # Adjust for creativity
            # For newer models that support JSON mode
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        # Log a snippet
        api_logger.debug(
            f"Raw content received from ChatGPT: {content[:500]}...")

        # Attempt to parse the JSON content
        story_data = json.loads(content)
        api_logger.info("Successfully parsed JSON response from ChatGPT.")

        # Validate structure (basic validation)
        if not all(key in story_data for key in EXPECTED_CHATGPT_RESPONSE_KEYS):
            error_logger.error(
                f"ChatGPT response missing one of keys: {EXPECTED_CHATGPT_RESPONSE_KEYS}. Response: {story_data}")
            raise ValueError(
                f"ChatGPT response missing one of keys: {EXPECTED_CHATGPT_RESPONSE_KEYS}")
        if not isinstance(story_data["Pages"], list):
            error_logger.error(
                f"ChatGPT response 'Pages' should be a list. Response: {story_data}")
            raise ValueError("ChatGPT response 'Pages' should be a list.")
        for page in story_data["Pages"]:
            if not all(key in page for key in EXPECTED_PAGE_KEYS):
                error_logger.error(
                    f"Each page in ChatGPT response missing one of keys: {EXPECTED_PAGE_KEYS}. Page: {page}")
                raise ValueError(
                    f"Each page in ChatGPT response missing one of keys: {EXPECTED_PAGE_KEYS}")
            if not isinstance(page.get("Page_number"), int) or not isinstance(page.get("Text"), str) or not isinstance(page.get("Image_description"), str):
                error_logger.error(
                    f"Invalid data type for page attributes. Page: {page}")
                raise ValueError("Invalid data type for page attributes.")
        api_logger.debug("ChatGPT response structure validated successfully.")
        return story_data
    except json.JSONDecodeError as e:
        # Log the invalid JSON `content` for debugging
        error_logger.error(
            f"ChatGPT returned invalid JSON. Content: {content}", exc_info=True)
        raise ValueError(
            f"Failed to decode JSON response from ChatGPT. Error: {e}")
    except openai.APIError as e:
        error_logger.error(
            f"OpenAI API Error during story generation: {e}", exc_info=True)
        raise
    except Exception as e:
        error_logger.error(
            f"An unexpected error occurred while generating story: {e}", exc_info=True)
        raise


def generate_image_from_dalle(prompt: str, image_path: str) -> str:
    """
    Generates an image using DALL·E 3 based on a prompt and saves it locally.
    Returns the path to the saved image.
    """
    api_logger.debug(
        f"Attempting to generate image with DALL-E. Prompt: {prompt[:200]}...")
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",  # or "1792x1024", "1024x1792"
            quality="standard",  # or "hd"
            n=1,
            response_format="url"  # or "b64_json"
        )
        image_url = response.data[0].url
        api_logger.info(f"DALL-E returned image URL: {image_url}")

        # Download and save the image
        api_logger.debug(f"Downloading image from URL: {image_url}")
        image_response = requests.get(image_url, stream=True)
        image_response.raise_for_status()  # Raise an exception for HTTP errors

        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        with open(image_path, 'wb') as f:
            for chunk in image_response.iter_content(8192):
                f.write(chunk)
        api_logger.info(
            f"Successfully downloaded and saved image to: {image_path}")
        return image_path
    except openai.APIError as e:
        error_logger.error(f"DALL-E API Error: {e}", exc_info=True)
        # Potentially return a placeholder or raise a specific exception
        raise
    except requests.exceptions.RequestException as e:
        error_logger.error(
            f"Error downloading image from {image_url if 'image_url' in locals() else 'unknown URL'}: {e}", exc_info=True)
        raise
    except Exception as e:
        error_logger.error(
            f"An unexpected error occurred while generating image: {e}", exc_info=True)
        raise


# Example usage (for testing this file directly)
if __name__ == "__main__":
    # Test ChatGPT
    sample_story_input = {
        "genre": "Children’s",
        "story_outline": "A brave knight saves a friendly dragon from a misunderstanding village.",
        "main_characters": [
            {"name": "Sir Reginald", "description": "A kind knight in shiny armor",
                "personality": "Brave and fair"},
            {"name": "Sparky", "description": "A small, green dragon who loves to play",
                "personality": "Playful and misunderstood"}
        ],
        "num_pages": 3,
        "tone": "Lighthearted and adventurous",
        "setting": "A medieval kingdom with a dark forest"
    }
    try:
        print("Generating story from ChatGPT...")
        generated_story = generate_story_from_chatgpt(sample_story_input)
        print("Successfully generated story:")
        print(json.dumps(generated_story, indent=2))

        if generated_story and generated_story.get("Pages"):
            first_page_prompt = generated_story["Pages"][0].get(
                "Image_description")
            if first_page_prompt:
                print(
                    f"\nGenerating image for first page with prompt: {first_page_prompt}")
                # Ensure the 'data/images' directory exists for the test
                # Adjust path for direct script execution if necessary, assuming 'data' is sibling to 'backend'
                test_image_dir = os.path.join(os.path.dirname(
                    __file__), '..', 'data', 'images', 'test_ai_service')
                os.makedirs(test_image_dir, exist_ok=True)
                image_file_path = os.path.join(
                    test_image_dir, "test_image_from_ai_service.png")
                saved_path = generate_image_from_dalle(
                    first_page_prompt, image_file_path)
                print(
                    f"Successfully generated and saved image to: {saved_path}")
            else:
                print("No image description found for the first page.")
        else:
            print("No pages found in the generated story to test image generation.")

    except ValueError as e:
        print(f"Input or parsing error: {e}")
    except openai.APIError as e:
        print(f"OpenAI API error during test: {e}")
    except Exception as e:
        print(f"Generic error during test: {e}")
