import openai
from openai import OpenAI
import os
import requests
import json
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional  # Added Optional
import base64  # Added for image encoding
import uuid  # Added for unique filenames
import sys  # Added import
import logging  # Added logging import

# Import loggers
from .logging_config import api_logger, error_logger, app_logger  # Added app_logger
# Added ImageStyle, TextDensity
from .schemas import CharacterDetail, WordToPictureRatio, ImageStyle, TextDensity

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
# Added "Characters_in_scene" to expected page keys
EXPECTED_PAGE_KEYS = ["Page_number", "Text",
                      "Image_description", "Characters_in_scene"]

OPENAI_CLIENT = None

# Initialize logging
logger = logging.getLogger(__name__)
error_logger = logging.getLogger('error_logger')
warning_logger = logging.getLogger('warning_logger')

IMAGE_MODEL = "gpt-image-1"
IMAGE_SIZE = "1024x1024"
MAX_PROMPT_LENGTH = 4000  # Max prompt length for DALL-E 3


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
    return truncated + "..."  # Fallback if no space found near end


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

        # 1. Primary Visual: DALL-E revised prompt or user inputs
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
    - The description must be a non-empty string and should also incorporate the overall \\'{image_style_description}\\'.
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
     - For the Title Page (Cover Image): If main characters are part of the cover\\\\'s theme, ensure their appearance is artistically integrated and clearly inspired by their \\\\'Canonical Visual Description\\\\'. The goal is recognizability and consistency with their established look. AVOID appending the full \\\\'Canonical Visual Description\\\\\' verbatim. The depiction should be natural within the artistic composition of the cover, avoiding a literal list of traits. Focus on key recognizable features that align with their canonical look, ensuring these features are consistent with those used in content pages.
  4. Apply Unified Styling: Ensure the ENTIRE "Image_description" (which is: [Scene from Page Text] + [Integrated Key Character Features]) reflects the overall \\\\\\'{image_style_description}\\\\\\''. All characters, objects, and background elements within the single image MUST be rendered in this exact same style. For example, you might append \\\\\\', {image_style_description} style\\\\\\' to the complete description.
  This step-by-step process (1. Scene from Page Text FIRST -> 2. Identify Characters -> 3. Incorporate Character Visuals as specified for page type -> 4. Apply Style) is vital for creating relevant images with consistent characters. The scene description from the page text MUST come first.
