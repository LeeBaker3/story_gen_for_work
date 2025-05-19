import openai
from openai import OpenAI
import os
import requests
import json
from dotenv import load_dotenv
from typing import List, Dict, Any
import base64  # Added for image encoding

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

        if reference_image_revised_prompt:
            details_for_prompt.append(
                f"  - Primary Visual Reference (from DALL-E revised_prompt): '{reference_image_revised_prompt}'. This is the MOST IMPORTANT visual description. If {char_name} is in the scene, this ENTIRE description MUST be appended VERBATIM to the Image_description.")
            if user_physical_appearance:
                details_for_prompt.append(
                    f"  - User-Defined Physical Appearance (Supplementary): '{user_physical_appearance}'. Use this to complement the Primary Visual Reference if consistent.")
            if user_clothing_style:
                details_for_prompt.append(
                    f"  - User-Defined Clothing Style (Supplementary): '{user_clothing_style}'. Use this to complement the Primary Visual Reference if consistent.")
        else:  # No revised_prompt, fall back to user descriptions
            if user_physical_appearance:
                details_for_prompt.append(
                    f"  - User-Defined Physical Appearance: '{user_physical_appearance}'. This description MUST be included VERBATIM in the image prompt if {char_name} is present.")
            if user_clothing_style:
                details_for_prompt.append(
                    f"  - User-Defined Clothing Style: '{user_clothing_style}'. This description MUST be included VERBATIM in the image prompt if {char_name} is present.")

        if ai_generated_desc_from_ref:  # This is the AI's text description of the reference image
            details_for_prompt.append(
                f"  - AI-Generated Detailed Visuals (from reference image analysis): '{ai_generated_desc_from_ref}'. This provides supplementary details. If a Primary Visual Reference (revised_prompt) exists, this is secondary. Otherwise, if no other specific descriptions are present, this can be used VERBATIM if {char_name} is present.")

        if not reference_image_revised_prompt and not user_physical_appearance and not user_clothing_style and not ai_generated_desc_from_ref:
            details_for_prompt.append(
                f"  - Note: No specific visual appearance, clothing, or AI-generated details were provided for {char_name}. Use story context if they appear in images.")

        if user_key_traits:
            details_for_prompt.append(
                f"  - Other Distinctive User-Defined Visual Traits: '{user_key_traits}'. These should be incorporated if compatible and additive to the primary descriptions.")

        if char_data.get('age'):
            details_for_prompt.append(f"  - Age Context: {char_data['age']}")
        if char_data.get('gender'):
            details_for_prompt.append(
                f"  - Gender Context: {char_data['gender']}")

        if char_data.get('reference_image_path'):
            details_for_prompt.append(
                f"  - Reference Image Note: This character has a reference image. The descriptions above are derived from user inputs and this reference. Visuals MUST align.")

        if len(details_for_prompt) > 1:
            character_visual_instructions.append("\n".join(details_for_prompt))

    detailed_characters_description = "\n\n".join(
        character_visual_instructions)

    # Prepare story title information for the prompt
    user_provided_title = story_input.get('title')
    title_instruction = ""
    if user_provided_title and user_provided_title.strip():
        title_instruction = f"- The user has provided the following title for the story: '{user_provided_title}'. This title MUST be used for the story."
    else:
        title_instruction = "- The user has NOT provided a story title. You MUST generate a suitable and creative title for the story based on the other inputs."

    prompt = f"""Please generate a story that meets ALL the following requirements with EXTREME precision. The story will be of a specific length. Each segment of the story will need an image description (or null if specified by the ratio) that is appropriate for use as a prompt to generate an AI-created image.

CRITICAL REQUIREMENT - TEXT DENSITY PER PAGE:
- Adhere ABSOLUTELY STRICTLY to the specified text density: {text_density_instruction}.
- This means the 'Text' field for EACH page object in the JSON output MUST conform to the word count defined in this instruction. This is a primary constraint.

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
- The story should start with a title.
- CRUCIAL FOR IMAGE DESCRIPTION AND VISUAL CONSISTENCY:
  For every page/segment that requires an image (i.e., "Image_description" is not null), construct the "Image_description" using the following STRICT, SEQUENTIAL process:
  1. START WITH SCENE FROM PAGE TEXT: MANDATORY FIRST STEP. Create a vivid description of the scene, including specific actions, character interactions, key objects, and the environment. This description MUST be based DIRECTLY and EXCLUSIVELY on the "Text" of that specific page/segment. This forms the foundational part of the "Image_description". DO NOT skip or minimize this step.
  2. Identify Characters in Scene: After describing the scene from the text, determine which of the Main Characters (listed above) are present or clearly implied in this scene.
  3. Append Character Visuals Verbatim: For EACH identified Main Character present in the scene, sequentially append their visual details AFTER the scene description from step 1. Follow this hierarchy for appending details:
     a. Check for a 'Primary Visual Reference (from DALL-E revised_prompt)'. If it exists for the character, append this ENTIRE description VERBATIM. This is the highest priority visual data.
     b. If no 'Primary Visual Reference' exists, then check for 'User-Defined Physical Appearance'. If present, append it VERBATIM.
     c. If no 'Primary Visual Reference' exists, then check for 'User-Defined Clothing Style'. If present, append it VERBATIM.
     d. If a 'Primary Visual Reference' exists, 'User-Defined Physical Appearance' and 'User-Defined Clothing Style' can be appended VERBATIM as *supplementary* details if they are consistent and add value beyond the revised_prompt.
     e. Check for 'AI-Generated Detailed Visuals (from reference image analysis)'. If a 'Primary Visual Reference' (revised_prompt) exists, this is secondary. If no revised_prompt or user-defined descriptions are primary, this can be appended VERBATIM.
     f. Check for 'Other Distinctive User-Defined Visual Traits'. Append these VERBATIM if they are compatible and additive to the already appended descriptions.
     The chosen visual descriptions MUST NOT be summarized, shortened, rephrased, or altered in any way. They are to be treated as fixed blocks of text to be appended sequentially for each character, AFTER the initial scene description derived from the page text.
  4. Apply Unified Styling: Ensure the ENTIRE "Image_description" (which is: [Scene from Page Text] + [Appended Character Visuals]) reflects the overall '{image_style_description}'. All characters, objects, and background elements within the single image MUST be rendered in this exact same style. For example, you might append ', {image_style_description} style' to the complete description.
  This step-by-step process (1. Scene from Page Text FIRST -> 2. Identify Characters -> 3. Append Verbatim Character Details Sequentially -> 4. Apply Style) is vital for creating relevant images with consistent characters. The scene description from the page text MUST come first.
- The final output MUST be a single JSON object. This JSON object must have a top-level key 'Title' (string) and a top-level key 'Pages' (a list of page objects as described above, adhering to the image generation strategy). Do not include any text or explanations outside of this JSON object.
"""
    api_logger.debug(
        f"Prompt sent to ChatGPT for story generation (ratio: {word_to_picture_ratio}): {prompt[:500]}...")

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
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


