"""OpenAI smoke test script (manual).

Purpose
-------
Validate that our configured OpenAI models work end-to-end against the real API:
- Story generation (Chat Completions or Responses API) and JSON contract
- Image generation (`images.generate`)
- Image edit/reference flow (`images.edit`) using a tiny local PNG

This script is meant for staging / manual verification and is not part of the
pytest suite.

Usage
-----
1) Ensure env vars are set (recommended via repo root .env):
   - OPENAI_API_KEY=...
   - TEXT_MODEL=gpt-5-mini
   - IMAGE_MODEL=gpt-image-1.5
   - USE_OPENAI_RESPONSES_API=true   # enable Responses path for staging
    - SMOKE_EDIT_IMAGE_PATH=/absolute/or/relative/path/to/real_input_image.png

2) Run:
   python scripts/smoke_test_openai.py

Exit codes
----------
0: all checks passed
1: at least one check failed
"""

import os
import sys
from typing import Any, Dict

from dotenv import load_dotenv


# Prefer loading the repository root .env for local/staging runs.
_HERE = os.path.dirname(__file__)
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

_REPO_ROOT_ENV = os.path.abspath(os.path.join(_HERE, "..", ".env"))
if os.path.exists(_REPO_ROOT_ENV):
    load_dotenv(dotenv_path=_REPO_ROOT_ENV, override=False)
else:
    load_dotenv(override=False)

# Optional: allow a scripts/.env for ad-hoc local overrides.
_LOCAL_ENV = os.path.join(_HERE, ".env")
if os.path.exists(_LOCAL_ENV):
    load_dotenv(dotenv_path=_LOCAL_ENV, override=False)


def _require_env(name: str) -> str:
    """Return env var value or raise a clear error."""

    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _print_kv(key: str, value: str) -> None:
    print(f"- {key}: {value}", flush=True)


def main() -> int:
    """Run smoke checks against OpenAI and return a process exit code."""

    print("Starting OpenAI smoke test...", flush=True)

    _require_env("OPENAI_API_KEY")

    # Import lazily so env is present first.
    from backend.ai_services import generate_image, generate_story_from_chatgpt
    from backend.tests.test_ai_story_json_contract import assert_ai_story_json_contract

    text_model = os.getenv("TEXT_MODEL", "")
    image_model = os.getenv("IMAGE_MODEL", "")
    use_responses = os.getenv("USE_OPENAI_RESPONSES_API", "").lower() in (
        "1",
        "true",
        "yes",
    )

    print("OpenAI smoke test configuration", flush=True)
    _print_kv("TEXT_MODEL", text_model or "(default from settings)")
    _print_kv("IMAGE_MODEL", image_model or "(default from settings)")
    _print_kv("USE_OPENAI_RESPONSES_API", str(use_responses))

    failures: list[str] = []

    # 1) Story generation + contract.
    try:
        print("\n[1/3] Story generation + contract", flush=True)
        story_input: Dict[str, Any] = {
            "title": "Smoke Test Story",
            "genre": "Fantasy",
            "story_outline": "A short, calm quest to verify integrations.",
            "main_characters": [
                {
                    "name": "Mira",
                    "physical_appearance": "a young adventurer with a red scarf",
                    "clothing_style": "simple travel clothes",
                    "key_traits": "curious and brave",
                }
            ],
            "num_pages": 1,
            "image_style": "Default",
            "word_to_picture_ratio": "One image per page",
            "text_density": "Concise (~30-50 words)",
        }
        story = generate_story_from_chatgpt(story_input)
        assert_ai_story_json_contract(story)
        print("OK: story contract validated", flush=True)
    except Exception as exc:  # noqa: BLE001 - manual script
        failures.append(f"Story generation failed: {exc}")
        print(f"FAIL: story generation/contract: {exc}", flush=True)

    # 2) Image generation.
    try:
        print("\n[2/3] Image generation (images.generate)", flush=True)
        img_bytes = generate_image(
            prompt="A simple test illustration of a lighthouse on a hill.",
            reference_image_paths=None,
        )
        if not img_bytes:
            raise RuntimeError("generate_image returned None")
        print(f"OK: generated image bytes: {len(img_bytes)}", flush=True)
    except Exception as exc:  # noqa: BLE001 - manual script
        failures.append(f"Image generation failed: {exc}")
        print(f"FAIL: image generation: {exc}", flush=True)

    # 3) Image edit/reference flow.
    try:
        print("\n[3/3] Image edit/reference (images.edit)", flush=True)
        edit_image_path = os.getenv("SMOKE_EDIT_IMAGE_PATH")
        if not edit_image_path:
            raise RuntimeError(
                "Set SMOKE_EDIT_IMAGE_PATH to a real local PNG/JPG/WebP file to test edits."
            )

        edit_image_path = os.path.expanduser(edit_image_path)
        if not os.path.isabs(edit_image_path):
            edit_image_path = os.path.abspath(edit_image_path)
        if not os.path.exists(edit_image_path):
            raise RuntimeError(
                f"SMOKE_EDIT_IMAGE_PATH not found: {edit_image_path}")

        edited_bytes = generate_image(
            prompt=(
                "Create a 3-angle character reference sheet (front, side, back) "
                "based on the input image."
            ),
            reference_image_paths=[edit_image_path],
        )
        if not edited_bytes:
            raise RuntimeError("generate_image returned None for edit")
        print(f"OK: edited image bytes: {len(edited_bytes)}", flush=True)

    except Exception as exc:  # noqa: BLE001 - manual script
        failures.append(f"Image edit failed: {exc}")
        print(f"FAIL: image edit/reference: {exc}", flush=True)
        print(
            "Hint: if this fails for gpt-image-1.5, consider falling back to "
            "gpt-image-1 for edits only.", flush=True)

    if failures:
        print("\nSummary: FAIL", flush=True)
        for item in failures:
            print(f"- {item}", flush=True)
        return 1

    print("\nSummary: OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
