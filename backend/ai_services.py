import openai
from openai import OpenAI
import os
import requests
import json
from dotenv import load_dotenv
from typing import List, Dict, Any
# Import loggers
from .logging_config import api_logger, error_logger
from .schemas import CharacterDetail, WordToPictureRatio  # Added WordToPictureRatio

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    # Use error_logger for critical setup issues
    error_logger.error("OPENAI_API_KEY not found in environment variables.")
    raise ValueError(
        "OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")

# Initialize the new client
client = OpenAI(api_key=OPENAI_API_KEY)

EXPECTED_CHATGPT_RESPONSE_KEYS = ["Title", "Pages"]
EXPECTED_PAGE_KEYS = ["Page_number", "Text", "Image_description"]


def generate_story_from_chatgpt(story_input: dict) -> Dict[str, Any]:
    """
    Generates a story using OpenAI's ChatGPT API based on user inputs.
    story_input should contain: genre, story_outline, main_characters, num_pages, tone, setting, image_style, word_to_picture_ratio, text_density.
    """
    # Prepare character descriptions
    character_lines = []
    for char_data in story_input['main_characters']:
        details = []
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
        if char_data.get('description') and not char_data.get('physical_appearance'):
            details.append(f"Basic Description: {char_data['description']}")
        if char_data.get('personality'):
            details.append(f"Personality: {char_data['personality']}")
        if char_data.get('background'):
            details.append(f"Background: {char_data['background']}")
        details_str = ". ".join(filter(None, details))
        character_lines.append(
            f"- {char_data['name']}: {details_str if details_str else 'No specific details provided.'}")
    characters_description = "\n".join(character_lines)

    # Prepare image style description
    image_style_description = story_input.get('image_style', 'Default')
    if hasattr(image_style_description, 'value'):  # Handle Pydantic Enum
        image_style_description = image_style_description.value

    # Prepare text density instructions (New Req)
    raw_text_density = story_input.get(
        'text_density', 'CONCISE')  # Default in schema is CONCISE
    if hasattr(raw_text_density, 'value'):  # Handle Pydantic Enum
        text_density = raw_text_density.value
    else:
        text_density = str(raw_text_density)

    text_density_instruction = ""
    if text_density == 'CONCISE':
        text_density_instruction = "Each page should contain concise text, approximately 3-4 lines long."
    elif text_density == 'STANDARD':
        text_density_instruction = "Each page should contain a standard amount of text, approximately 5-7 lines long."
    elif text_density == 'DETAILED':
        text_density_instruction = "Each page should contain detailed text, approximately 8-10 lines or more."
    else:
        error_logger.warning(
            f"Invalid text_density '{text_density}' received. Defaulting to Concise (3-4 lines).")
        text_density_instruction = "Each page should contain concise text, approximately 3-4 lines long."

    # Prepare word-to-picture ratio and instructions
    # Default to PER_PAGE if not provided or invalid, though schema has a default.
    raw_ratio = story_input.get(
        'word_to_picture_ratio', WordToPictureRatio.PER_PAGE.value)
    if hasattr(raw_ratio, 'value'):  # Handle Pydantic Enum
        word_to_picture_ratio = raw_ratio.value
    else:
        word_to_picture_ratio = str(raw_ratio)  # Ensure it's a string

    num_pages_input = story_input['num_pages']
    num_pages_description = f"{num_pages_input} pages"
    if word_to_picture_ratio == WordToPictureRatio.PER_PARAGRAPH.value:
        num_pages_description = f"{num_pages_input} paragraphs/segments"

    image_generation_instructions = ""
    if word_to_picture_ratio == WordToPictureRatio.PER_PAGE.value:
        image_generation_instructions = f"""
- The story must be {num_pages_description} long.
- For each page, provide the page number, the story text for that page, and a detailed image prompt (Image_description).
- It is absolutely crucial that every page has a non-empty "Image_description".
"""
    elif word_to_picture_ratio == WordToPictureRatio.PER_TWO_PAGES.value:
        image_generation_instructions = f"""
- The story must be {num_pages_description} long.
- Image Generation Strategy: One image for every two pages.
  - For even-numbered pages (e.g., page 2, page 4, ... up to page {num_pages_input}), provide a detailed `Image_description` relevant to the text of that page. This description must be a non-empty string.
  - For odd-numbered pages (e.g., page 1, page 3, ... up to page {num_pages_input}), the `Image_description` field MUST be `null`.
  - Ensure every page object in the JSON has an `Image_description` key, with its value adhering to these rules.
"""
    elif word_to_picture_ratio == WordToPictureRatio.PER_PARAGRAPH.value:
        image_generation_instructions = f"""
- The story should be composed of {num_pages_description}. Each paragraph/segment will be treated as a separate 'page' in the output structure.
- The 'Pages' list in the JSON should contain {num_pages_input} objects.
- Each object in the 'Pages' list represents one paragraph/segment and must have:
    - `Page_number`: A sequential number for the paragraph/segment (1, 2, 3,... up to {num_pages_input}).
    - `Text`: The text content of that single paragraph/segment.
    - `Image_description`: A detailed image prompt relevant to that paragraph/segment's text.
- It is absolutely crucial that every paragraph/segment (i.e., every 'page' object) has a non-empty "Image_description".
"""
    else:  # Fallback to PER_PAGE if somehow an invalid ratio string is passed
        error_logger.warning(
            f"Invalid word_to_picture_ratio '{word_to_picture_ratio}' received. Defaulting to PER_PAGE.")
        # for validation logic later
        word_to_picture_ratio = WordToPictureRatio.PER_PAGE.value
        image_generation_instructions = f"""
- The story must be {num_pages_input} pages long.
- For each page, provide the page number, the story text for that page, and a detailed image prompt (Image_description).
- It is absolutely crucial that every page has a non-empty "Image_description".
"""

    prompt = f"""Please generate a story that meets the following requirements. The story will be of a specific length. Each segment of the story will need an image description (or null if specified by the ratio) that is appropriate for use as a prompt to generate an AI-created image.

Instructions:
- The story genre is: {story_input['genre']}.
- Story outline: {story_input['story_outline']}.
- Main characters:\n{characters_description}
{image_generation_instructions}
- The desired visual style for all images is: '{image_style_description}'. All "Image_description" fields that are not null must reflect this style (e.g., by appending ', {image_style_description} style' or similar phrasing to the description).
- {text_density_instruction}
- Optional tone: {story_input.get('tone', 'N/A')}.
- Optional setting: {story_input.get('setting', 'N/A')}.

Requirements:
- The story should start with a title.
- For each "Image_description" that is not null, ensure it vividly describes the scene based on the "Text" of the page/segment AND incorporates the specified visual style: '{image_style_description}'.
- Crucially, if main characters (as defined above) are present or implied in the scene for a page/segment with an image, their "Image_description" (if not null) MUST include their key visual details to ensure visual consistency. Reiterate these character details in each relevant image description, also maintaining the '{image_style_description}' style.
- The final output MUST be a single JSON object. This JSON object must have a top-level key 'Title' (string) and a top-level key 'Pages' (a list of page objects as described above, adhering to the image generation strategy). Do not include any text or explanations outside of this JSON object.
"""
    api_logger.debug(
        f"Prompt sent to ChatGPT for story generation (ratio: {word_to_picture_ratio}): {prompt[:500]}...")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a creative story writer that outputs structured JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        api_logger.debug(
            f"Raw content received from ChatGPT: {content[:500]}...")

        story_data = json.loads(content)
        api_logger.info("Successfully parsed JSON response from ChatGPT.")

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

            page_num = page.get("Page_number")
            img_desc = page.get("Image_description")

            if not isinstance(page.get("Text"), str):  # Text must always be a string
                error_logger.error(
                    f"Page {page_num}: Text has invalid type '{type(page.get('Text'))}'. Expected string. Page: {page}")
                raise ValueError(f"Page {page_num}: Text must be a string.")

            if not isinstance(img_desc, (str, type(None))):
                error_logger.error(
                    f"Page {page_num}: Image_description has invalid type '{type(img_desc)}'. Expected string or null. Page: {page}")
                raise ValueError(
                    f"Page {page_num}: Image_description must be a string or null.")

            if word_to_picture_ratio == WordToPictureRatio.PER_PAGE.value or \
               word_to_picture_ratio == WordToPictureRatio.PER_PARAGRAPH.value:
                if not isinstance(img_desc, str) or not img_desc.strip():
                    error_logger.error(
                        f"Page {page_num}: Image_description must be a non-empty string for ratio '{word_to_picture_ratio}'. Got: '{img_desc}'. Page: {page}")
                    raise ValueError(
                        f"Page {page_num}: Image_description must be a non-empty string for ratio '{word_to_picture_ratio}'.")
            elif word_to_picture_ratio == WordToPictureRatio.PER_TWO_PAGES.value:
                # Should be caught by earlier Pydantic or schema validation if Page_number is not int
                if not isinstance(page_num, int):
                    error_logger.error(
                        f"Page_number '{page_num}' is not an integer. Cannot validate PER_TWO_PAGES. Page: {page}")
                    raise ValueError(
                        f"Page_number '{page_num}' is not an integer.")

                if page_num % 2 == 0:  # Even page
                    if not isinstance(img_desc, str) or not img_desc.strip():
                        error_logger.error(
                            f"Page {page_num} (even): Image_description must be a non-empty string for ratio '{word_to_picture_ratio}'. Got: '{img_desc}'. Page: {page}")
                        raise ValueError(
                            f"Page {page_num} (even): Image_description must be a non-empty string for ratio '{word_to_picture_ratio}'.")
                else:  # Odd page
                    if img_desc is not None:
                        error_logger.error(
                            f"Page {page_num} (odd): Image_description must be null for ratio '{word_to_picture_ratio}'. Got: '{img_desc}'. Page: {page}")
                        raise ValueError(
                            f"Page {page_num} (odd): Image_description must be null for ratio '{word_to_picture_ratio}'.")

            # Validate Page_number type (already implicitly handled by Pydantic if schema is used for parsing, but good for direct JSON)
            if not isinstance(page_num, int):
                error_logger.error(
                    f"Page_number has invalid type '{type(page_num)}'. Expected int. Page: {page}")
                raise ValueError("Page_number must be an integer.")

        api_logger.debug(
            "ChatGPT response structure and content validated successfully against word_to_picture_ratio.")
        return story_data
    except json.JSONDecodeError as e:
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
        "num_pages": 4,  # Test with even number for PER_TWO_PAGES
        "tone": "Lighthearted and adventurous",
        "setting": "A medieval kingdom with a dark forest",
        "image_style": "Cartoon",
        # Or use WordToPictureRatio.PER_TWO_PAGES.value
        "word_to_picture_ratio": "PER_TWO_PAGES"
    }
    try:
        print(
            f"Generating story from ChatGPT with ratio: {sample_story_input.get('word_to_picture_ratio')}...")
        generated_story = generate_story_from_chatgpt(sample_story_input)
        print("Successfully generated story:")
        print(json.dumps(generated_story, indent=2))

        if generated_story and generated_story.get("Pages"):
            for i, page_data in enumerate(generated_story["Pages"]):
                page_prompt = page_data.get("Image_description")
                page_num_text = page_data.get(
                    "Page_number", f"Unknown (index {i})")
                if page_prompt:  # Check if not None and not empty string
                    print(
                        f"\nGenerating image for page {page_num_text} with prompt: {page_prompt}")
                    # Ensure the 'data/images' directory exists for the test
                    test_image_dir = os.path.join(os.path.dirname(
                        __file__), '..', 'data', 'images', 'test_ai_service')
                    os.makedirs(test_image_dir, exist_ok=True)
                    image_file_path = os.path.join(
                        test_image_dir, f"test_image_page_{page_num_text}.png")
                    saved_path = generate_image_from_dalle(
                        page_prompt, image_file_path)
                    print(
                        f"Successfully generated and saved image to: {saved_path}")
                else:
                    print(
                        f"\nNo image description (or it's null) for page {page_num_text} as per ratio.")
        else:
            print("No pages found in the generated story to test image generation.")

    except ValueError as e:
        print(f"Input or parsing error: {e}")
    except openai.APIError as e:
        print(f"OpenAI API error during test: {e}")
    except Exception as e:
        print(f"Generic error during test: {e}")