def generate_image_from_dalle(prompt: str, image_path: str) -> dict:
    """
    Generates an image using DALL·E 3 based on a prompt and saves it locally.
    Returns a dictionary containing the path to the saved image, the revised_prompt, and the gen_id.
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
        image_data = response.data[0]
        image_url = image_data.url
        revised_prompt = image_data.revised_prompt
        # The DALL-E API doesn't explicitly return a 'seed' or 'gen_id' in this response format.
        # The 'revised_prompt' is the most consistent piece of information we can get back
        # that is related to the generation. We will use the revised_prompt itself or a hash of it
        # if a seed-like behavior is needed, or rely on the user to input a seed if the API changes.
        # For now, we'll log that gen_id is not directly available from this endpoint.
        api_logger.info(f"DALL-E returned image URL: {image_url}")
        api_logger.info(f"DALL-E revised_prompt: {revised_prompt}")
        api_logger.info(
            "Note: gen_id is not directly available in the standard DALL-E API response for 'url' format.")

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
        # gen_id is None for now
        return {"image_path": image_path, "revised_prompt": revised_prompt, "gen_id": None}
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


def generate_character_reference_image(character: CharacterDetail, base_image_path: str) -> dict:
    """
    Generates a character reference image using DALL·E 3 and saves it.

    Args:
        character: A CharacterDetail object containing character attributes.
        base_image_path: The base directory path to save the image (e.g., data/images/story_id/).

    Returns:
        A dictionary containing the path to the saved character reference image,
        the revised_prompt, and gen_id (currently None).
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
        # generate_image_from_dalle now returns a dict
        generation_result = generate_image_from_dalle(prompt, full_image_path)
        saved_image_path = generation_result["image_path"]
        revised_prompt = generation_result["revised_prompt"]
        gen_id = generation_result["gen_id"]  # Will be None for now

        api_logger.info(
            f"Successfully generated and saved reference image for {character.name} at {saved_image_path}")
        return {"image_path": saved_image_path, "revised_prompt": revised_prompt, "gen_id": gen_id}
    except Exception as e:
        error_logger.error(
            f"Failed to generate reference image for character {character.name}: {e}", exc_info=True)
        # Depending on desired error handling, could return None or re-raise
        # For now, re-raising to make it visible during development
        raise


