import openai
from openai import OpenAI
import os
import requests
import json
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import base64
import uuid
import sys
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.orm import Session
import asyncio
import io

# Import loggers
from .logging_config import api_logger, error_logger, app_logger
from . import crud, schemas
from .schemas import CharacterDetail, WordToPictureRatio, ImageStyle, TextDensity

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    error_logger.error("OPENAI_API_KEY not found in environment variables.")
    raise ValueError(
        "OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")

# Define a retry decorator for OpenAI API calls
api_retry = retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    retry=retry_if_exception_type((openai.APIError, openai.Timeout, openai.APIConnectionError,
                                  openai.RateLimitError, requests.exceptions.RequestException)))

# Initialize the new client
client = OpenAI(api_key=OPENAI_API_KEY, base_url="https://api.openai.com/v1")

EXPECTED_CHATGPT_RESPONSE_KEYS = ["Title", "Pages"]
EXPECTED_PAGE_KEYS = ["Page_number", "Text",
                      "Image_description", "Characters_in_scene"]

OPENAI_CLIENT = None

# Initialize logging
logger = logging.getLogger(__name__)
error_logger = logging.getLogger('error_logger')
warning_logger = logging.getLogger('warning_logger')

IMAGE_MODEL = "gpt-image-1"
IMAGE_SIZE = "1024x1024"
MAX_PROMPT_LENGTH = 4000


def _truncate_prompt(prompt: str, max_length: int = MAX_PROMPT_LENGTH) -> str:
    """
    Truncates the prompt to the specified maximum length.
    Avoids cutting words in half if possible, but prioritizes max_length.
    """
    if len(prompt) <= max_length:
        return prompt
    # Simple truncation for now, can be made smarter
    truncated = prompt[:max_length]
    # Try to cut at the last space to avoid breaking a word, if space exists nearby
    # look for space in last 30 chars
    last_space = truncated.rfind(' ', max_length - 30, max_length)
    if last_space != -1:
        return truncated[:last_space] + "..."
    app_logger.warning(
        f"Prompt was truncated mid-word or abruptly. Original length: {len(prompt)}, Max: {max_length}")
    return truncated + "..."


