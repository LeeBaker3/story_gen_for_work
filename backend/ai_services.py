import openai
from openai import OpenAI
import os
import requests
import json
from dotenv import load_dotenv
from typing import List, Dict, Any
# Import loggers
from .logging_config import api_logger, error_logger
from .schemas import CharacterDetail  # Added for type hinting

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
    story_input should contain: genre, story_outline, main_characters, num_pages, tone, setting, image_style.
    """
    # Construct the prompt based on PRD section 5
    # Updated character description formatting to include new detailed fields
    character_lines = []
    for char_data in story_input['main_characters']:
        details = []
        # Prioritize new, specific fields
        if char_data.get('age'):
            details.append(f"Age: {char_data['age']}")
        if char_data.get('gender'):
            details.append(f"Gender: {char_data['gender']}")
        if char_data.get('physical_appearance'):
            details.append(
                f"Physical Appearance: {char_data['physical_appearance']}")
        if char_data.get('clothing_style'):
            details.append(f"Clothing Style: {char_data['clothing_style']}")
        if char_data.get('key_traits'):
            details.append(f"Key Traits: {char_data['key_traits']}")

        # Include older/general fields if they are still provided and relevant
        # 'description' is the old general description, now optional.
        # Avoid redundancy if physical_appearance is detailed
        if char_data.get('description') and not char_data.get('physical_appearance'):
            details.append(f"Basic Description: {char_data['description']}")
        if char_data.get('personality'):
            details.append(f"Personality: {char_data['personality']}")
        if char_data.get('background'):
            details.append(f"Background: {char_data['background']}")

        # filter(None, ...) removes empty strings if a field was empty
        details_str = ". ".join(filter(None, details))
        character_lines.append(
            f"- {char_data['name']}: {details_str if details_str else 'No specific details provided.'}")
    characters_description = "\n".join(character_lines)

    image_style_description = story_input.get('image_style', 'Default')
    # Ensure a user-friendly string if it's an enum value
    if hasattr(image_style_description, 'value'):
        image_style_description = image_style_description.value

    prompt = f"""Please generate a story that meets the following requirements. The story will be of a specific length in pages. Each page of the story will need an image description that is appropriate for use as a prompt to generate an AI-created image. The image description should be relevant to the story content on that page.

Instructions:
- The story genre is: {story_input['genre']}.
- Story outline: {story_input['story_outline']}.
- Main characters:
{characters_description}
- The story must be {story_input['num_pages']} pages long.
- The desired visual style for all images is: '{image_style_description}'. All "Image_description" fields must reflect this style (e.g., by appending ', {image_style_description} style' or similar phrasing to the description).
- Optional tone: {story_input.get('tone', 'N/A')}.
- Optional setting: {story_input.get('setting', 'N/A')}.

Requirements:
- The story should start with a title.
- For each page, provide the page number, the story text for that page, and a detailed image prompt (Image_description). It is absolutely crucial that every page has a non-empty "Image_description".
- For each "Image_description", ensure it vividly describes the scene based on the "Text" of the page AND incorporates the specified visual style: '{image_style_description}'.
- Crucially, if main characters (as defined in the 'Main characters' section above, using details like physical appearance, clothing, age, gender, and key traits) are present or implied in the scene for a page, their "Image_description" MUST include their key visual details to ensure visual consistency across all story images. Reiterate these character details in each relevant image description, also maintaining the '{image_style_description}' style.
- The final output MUST be a single JSON object. This JSON object must have a top-level key 'Title' (string) and a top-level key 'Pages' (a list of page objects as described above). Do not include any text or explanations outside of this JSON object.
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


def generate_character_reference_image(character: CharacterDetail, base_image_path: str) -> str:
    """
    Generates a character reference image using DALL·E 3 and saves it.

    Args:
        character: A CharacterDetail object containing character attributes.
        base_image_path: The base directory path to save the image (e.g., data/images/story_id/).

    Returns:
        The path to the saved character reference image.
    """
    api_logger.info(
        f"Generating reference image for character: {character.name}")

    # Construct a detailed prompt for character reference image
    prompt_parts = [
        f"Character concept art reference sheet: {character.name}.",
        "Full body portrait, clear view of the character.",
        "Neutral background, studio lighting, concept art style.",
    ]
    if character.physical_appearance:
        prompt_parts.append(
            f"Physical appearance: {character.physical_appearance}.")
    if character.clothing_style:
        prompt_parts.append(f"Typical clothing: {character.clothing_style}.")
    if character.age:
        prompt_parts.append(f"Age: {character.age}.")
    if character.gender:
        prompt_parts.append(f"Gender: {character.gender}.")
    if character.key_traits:
        prompt_parts.append(
            f"Key traits to visualize: {character.key_traits}.")

    prompt = " ".join(prompt_parts)
    api_logger.debug(f"Prompt for {character.name} reference image: {prompt}")

    # Sanitize character name for filename
    safe_character_name = "".join(
        c if c.isalnum() else '_' for c in character.name)
    image_filename = f"character_{safe_character_name}_reference.png"

    # Ensure the base_image_path ends with a slash if it's a directory
    # and then join with character-specific subfolder and filename
    # Example: data/images/STORY_ID/characters/CHARACTER_NAME_reference.png
    character_image_dir = os.path.join(base_image_path, "characters")
    # Ensure character-specific directory exists
    os.makedirs(character_image_dir, exist_ok=True)
    full_image_path = os.path.join(character_image_dir, image_filename)

    try:
        saved_image_path = generate_image_from_dalle(prompt, full_image_path)
        api_logger.info(
            f"Successfully generated and saved reference image for {character.name} at {saved_image_path}")
        return saved_image_path
    except Exception as e:
        error_logger.error(
            f"Failed to generate reference image for character {character.name}: {e}", exc_info=True)
        # Depending on desired error handling, could return None or re-raise
        # For now, re-raising to make it visible during development
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