def generate_detailed_description_from_image(image_path: str, character_name: str, initial_character_details: CharacterDetail) -> str:
    """
    Uses a vision-capable model (like GPT-4 Vision) to generate a detailed textual description
    of a character based on a reference image and initial details.

    Args:
        image_path: Path to the character's reference image.
        character_name: Name of the character.
        initial_character_details: The initial CharacterDetail object provided by the user.

    Returns:
        A detailed textual description of the character's visual appearance from the image.
    """
    api_logger.info(
        f"Generating detailed visual description for {character_name} from image: {image_path}")

    try:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        error_logger.error(
            f"Reference image file not found at {image_path} for character {character_name}.")
        raise ValueError(
            f"Reference image file not found for {character_name} at {image_path}.")
    except Exception as e:
        error_logger.error(
            f"Could not read or encode image {image_path} for {character_name}: {e}")
        raise ValueError(f"Could not process image file for {character_name}.")

    user_provided_details_parts = []
    if initial_character_details.physical_appearance:
        user_provided_details_parts.append(
            f"User-provided physical appearance: {initial_character_details.physical_appearance}")
    if initial_character_details.clothing_style:
        user_provided_details_parts.append(
            f"User-provided clothing style: {initial_character_details.clothing_style}")
    if initial_character_details.key_traits:
        user_provided_details_parts.append(
            f"User-provided key traits: {initial_character_details.key_traits}")

    user_details_prompt_segment = ". ".join(user_provided_details_parts)
    if not user_details_prompt_segment.strip():
        user_details_prompt_segment = "No specific user-provided visual details beyond the image itself were given for context."
    else:
        user_details_prompt_segment = f"For context, here are some details the user initially provided for this character: {user_details_prompt_segment}."

    prompt_messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"""Analyze the provided image of the character named '{character_name}'.
Based *only* on what is visually apparent in this image, provide a very detailed and specific textual description of their appearance.
Focus on concrete visual elements like: hair style and color, eye color and shape, facial features (nose, mouth, jawline, etc.), skin tone, build/physique, exact clothing items and their colors/styles/textures, accessories, and any unique distinguishing marks or features visible.
This description will be used to help an image generation AI recreate this character consistently in subsequent images. Be as objective and descriptive as possible.
{user_details_prompt_segment}
Your output should be a single, coherent paragraph focusing *only* on the character's visual attributes as seen in the image. Do not describe the background, pose, or image composition. Do not add any preamble like 'Okay, here is the description...'. Just provide the description itself."""
                },
                {
                    "type": "image_url",
                    "image_url": {
                        # Assuming PNG, adjust if other formats are possible
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                }
            ]
        }
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",  # Updated model
            messages=prompt_messages,
            max_tokens=600  # Increased slightly for potentially more detailed descriptions
        )
        description = response.choices[0].message.content.strip()
        api_logger.info(
            f"Successfully generated detailed description for {character_name} from reference image.")
        api_logger.debug(
            f"Generated description for {character_name}: {description}")
        return description
    except openai.APIError as e:
        error_logger.error(
            f"OpenAI API Error during vision description generation for {character_name}: {e}", exc_info=True)
        # Consider returning a specific error message or None
        raise ValueError(
            f"AI vision service failed to generate description for {character_name}.")
    except Exception as e:
        error_logger.error(
            f"Unexpected error during vision description generation for {character_name}: {e}", exc_info=True)
        raise ValueError(
            f"An unexpected error occurred while generating vision description for {character_name}.")


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