- The final output MUST be a single JSON object. This JSON object must have a top-level key \\'Title\\' (string) and a top-level key \\'Pages\\' (a list of page objects as described above, adhering to the image generation strategy). Do not include any text or explanations outside of this JSON object.
"""
    api_logger.debug(
        f"Prompt sent to ChatGPT for story generation (ratio: {word_to_picture_ratio}): {prompt[:500]}...")

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": "You are a creative story writer that outputs structured JSON. Adherence to all formatting and content constraints, including specified text density per page, is critical."},
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

        # Validate pages
        if not story_data["Pages"]:
            error_logger.error("ChatGPT response 'Pages' list is empty.")
            raise ValueError("ChatGPT response 'Pages' list cannot be empty.")

        # Validate Title Page (first page)
        title_page_data = story_data["Pages"][0]
        if not all(key in title_page_data for key in EXPECTED_PAGE_KEYS):
            error_logger.error(
                f"Title Page in ChatGPT response missing one of keys: {EXPECTED_PAGE_KEYS}. Page: {title_page_data}")
            raise ValueError(
                f"Title Page in ChatGPT response missing one of keys: {EXPECTED_PAGE_KEYS}")

        if title_page_data.get("Page_number") != "Title":
            error_logger.error(
                f"First page is not a Title Page. Expected Page_number 'Title', got '{title_page_data.get('Page_number')}'. Page: {title_page_data}")
            raise ValueError(
                "First page must be a Title Page with Page_number 'Title'.")

        title_page_text = title_page_data.get("Text")
        if not isinstance(title_page_text, str) or not title_page_text.strip():
            error_logger.error(
                f"Title Page: Text must be a non-empty string. Page: {title_page_data}")
            raise ValueError("Title Page: Text must be a non-empty string.")

        # Ensure the title in the title page matches the top-level title
        # If they differ, update the title page's text to match the main story title.
        main_story_title = story_data.get("Title")
        if main_story_title != title_page_text:
            app_logger.warning(  # Changed from error_logger.error to app_logger.warning
                f"Title Page text ('{title_page_text}') does not match top-level story title ('{main_story_title}'). Updating page text to match main title. Page: {title_page_data}")
            # Update the text of the title page in the story_data
            story_data["Pages"][0]["Text"] = main_story_title

        title_page_img_desc = title_page_data.get("Image_description")
        if not isinstance(title_page_img_desc, str) or not title_page_img_desc.strip():
            error_logger.error(
                f"Title Page: Image_description must be a non-empty string for the cover image. Page: {title_page_data}")
            raise ValueError(
                "Title Page: Image_description must be a non-empty string for the cover image.")

        # Validate Content Pages (remaining pages)
        # Ensure there's at least one content page if num_pages > 0, or handle num_pages = 0 case if that's valid (e.g. only title page)
        # The prompt implies num_pages refers to content pages.

        # This is the 'num_pages' from user input
        expected_num_content_pages = story_input['num_pages']

        # Adjusting for word_to_picture_ratio = PER_PARAGRAPH where num_pages means segments
        if word_to_picture_ratio == WordToPictureRatio.PER_PARAGRAPH.value:
            # In this case, num_pages from input is the number of "paragraph" objects,
            # each of which is a "page" in the output.
            pass  # expected_num_content_pages is already correct.

        # Subtract 1 for the title page
        actual_num_content_pages = len(story_data["Pages"]) - 1

        # This check might be too strict if AI is allowed to slightly deviate.
        # Consider if num_pages is a strict requirement or a guideline.
        # For now, let's assume it's a guideline for the AI, but we validate what we get.
        # if actual_num_content_pages != expected_num_content_pages and expected_num_content_pages > 0 :
        #     error_logger.warning(
        #         f"Warning: Number of content pages ({actual_num_content_pages}) does not match expected ({expected_num_content_pages}).")
        # Depending on strictness, this could be an error.

        # Validate Title Page (first page) - continued
        title_page_chars_in_scene = title_page_data.get("Characters_in_scene")
        if not isinstance(title_page_chars_in_scene, list):
            error_logger.error(
                f"Title Page: Characters_in_scene must be a list. Page: {title_page_data}")
            raise ValueError("Title Page: Characters_in_scene must be a list.")
        for char_name in title_page_chars_in_scene:
            if not isinstance(char_name, str):
                error_logger.error(
                    f"Title Page: Each item in Characters_in_scene must be a string. Found: {char_name}. Page: {title_page_data}")
                raise ValueError(
                    "Title Page: Each item in Characters_in_scene must be a string.")

        # Start from the second page (index 1)
        for i, page_data in enumerate(story_data["Pages"][1:], start=1):
            if not all(key in page_data for key in EXPECTED_PAGE_KEYS):
                error_logger.error(
                    f"Content Page (expected {i}) in ChatGPT response missing one of keys: {EXPECTED_PAGE_KEYS}. Page: {page_data}")
                raise ValueError(
                    f"Content Page (expected {i}) in ChatGPT response missing one of keys: {EXPECTED_PAGE_KEYS}")

            page_num = page_data.get("Page_number")
            img_desc = page_data.get("Image_description")
            page_text = page_data.get("Text")
            chars_in_scene = page_data.get("Characters_in_scene")  # New field

            if not isinstance(page_num, int):
                error_logger.error(
                    f"Content Page_number '{page_num}' (expected {i}) has invalid type '{type(page_num)}'. Expected int. Page: {page_data}")
                raise ValueError(
                    f"Content Page_number '{page_num}' must be an integer.")

            # Optional: Check for sequential page numbers for content pages.
            # The AI is asked for sequential numbers (1, 2, 3...).
            # If the AI returns page numbers like 1, 3, 4, this check would fail.
            # For now, we trust the AI was asked for sequential and validate type.
            # If strict sequence is needed:
            # if page_num != i:
            #     error_logger.error(f"Content Page_number '{page_num}' is not sequential. Expected {i}. Page: {page_data}")
            #     raise ValueError(f"Content Page_number '{page_num}' is not sequential. Expected {i}.")

            if not isinstance(page_text, str):
                error_logger.error(
                    f"Content Page {page_num}: Text has invalid type '{type(page_text)}'. Expected string. Page: {page_data}")
                raise ValueError(
                    f"Content Page {page_num}: Text must be a string.")
            # Add text length validation here if needed, based on text_density_instruction

            if not isinstance(chars_in_scene, list):  # Validation for new field
                error_logger.error(
                    f"Content Page {page_num}: Characters_in_scene must be a list. Page: {page_data}")
                raise ValueError(
                    f"Content Page {page_num}: Characters_in_scene must be a list.")
            for char_name in chars_in_scene:  # Validation for new field
                if not isinstance(char_name, str):
                    error_logger.error(
                        f"Content Page {page_num}: Each item in Characters_in_scene must be a string. Found: {char_name}. Page: {page_data}")
                    raise ValueError(
                        f"Content Page {page_num}: Each item in Characters_in_scene must be a string.")

            if not isinstance(img_desc, (str, type(None))):
                error_logger.error(
                    f"Content Page {page_num}: Image_description has invalid type '{type(img_desc)}'. Expected string or null. Page: {page_data}")
                raise ValueError(
                    f"Content Page {page_num}: Image_description must be a string or null.")

            # Ratio validation for content pages
            if word_to_picture_ratio == WordToPictureRatio.PER_PAGE.value or \
               word_to_picture_ratio == WordToPictureRatio.PER_PARAGRAPH.value:
                if not isinstance(img_desc, str) or not img_desc.strip():
                    error_logger.error(
                        f"Content Page {page_num}: Image_description must be a non-empty string for ratio '{word_to_picture_ratio}'. Got: '{img_desc}'. Page: {page_data}")
                    raise ValueError(
                        f"Content Page {page_num}: Image_description must be a non-empty string for ratio '{word_to_picture_ratio}'.")
            elif word_to_picture_ratio == WordToPictureRatio.PER_TWO_PAGES.value:
                # page_num is already validated as int for content pages
                if page_num % 2 == 0:  # Even page
                    if not isinstance(img_desc, str) or not img_desc.strip():
                        error_logger.error(
                            f"Content Page {page_num} (even): Image_description must be a non-empty string for ratio '{word_to_picture_ratio}'. Got: '{img_desc}'. Page: {page_data}")
                        raise ValueError(
                            f"Content Page {page_num} (even): Image_description must be a non-empty string for ratio '{word_to_picture_ratio}'.")
                else:  # Odd page (page_num % 2 != 0)
                    if img_desc is not None:
                        error_logger.error(
                            f"Content Page {page_num} (odd): Image_description must be null for ratio '{word_to_picture_ratio}'. Got: '{img_desc}'. Page: {page_data}")
                        raise ValueError(
                            f"Content Page {page_num} (odd): Image_description must be null for ratio '{word_to_picture_ratio}'.")

        api_logger.debug(
            "ChatGPT response structure and content validated successfully against word_to_picture_ratio and title page requirements.")
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


def generate_image(
    page_image_description: str,
    image_path: str,
    character_reference_image_paths: Optional[List[str]] = None,  # Modified
    character_name_for_reference: Optional[str] = None,
    # Changed from dall-e-3 to gpt-image-1
    model: str = "gpt-image-1",
    # Add openai_style parameter with default
    openai_style: Optional[str] = "vivid"
) -> Dict[str, Any]:
    """
    Generates an image using OpenAI's DALL-E API.
    Can use image editing if a reference image is provided, otherwise generates a new image.

    Args:
        page_image_description: The textual prompt for the image.
        image_path: The path where the generated image will be saved.
        character_reference_image_paths: Optional list of paths to reference images for character consistency.
        character_name_for_reference: Optional name of the character for whom reference is provided.
        model: The OpenAI model to use for image generation.
        openai_style: The style parameter for DALL-E ('vivid' or 'natural'). Defaults to 'vivid'.

    Returns:
        A dictionary containing the path to the saved image and the revised prompt (if any).
    """
    # Ensure the directory for the image_path exists
    os.makedirs(os.path.dirname(image_path), exist_ok=True)

    # Validate openai_style
    if openai_style not in ["vivid", "natural"]:
        app_logger.warning(
            f"Invalid openai_style '{openai_style}' provided. Defaulting to 'vivid'.")
        openai_style = "vivid"

    # Prepare reference images if provided
    valid_reference_files: List[Any] = []  # To hold open file objects
    opened_files_for_cleanup: List[Any] = []

    if character_reference_image_paths:
        for ref_path in character_reference_image_paths:
            if ref_path and os.path.exists(ref_path):
                try:
                    file_obj = open(ref_path, "rb")
                    valid_reference_files.append(file_obj)
                    opened_files_for_cleanup.append(file_obj)
                except Exception as e:
                    error_logger.warning(
                        f"Could not open reference file {ref_path}: {e}")
            else:
                error_logger.warning(
                    f"Reference image path {ref_path} does not exist or is None.")

    if valid_reference_files:
        try:
            primary_reference_file = valid_reference_files[0]
            num_references = len(valid_reference_files)

            instruction_prefix = (
                "IMPORTANT: Use the provided image as a strict visual reference for a key character in the scene. "
                "This character in the output image MUST visually match the reference, especially their face, hair, and build. "
                "This visual reference takes precedence over any conflicting appearance details in the text prompt below. "
                "Integrate this character (matching the reference) into the following scene, ensuring they fit the scene\\\'s style and actions. "
                "Scene details: "
            )

            if num_references > 1:
                other_refs_desc = f" Additionally, consider {num_references - 1} other guiding reference concepts implied by the context of this request."
                instruction_prefix = (
                    f"IMPORTANT: Use the primary provided image as a strict visual reference for a key character. "
                    f"This character in the output image MUST visually match this primary reference (face, hair, build).{other_refs_desc} "
                    f"This visual guidance takes precedence. Integrate this character into the following scene. Scene details: "
                )

            # The prompt for `images.edit` should be the `page_image_description` prefixed by the instruction.
            edit_prompt = instruction_prefix + page_image_description
            api_logger.debug(
                f"Attempting OpenAI Image API edit with prompt: {edit_prompt[:150]}... and {num_references} reference(s). Primary: {character_reference_image_paths[0] if character_reference_image_paths else 'None'}")

            response = client.images.edit(
                model=model,
                image=primary_reference_file,  # This is the opened file object
                prompt=edit_prompt,
                n=1,
                size="1024x1024",
                style=openai_style  # Pass openai_style to edit
                # response_format="b64_json" # Removed: gpt-image-1 always returns b64_json
            )
            if response.data and response.data[0].b64_json:
                image_data = base64.b64decode(response.data[0].b64_json)
                with open(image_path, 'wb') as f_out:
                    f_out.write(image_data)
                app_logger.info(
                    f"Image successfully generated using EDIT API and saved to {image_path}")
                revised_prompt_from_api = response.data[0].revised_prompt if hasattr(
                    response.data[0], 'revised_prompt') else edit_prompt
                gen_id_from_api = f"edit_{response.created}" if hasattr(
                    response, 'created') else f"edit_{uuid.uuid4().hex}"

                # No need to iterate and close here, finally block will handle it
                return {"image_path": image_path, "revised_prompt": revised_prompt_from_api, "gen_id": gen_id_from_api}
            else:
                error_logger.error(
                    "OpenAI Image API edit call did not return image data.")
                # Fall through to generate API

        except Exception as e:
            error_logger.error(
                f"OpenAI Image API edit call failed: {e}. Falling back to generate API.", exc_info=True)
            # Fall through to generate API
        finally:
            for f_obj in opened_files_for_cleanup:  # Ensure all opened reference files are closed
                # if hasattr(f_obj, 'closed') and not f_obj.closed: # Old condition
                if hasattr(f_obj, 'close') and callable(f_obj.close):  # New condition
                    try:
                        f_obj.close()
                    except Exception as close_e:
                        error_logger.warning(
                            f"Error closing reference file: {close_e}")
            opened_files_for_cleanup.clear()  # Clear the list after attempting to close

    # Fallback to generate API if no valid references, or if edit API failed
    app_logger.info(
        "Using OpenAI Image API generate (either no valid refs, or edit failed/skipped).")
    api_action_type_log = "generate"  # Define for logging in case of error
    prompt_to_log = page_image_description  # Define for logging in case of error
    try:
        # Ensure any files from a previous attempt (if edit block was skipped or failed early) are closed.
        # This is now redundant due to the finally block above, but kept for safety if logic changes.
        for f_obj in opened_files_for_cleanup:
            if hasattr(f_obj, 'closed') and not f_obj.closed:
                f_obj.close()
        opened_files_for_cleanup.clear()

        api_logger.debug(
            f"Attempting OpenAI Image API generate with prompt: {page_image_description[:150]}...")
        response = client.images.generate(
            model=model,  # Ensure model is passed here too
            prompt=page_image_description,
            size="1024x1024",
            n=1,
            style=openai_style  # Pass openai_style to generate
            # response_format parameter removed as it's not supported for gpt-image-1
        )

        if response.data and response.data[0] and response.data[0].b64_json:
            image_data = base64.b64decode(response.data[0].b64_json)
            with open(image_path, 'wb') as f_out:
                f_out.write(image_data)
            app_logger.info(
                f"Image successfully generated using GENERATE API and saved to {image_path}")

            # Determine revised_prompt, fallback to original prompt if not available
            current_revised_prompt = page_image_description
            if hasattr(response.data[0], 'revised_prompt') and response.data[0].revised_prompt:
                current_revised_prompt = response.data[0].revised_prompt

            # Determine gen_id, fallback to UUID if 'created' not available
            current_gen_id = f"gen_{uuid.uuid4().hex}"
            if hasattr(response, 'created') and response.created:
                current_gen_id = f"gen_{response.created}"

            return {"image_path": image_path, "revised_prompt": current_revised_prompt, "gen_id": current_gen_id}
        else:
            # This case means the API call succeeded (no exception) but the response format is unexpected.
            error_logger.error(
                f"OpenAI Image API generate call for prompt '{prompt_to_log[:100]}...' succeeded but returned no image data or unexpected response structure. Response: {response}")
            raise ValueError(
                "OpenAI Image API generate call returned no image data.")

    except openai.BadRequestError as e:
        error_details = e.response.json() if e.response else {
            "error": {"message": str(e)}}
        error_message_detail = error_details.get(
            "error", {}).get("message", "Unknown BadRequestError")
        error_code_detail = error_details.get("error", {}).get("code")

        # Determine api_action_type_log if not already set (e.g. if error happened in edit block)
        # This specific except block is for the 'generate' part, so api_action_type_log is 'generate'
        # However, to be robust, if we were to combine error handling, we'd need a more dynamic way.
        # For now, it's correctly 'generate' as per the flow.

        if error_code_detail == 'moderation_blocked' or "safety system" in error_message_detail:
            # Use prompt_to_log which is page_image_description for the generate block
            error_logger.error(
                f"OpenAI Image API call failed due to moderation/safety system. ACTION: {api_action_type_log}. FULL PROMPT: {prompt_to_log}")
            error_logger.error(
                f"OpenAI Image API {api_action_type_log} call failed: {error_message_detail} (Code: {error_code_detail})", exc_info=True)
        else:
            error_logger.error(
                f"OpenAI Image API {api_action_type_log} call failed: {error_message_detail} (Code: {error_code_detail})", exc_info=True)
        raise  # Re-raise the exception
    except openai.OpenAIError as e:
        error_logger.error(
            f"OpenAI API Error during image generation: {e}", exc_info=True)
        raise
    except Exception as e:
        error_logger.error(
            f"An unexpected error occurred while generating image: {e}", exc_info=True)
        raise


def generate_character_reference_image(
    character: CharacterDetail,
    user_id: int,
    story_id: int,
    image_style_enum: ImageStyle,  # This is the application's ImageStyle enum
    # To pass dynamic list item's additional_config
    image_styles_config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    app_logger.info(  # ADDED THIS ENTRY LOG
        f"Attempting to generate reference image for character: {character.name} (User: {user_id}, Story: {story_id}, Style Enum: {image_style_enum})")

    # Determine the OpenAI style to use
    # Default to 'vivid'
    final_openai_style = "vivid"
    if image_styles_config and isinstance(image_styles_config, dict):
        # Look for 'openai_style' in the additional_config of the 'image_styles' item
        configured_style = image_styles_config.get("openai_style")
        if configured_style in ["vivid", "natural"]:
            final_openai_style = configured_style
            app_logger.info(
                f"Using configured openai_style '{final_openai_style}' for character reference image from image_styles config.")
        elif configured_style:
            app_logger.warning(
                f"Invalid openai_style '{configured_style}' in image_styles config. Defaulting to 'vivid'.")
    else:
        app_logger.info(
            f"No valid image_styles_config provided or 'openai_style' not found. Defaulting to 'vivid' for character reference image.")

    # Use "the character" if name is empty or whitespace
    char_name_for_prompt = character.name if character.name and character.name.strip(
    ) else "the character"

    prompt_parts = [
        f"Generate a character sheet for {char_name_for_prompt} showing the character from multiple consistent angles (e.g., front, side, three-quarter view), including a full body view.",
        "It is crucial that all views depict the exact same character consistently."
    ]  # New prompt start for multiple angles
    if character.physical_appearance:
        prompt_parts.append(
            f"Physical Appearance: {character.physical_appearance}.")
    if character.clothing_style:
        prompt_parts.append(f"Clothing Style: {character.clothing_style}.")
    if character.key_traits:
        prompt_parts.append(f"Key Traits: {character.key_traits}.")
    if character.age:
        prompt_parts.append(f"Age: {character.age}.")
    if character.gender:
        prompt_parts.append(f"Gender: {character.gender}.")

    # Add image style to the prompt
    style_value = image_style_enum.value if hasattr(
        image_style_enum, 'value') else str(image_style_enum)
    if style_value != "Default":  # Assuming "Default" is a valid enum member string value
        prompt_parts.append(f"Style: {style_value}.")
    else:
        # Default style description
        prompt_parts.append("Style: Clear, vibrant, detailed illustration.")

    # prompt_parts.append(
    #     "The character should be clearly visible, facing forward or slightly angled, on a simple or neutral background to emphasize their design.") # Old instruction
    prompt_parts.append(
        "The character should be clearly visible on a simple or neutral background to emphasize their design for the character sheet."
    )  # New instruction

    image_prompt = _truncate_prompt(" ".join(filter(None, prompt_parts)))
    api_logger.debug(
        f"Image model prompt for character {character.name}: {image_prompt}")

    # Define image save paths
    # Path relative to 'data/' for storing in DB and for frontend access
    # e.g., images/user_1/story_123/references/char_Luna_ref_abc123.png
    char_filename_safe_name = "".join(
        c if c.isalnum() else '_' for c in character.name)
    unique_suffix = uuid.uuid4().hex[:6]
    char_image_filename = f"char_{char_filename_safe_name}_ref_{unique_suffix}.png"

    user_images_base_path_for_db = f"images/user_{user_id}"
    story_folder_name_for_db = f"story_{story_id}"
    char_ref_image_subfolder_name = "references"

    _db_path_prefix = os.path.join(
        user_images_base_path_for_db, story_folder_name_for_db, char_ref_image_subfolder_name)
    _save_directory_on_disk = os.path.join("data", _db_path_prefix)

    os.makedirs(_save_directory_on_disk, exist_ok=True)
    image_save_path_on_disk = os.path.join(
        _save_directory_on_disk, char_image_filename)
    image_path_for_db = os.path.join(_db_path_prefix, char_image_filename)

    # ADDED/ENHANCED LOG
    app_logger.debug(
        f"generate_character_reference_image: About to call generate_image for character '{character.name}'. Disk path: {image_save_path_on_disk}. Prompt: '{image_prompt[:100]}...'")

    try:
        image_generation_result = generate_image(
            page_image_description=image_prompt,
            image_path=image_save_path_on_disk,
            character_reference_image_paths=None,
            character_name_for_reference=None,  # Explicitly None for character ref generation
        )

        updated_character_dict = character.model_dump(exclude_none=True)
        updated_character_dict["reference_image_path"] = image_path_for_db
        updated_character_dict["reference_image_revised_prompt"] = image_generation_result.get(
            "revised_prompt")
        updated_character_dict["reference_image_gen_id"] = image_generation_result.get(
            "gen_id")

        app_logger.info(  # ENSURED THIS LOG IS PRESENT
            f"Reference image for {character.name} generated and saved to {image_save_path_on_disk}. DB path: {image_path_for_db}")
        return updated_character_dict

    except Exception as e:
        error_logger.error(
            f"generate_character_reference_image: Exception caught for char '{character.name}'. Type: {type(e).__name__}, Msg: {str(e)}. Failing prompt was: {image_prompt}", exc_info=True)
        # Always return the model dump as per test expectation
        return character.model_dump(exclude_none=True)

# Changed character_name to character_details
# async def generate_image_description_from_image(image_path: str, character_details: CharacterDetail) -> str:
#     """
#     Uses GPT-4 Vision to generate a detailed textual description of a character
#     based on their reference image and initial details.
#     """
#     api_logger.info(
#         f"Generating detailed visual description for character: {character_details.name} from image: {image_path}")
#
#     try:
#         # Ensure the image_path is an absolute path or correctly relative to where the script runs
#         # For local files, it might need to be prefixed if not absolute.
#         # Assuming image_path is accessible.
#         full_image_path = os.path.abspath(image_path)
#         if not os.path.exists(full_image_path):
#             error_logger.error(
#                 f"Image file not found at {full_image_path} for GPT-4 Vision processing.")
#             # Fallback or raise error
#             return "Error: Image file not found for description generation."
#
#         with open(full_image_path, "rb") as image_file:
#             base64_image = base64.b64encode(image_file.read()).decode('utf-8')
#
#         headers = {
#             "Content-Type": "application/json",
#             "Authorization": f"Bearer {OPENAI_API_KEY}"
#         }
#
#         # Constructing a more detailed prompt for GPT-4 Vision
#         vision_prompt_parts = [
#             f"Analyze the provided image, which is a character reference for '{character_details.name}'.",
#             "Focus on extracting and describing concrete visual details suitable for maintaining consistency in future image generations.",
#             "Describe the character's key physical features, clothing, any notable accessories, and overall style as depicted in the image.",
#             "Do not invent details not present in the image. Be objective and descriptive.",
#             "The goal is to create a textual description that can be used by an image generation AI (like DALL-E) to recreate this character accurately."
#         ]
#         # Add user-provided details as context, if available
#         if character_details.physical_appearance:  # Corrected from initial_character_details
#             vision_prompt_parts.append(
#                 # Corrected
#                 f"User-provided physical appearance for context: {character_details.physical_appearance}")
#         if character_details.clothing_style:  # Corrected
#             vision_prompt_parts.append(
#                 # Corrected
#                 f"User-provided clothing style for context: {character_details.clothing_style}")
#         if character_details.key_traits:  # Corrected
#             vision_prompt_parts.append(
#                 # Corrected
#                 f"User-provided key traits for context: {character_details.key_traits}")
#
#         vision_prompt = " ".join(vision_prompt_parts)
#
#         payload = {
#             "model": "gpt-4-vision-preview",
#             "messages": [
#                 {
#                     "role": "user",
#                     "content": [
#                         {
#                             "type": "text",
#                             "text": vision_prompt
#                         },
#                         {
#                             "type": "image_url",
#                             "image_url": {
#                                 "url": f"data:image/png;base64,{base64_image}"
#                             }
#                         }
#                     ]
#                 }
#             ],
#             "max_tokens": 300
#         }
#
#         api_logger.debug(
#             f"Sending request to GPT-4 Vision for character {character_details.name}. Prompt: {vision_prompt[:100]}...")
#         response = requests.post(
#             "https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
#         response.raise_for_status()  # Raise an exception for bad status codes
#
#         description_data = response.json()
#         generated_description = description_data['choices'][0]['message']['content']
#
#         api_logger.info(
#             f"Successfully generated visual description for {character_details.name} using GPT-4 Vision.")
#         api_logger.debug(
#             f"Generated description for {character_details.name}: {generated_description}")
#
#         return generated_description
#
#     except requests.exceptions.RequestException as e:
#         error_logger.error(
#             f"API request failed during GPT-4 Vision processing for {character_details.name}: {e}", exc_info=True)
#         # Fallback description
#         return f"Could not generate detailed visual description due to API error. Basic details: Name {character_details.name}."
#     except FileNotFoundError as e:
#         error_logger.error(
#             f"Image file not found for GPT-4 Vision processing of {character_details.name}: {e}", exc_info=True)
#         return f"Could not generate detailed visual description as image was not found. Basic details: Name {character_details.name}."
#     except Exception as e:
#         error_logger.error(
#             f"An unexpected error occurred during GPT-4 Vision processing for {character_details.name}: {e}", exc_info=True)
#         # Fallback description
#         return f"Could not generate detailed visual description due to an unexpected error. Basic details: Name {character_details.name}."


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
        "word_to_picture_ratio": "PER_TWO_PAGES",
        "text_density": "Concise (~30-50 words)"  # Added for completeness
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
                    image_gen_details = generate_image(  # Changed function name
                        page_image_description=page_prompt,  # Pass prompt as page_image_description
                        image_path=image_file_path,
                        character_reference_image_paths=None,  # Add new parameter for testing
                        character_name_for_reference=None  # Explicitly None for this test case
                    )
                    print(
                        f"Successfully generated and saved image to: {image_gen_details['image_path']}")
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