@api_retry
def generate_story_from_chatgpt(story_input: dict) -> Dict[str, Any]:
    """
    Generates a story using OpenAI's ChatGPT API based on user inputs.
    story_input should contain: title (optional), genre, story_outline, main_characters, num_pages, tone, setting, image_style, word_to_picture_ratio, text_density.
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
        if char_data.get('reference_image_path'):
            details.append(
                f"Visuals should align with their established concept art (referenced by path: {char_data['reference_image_path']}). Their look is defined and should not change significantly.")
            if char_data.get('detailed_visual_description_from_reference'):
                details.append(
                    f"AI-Generated Detailed Visuals from Reference Art: {char_data['detailed_visual_description_from_reference']}. These details are extracted directly from the reference image and are paramount for consistency.")
        else:
            details.append(
                f"The listed physical appearance, clothing, and key traits define {char_data['name']}'s consistent look. This look should be maintained across all images.")
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
    if text_density == 'Concise (~30-50 words)':
        text_density_instruction = "Each page should contain concise text, approximately 30-50 words long."
    elif text_density == 'Standard (~60-90 words)':
        text_density_instruction = "Each page should contain a standard amount of text, approximately 60-90 words long."
    elif text_density == 'Detailed (~100-150 words)':
        text_density_instruction = "Each page should contain detailed text, approximately 100-150 words long."
    else:
        error_logger.warning(
            f"Invalid text_density '{text_density}' received. Defaulting to Concise (~30-50 words).")
        text_density_instruction = "Each page should contain concise text, approximately 30-50 words long."

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
- The story must be {num_pages_description} long.
- For each page, provide the page number, the story text for that page, and a detailed image prompt (Image_description).
- It is absolutely crucial that every page has a non-empty "Image_description".
"""

    # Enhanced character instructions for the prompt
    character_visual_instructions = [
        "IMPORTANT: The following visual details for each character are key to maintaining consistency across all images.",
        "When a character is in a scene, their Image_description MUST incorporate these details accurately and consistently with their established look."
    ]
    for char_data in story_input['main_characters']:
        char_name = char_data['name']

        # Escape curly braces in user-provided details
        _raw_physical_appearance = char_data.get('physical_appearance')
        user_physical_appearance = _raw_physical_appearance.replace(
            '{', '{{').replace('}', '}}') if _raw_physical_appearance else None

        _raw_clothing_style = char_data.get('clothing_style')
        user_clothing_style = _raw_clothing_style.replace(
            '{', '{{').replace('}', '}}') if _raw_clothing_style else None

        _raw_ai_generated_desc_from_ref = char_data.get(
            'detailed_visual_description_from_reference')
        ai_generated_desc_from_ref = _raw_ai_generated_desc_from_ref.replace(
            '{', '{{').replace('}', '}}') if _raw_ai_generated_desc_from_ref else None

        _raw_reference_image_revised_prompt = char_data.get(
            'reference_image_revised_prompt')
        reference_image_revised_prompt = _raw_reference_image_revised_prompt.replace(
            '{', '{{').replace('}', '}}') if _raw_reference_image_revised_prompt else None

        _raw_key_traits = char_data.get('key_traits')
        user_key_traits = _raw_key_traits.replace(
            '{', '{{').replace('}', '}}') if _raw_key_traits else None

        details_for_prompt = [f"Character Name: {char_name}"]
        char_specific_visual_description_parts = []

        # 1. Primary Visual: AI-generated revised prompt or user inputs
        if reference_image_revised_prompt:
            char_specific_visual_description_parts.append(
                f"Primary Visual (from AI image model, use verbatim): '{reference_image_revised_prompt}'")
            # Supplementary user inputs
            if user_physical_appearance:
                char_specific_visual_description_parts.append(
                    f"Supplementary Physical Appearance: '{user_physical_appearance}'")
            if user_clothing_style:
                char_specific_visual_description_parts.append(
                    f"Supplementary Clothing Style: '{user_clothing_style}'")
        else:
            # Fallback to user descriptions if no revised_prompt
            if user_physical_appearance:
                char_specific_visual_description_parts.append(
                    f"Physical Appearance: '{user_physical_appearance}'")
            if user_clothing_style:
                char_specific_visual_description_parts.append(
                    f"Clothing Style: '{user_clothing_style}'")

        # 2. AI Generated Description (from reference image analysis)
        if ai_generated_desc_from_ref:
            # Check if other primary/secondary details already exist
            if reference_image_revised_prompt or \
               (not reference_image_revised_prompt and (user_physical_appearance or user_clothing_style)):
                char_specific_visual_description_parts.append(
                    f"Supplementary AI-Generated Visuals (from reference image analysis): '{ai_generated_desc_from_ref}'")
            else:  # This becomes a primary source if others are missing
                char_specific_visual_description_parts.append(
                    f"AI-Generated Visuals (from reference image analysis): '{ai_generated_desc_from_ref}'")

        # 3. User Key Traits
        if user_key_traits:
            char_specific_visual_description_parts.append(
                f"Other Distinctive Traits: '{user_key_traits}'")

        # 4. Form the Canonical Visual Description
        if char_specific_visual_description_parts:
            canonical_description = ". ".join(
                char_specific_visual_description_parts)
            # Ensure the description ends with a period if it doesn't have one, for consistency.
            if canonical_description and not canonical_description.endswith('.'):
                canonical_description += "."
            details_for_prompt.append(
                f"  - Canonical Visual Description to use VERBATIM: '{canonical_description}'")
        else:
            details_for_prompt.append(
                f"  - Note: No specific visual appearance, clothing, or AI-generated details were provided for {char_name}. Use story context if they appear in images.")

        if char_data.get('age'):
            details_for_prompt.append(f"  - Age Context: {char_data['age']}")
        if char_data.get('gender'):
            details_for_prompt.append(
                f"  - Gender Context: {char_data['gender']}")

        if char_data.get('reference_image_path'):
            details_for_prompt.append(
                f"  - Reference Image Note: This character has a reference image. The descriptions above are derived from user inputs and this reference. Visuals MUST align.")

        if len(details_for_prompt) > 1:
            character_visual_instructions.append(
                "\\n".join(details_for_prompt))

    detailed_characters_description = "\\\\n\\\\n".join(
        character_visual_instructions)

    # Prepare story title information for the prompt
    user_provided_title = story_input.get('title')
    title_instruction = ""
    if user_provided_title and user_provided_title.strip():
        title_instruction = f"- The user has provided the following title for the story: '{user_provided_title}'. This title MUST be used for the story. The 'Text' field of the 'Title Page' object must contain this title."
    else:
        title_instruction = f"- The user has NOT provided a story title. You MUST generate a suitable and creative title for the story based on the other inputs. The 'Text' field of the 'Title Page' object must contain this generated title."

    prompt = f"""Please generate a story that meets ALL the following requirements with EXTREME precision. The story will be of a specific length. Each segment of the story will need an image description (or null if specified by the ratio) that is appropriate for use as a prompt to generate an AI-created image.

CRITICAL REQUIREMENT - TEXT DENSITY PER PAGE:
- Adhere ABSOLUTELY STRICTLY to the specified text density: {text_density_instruction}.
- This means the 'Text' field for EACH content page object (Page_number 1, 2, 3, etc.) in the JSON output MUST conform to the word count defined in this instruction. This is a primary constraint.

Further Instructions:
{title_instruction}
- The story genre is: {story_input['genre']}.
- Story outline: {story_input['story_outline']}.
- Main characters and their detailed visual descriptions. These are CRITICAL for visual consistency.
  Review each character's details below. For each character, specific visual descriptions are provided.
{detailed_characters_description}
{image_generation_instructions}
- The desired visual style for all images is: '{image_style_description}'. All "Image_description" fields that are not null must reflect this style (e.g., by appending ', {image_style_description} style' or similar phrasing to the description).
- Optional tone: {story_input.get('tone', 'N/A')}.
- Optional setting: {story_input.get('setting', 'N/A')}.

Output Requirements:
- The final output MUST be a single JSON object.
- This JSON object must have a top-level key 'Title' (string), which is the final title of the story (either user-provided or AI-generated as per title_instruction).
- It must also have a top-level key 'Pages' (a list of page objects).
- CRUCIAL - TITLE PAGE REQUIREMENT:
  - The VERY FIRST page object in the \\'Pages\\' list MUST be a special \\'Title Page\\'.
  - This \\'Title Page\\' object MUST have its \\'Page_number\\' field set to the exact string "Title".
  - Its \\'Text\\' field MUST contain the final story title (matching the top-level \\'Title\\' field).
  - Its \\'Image_description\\' field MUST be a detailed and evocative prompt for a captivating COVER IMAGE.
    - This prompt should focus on setting the overall mood, hinting at the story\\'s theme and genre, and visually introducing the main character(s) in an artistic and engaging way, consistent with their established look but AVOIDING literal depiction of their detailed textual descriptions (like specific height, measurements, or lists of traits).
    - The goal is a visually appealing cover, not a character specification sheet.
    - The description must be a non-empty string and should also incorporate the overall \\\'{image_style_description}\\\'.
    - When main characters are included on the cover, their appearance should be inspired by their \\'Canonical Visual Description\\' but integrated naturally and artistically into the scene, rather than having the full canonical description appended verbatim as is done for internal story pages.
- CONTENT PAGES REQUIREMENT:
  - Subsequent page objects in the 'Pages' list represent the content pages of the story.
  - These content pages MUST have sequential integer 'Page_number' fields (e.g., 1, 2, 3, ...).
  - The 'Text' for these content pages must adhere to the {text_density_instruction}.
  - The 'Image_description' for these content pages must follow the rules specified in {image_generation_instructions} and the 'CRUCIAL FOR IMAGE DESCRIPTION AND VISUAL CONSISTENCY' section below.

- CRUCIAL FOR IMAGE DESCRIPTION AND VISUAL CONSISTENCY (for content pages and the Title Page\\'s cover image):
  For every page/segment that requires an image (i.e., "Image_description" is not null), construct the "Image_description" using the following STRICT, SEQUENTIAL process:
  1. START WITH SCENE FROM PAGE TEXT (or Title/Theme for Cover): MANDATORY FIRST STEP.
     - For Content Pages: Create a vivid description of the scene, including specific actions, character interactions, key objects, and the environment. This description MUST be based DIRECTLY and EXCLUSIVELY on the "Text" of that specific page/segment.
     - For the Title Page (Cover Image): Create a vivid description that captures the essence of the story, its genre, and its title. This forms the foundational part of the "Image_description".
     DO NOT skip or minimize this step.
  2. Identify Characters in Scene (if applicable, mainly for content pages): After describing the scene from the text, determine which of the Main Characters (listed above by name) are present or clearly implied in this scene. For the cover image, characters might be present if central to the theme.
     - For EACH page object (including the Title Page and all content pages), you MUST include a field called "Characters_in_scene". This field must be a JSON list of strings. Each string in the list must be the exact name of a Main Character (from the list provided to you) who is present in the scene described by that page's "Text" and "Image_description".
     - If no Main Characters are present in a specific page's scene, "Characters_in_scene" must be an empty list `[]`.
     - This "Characters_in_scene" list is separate from and in addition to the "Image_description".
  3. Incorporate Character Visuals:
     - For Content Pages: For EACH identified Main Character present in the scene, ensure their depiction in the image is CONSISTENT with their \\'Canonical Visual Description\\'. To achieve this, AFTER describing the scene from step 1, you should weave in KEY RECOGNIZABLE FEATURES from their \\'Canonical Visual Description\\' into the overall Image_description. The primary focus MUST remain the scene from the page text. The character details should support the scene, not overshadow it. Do not just append the entire canonical description if it makes the character description dominate the scene description. Instead, intelligently integrate the most important visual cues to ensure consistency while keeping the scene central. For example, if a character\\'s canonical description is very long, pick the 2-3 most defining visual elements to mention.
     - For the Title Page (Cover Image): If main characters are part of the cover\\\'s theme, ensure their appearance is artistically integrated and clearly inspired by their \\\\'Canonical Visual Description\\\\'. The goal is recognizability and consistency with their established look. AVOID appending the full \\\\'Canonical Visual Description\\\\' verbatim. The depiction should be natural within the artistic composition of the cover, avoiding a literal list of traits. Focus on key recognizable features that align with their canonical look, ensuring these features are consistent with those used in content pages.
  4. Apply Unified Styling: Ensure the ENTIRE "Image_description" (which is: [Scene from Page Text] + [Integrated Key Character Features]) reflects the overall \\\\\\'{image_style_description}\\\\\\'. All characters, objects, and background elements within the single image MUST be rendered in this exact same style. For example, you might append \\\\\\', {image_style_description} style\\\\\\' to the complete description.
  This step-by-step process (1. Scene from Page Text FIRST -> 2. Identify Characters -> 3. Incorporate Character Visuals as specified for page type -> 4. Apply Style) is vital for creating relevant images with consistent characters. The scene description from the page text MUST come first.
- The final output MUST be a single JSON object. This JSON object must have a top-level key \\'Title\\' (string) and a top-level key \\'Pages\\' (a list of page objects as described above, adhering to the image generation strategy). Do not include any text or explanations outside of this JSON object.
"""
    api_logger.debug(
        f"Prompt sent to ChatGPT for story generation (ratio: {word_to_picture_ratio}): {prompt[:500]}...")

    response_text = None
    try:
        app_logger.info(
            f"Sending request to ChatGPT API with prompt: {prompt[:200]}...")
        response = client.chat.completions.create(
            model="gpt-4.1-mini",  # CORRECTED MODEL NAME
            messages=[
                {"role": "system", "content": "You are a creative story writer that outputs structured JSON. Adherence to all formatting and content constraints, including specified text density per page, is critical."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        response_text = response.choices[0].message.content
        api_logger.info(
            f"Received response from ChatGPT API. Length: {len(response_text)}")

        # Validate and return the JSON response
        parsed_response = json.loads(response_text)
        if not all(key in parsed_response for key in EXPECTED_CHATGPT_RESPONSE_KEYS):
            warning_logger.warning(
                f"ChatGPT response missing one of the expected keys: {EXPECTED_CHATGPT_RESPONSE_KEYS}")
        return parsed_response

    except json.JSONDecodeError as e:
        error_logger.error(
            f"Failed to decode JSON from ChatGPT response: {e}. Response text: {response_text}")
        raise
    except Exception as e:
        error_logger.error(
            f"An unexpected error occurred in generate_story_from_chatgpt: {e}")
        raise


@api_retry
async def generate_character_image(character: CharacterDetail, image_style: str, db: Session, user_id: int) -> Optional[str]:
    """
    Generates a character image using the configured AI image model, saves it, and returns the path.
    """
    if not db:
        error_logger.error(
            "Database session is not available in generate_character_image")
        return None

    # ... existing code ...


@api_retry
def generate_character_image_from_description(character_name: str, description: str, image_style: str) -> Optional[str]:
    """
    Generates a character concept image from a description using the configured AI image model.
    """
    # ... existing code ...


@api_retry
async def generate_character_reference_image(character: CharacterDetail, story_input: schemas.StoryCreate, db: Session, user_id: int, story_id: int, image_save_path_on_disk: str = None, image_path_for_db: str = None) -> Optional[Dict[str, Any]]:
    """
    Generates a reference image for a character, saves it, and returns the updated character details as a dict.
    """
    if not db:
        error_logger.error(
            "Database session is not available in generate_character_reference_image")
        return None

    image_style = story_input.image_style
    if hasattr(image_style, 'value'):
        image_style = image_style.value
    else:
        image_style = str(image_style)

    # Construct a detailed prompt with style at the forefront
    prompt_parts = [
        f"A {image_style} style full-body character sheet for {character.name}"]
    if character.physical_appearance:
        prompt_parts.append(character.physical_appearance)
    if character.clothing_style:
        prompt_parts.append(f"wearing {character.clothing_style}")
    if character.key_traits:
        prompt_parts.append(f"Key traits: {character.key_traits}")
    if character.description:
        prompt_parts.append(character.description)

    prompt = ", ".join(prompt_parts)
    prompt += ". The character should be centered, showing front, side, and back views, and not cropped, especially the head or feet."

    image_bytes = await asyncio.to_thread(
        generate_image,
        prompt,
        size="1024x1536"  # Use portrait aspect ratio for full-body shots
    )

    char_dict = character.model_dump(exclude_none=True)

    if image_bytes and image_save_path_on_disk and image_path_for_db:
        try:
            os.makedirs(os.path.dirname(
                image_save_path_on_disk), exist_ok=True)
            with open(image_save_path_on_disk, "wb") as f:
                f.write(image_bytes)
            app_logger.info(
                f"Downloaded and saved character reference image for {character.name} at {image_save_path_on_disk}")

            # Save the prompt to a text file
            prompt_path = os.path.splitext(image_save_path_on_disk)[
                0].replace('_ref_', '_ref_prompt_') + ".txt"
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(prompt)
            app_logger.info(
                f"Saved character reference prompt to {prompt_path}")

            char_dict['reference_image_path'] = image_path_for_db
            return char_dict
        except Exception as e:
            error_logger.error(
                f"Failed to download or save character reference image for {character.name}: {e}")
            char_dict['reference_image_path'] = None
            return char_dict

    char_dict['reference_image_path'] = None
    return char_dict


@api_retry
async def generate_image_for_page(page_content: str, style_reference: str, db: Session, user_id: int, story_id: int, page_number: int, image_save_path_on_disk: str = None, image_path_for_db: str = None, reference_image_paths: Optional[List[str]] = None, characters_in_scene: Optional[List[str]] = None) -> Optional[str]:
    """
    Generates an image for a story page using the configured AI image model, saves it to disk, and returns the relative path.
    """
    if not db:
        error_logger.error(
            "Database session is not available in generate_image_for_page")
        return None

    prompt_parts = [f"A {style_reference} style image of {page_content}"]
    if characters_in_scene:
        prompt_parts.append(
            f"The scene features the following characters: {', '.join(characters_in_scene)}.")
    prompt = ". ".join(prompt_parts)

    # Call the sync generate_image in a thread, passing the paths directly
    image_bytes = await asyncio.to_thread(
        generate_image,
        prompt,
        reference_image_paths=reference_image_paths if reference_image_paths else None
    )

    if image_bytes and image_save_path_on_disk and image_path_for_db:
        try:
            os.makedirs(os.path.dirname(
                image_save_path_on_disk), exist_ok=True)
            with open(image_save_path_on_disk, "wb") as f:
                f.write(image_bytes)
            app_logger.info(
                f"Downloaded and saved image for page {page_number} of story {story_id} at {image_save_path_on_disk}")

            # Save the prompt to a text file
            prompt_path = os.path.splitext(image_save_path_on_disk)[
                0] + "_prompt.txt"
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(prompt)
            app_logger.info(f"Saved page image prompt to {prompt_path}")

            return image_path_for_db
        except Exception as e:
            error_logger.error(
                f"Failed to download or save image for page {page_number} of story {story_id}: {e}")
            return None
    return None


@api_retry
def generate_image(prompt: str, reference_image_paths: Optional[List[str]] = None, size: str = IMAGE_SIZE) -> Optional[bytes]:
    """
    Generates an image using the configured AI model based on a prompt.
    If reference_image_paths are provided, it opens the files and uses the edit endpoint.
    Returns the image as bytes, or None if an error occurred.
    """
    try:
        # Truncate the prompt if it's too long
        truncated_prompt = _truncate_prompt(prompt)

        api_logger.info(
            f"Requesting AI image with prompt: {truncated_prompt}, size: {size}")

        response = None
        if reference_image_paths:
            api_logger.info(
                f"Using {len(reference_image_paths)} reference image(s) for image generation.")

            opened_files = []
            try:
                for path in reference_image_paths:
                    # The path from the DB is relative to the 'data' directory, e.g., 'images/user_1/...'
                    full_path = os.path.join("data", path)
                    if os.path.exists(full_path):
                        opened_files.append(open(full_path, "rb"))
                    else:
                        error_logger.warning(
                            f"Reference image not found at path: {full_path}")

                if opened_files:
                    response = client.images.edit(
                        model=IMAGE_MODEL,
                        image=opened_files,
                        prompt=truncated_prompt,
                        size=size,
                        n=1
                    )
            finally:
                for f in opened_files:
                    f.close()

        # If no references were provided, or if opening files failed, generate a new image
        if response is None:
            response = client.images.generate(
                model=IMAGE_MODEL,
                prompt=truncated_prompt,
                size=size,
                quality="auto",
                n=1
            )

        api_logger.info(f"Response from AI image model: {response}")
        api_logger.info("Successfully received image from AI image model.")

        b64_json = response.data[0].b64_json
        if not b64_json:
            error_logger.error("AI image model returned an empty b64_json.")
            return None

        return base64.b64decode(b64_json)
    except openai.APIError as e:
        error_logger.error(f"OpenAI API error in AI image generation: {e}")
        raise
    except Exception as e:
        error_logger.error(
            f"An unexpected error occurred in AI image generation: {e}")
        raise
