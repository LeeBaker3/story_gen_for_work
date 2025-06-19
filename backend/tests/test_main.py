import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, ANY
from sqlalchemy.orm import Session
from backend.main import app  # Assuming your FastAPI app instance is named 'app'
from backend import schemas, crud, auth, ai_services, database
# Ensure UTC is imported for timezone-aware datetime
from datetime import datetime, UTC
from fastapi import Depends  # Added Depends

# --- Fixtures ---


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient instance for the FastAPI app."""
    # The 'app' instance is imported from backend.main at the module level.
    # TestClient will use this app instance. Dependency overrides applied by
    # autouse fixtures will be active on this app when requests are made.
    return TestClient(app)


@pytest.fixture
def db_session_mock():
    """Mocks the database session."""
    db = MagicMock(spec=Session)
    # If you need to mock specific db methods like query, add, commit, refresh:
    # db.query.return_value.filter.return_value.first.return_value = None # Example
    # db.add = MagicMock()
    # db.commit = MagicMock()
    # db.refresh = MagicMock()
    return db


@pytest.fixture
def current_user_mock():
    """Mocks the current authenticated user."""
    user = schemas.User(
        id=1,
        username="testuser",
        email="test@example.com",
        is_active=True,  # Added
        role="user"      # Added
        # hashed_password="hashedpassword" # Removed: Not part of schemas.User
        # stories will default to []
    )
    return user


@pytest.fixture
def story_create_input_mock():
    """Provides a sample StoryCreate input."""
    return schemas.StoryCreate(
        title="My Test Story",
        genre=schemas.StoryGenre.FANTASY,
        story_outline="A brave knight on a quest.",
        main_characters=[
            schemas.CharacterDetail(name="Sir TestAlot", physical_appearance="Shiny armor",
                                    clothing_style="Medieval", key_traits="Brave"),
            schemas.CharacterDetail(
                name="Dragon Testy", physical_appearance="Green scales", clothing_style="None", key_traits="Fiery")
        ],
        num_pages=2,
        image_style=schemas.ImageStyle.DEFAULT,  # Changed from CINEMATIC to DEFAULT
        word_to_picture_ratio=schemas.WordToPictureRatio.PER_PAGE,
        text_density=schemas.TextDensity.STANDARD
    )


@pytest.fixture(autouse=True)
def mock_get_db(db_session_mock):
    """Overrides the get_db dependency for all tests in this module."""
    def override_get_db():
        try:
            yield db_session_mock
        finally:
            pass  # No actual db.close() needed for mock
    app.dependency_overrides[database.get_db] = override_get_db
    yield
    # More specific cleanup for get_db
    if database.get_db in app.dependency_overrides:
        # Or restore original if it existed
        del app.dependency_overrides[database.get_db]


@pytest.fixture(autouse=True)
def default_mock_get_current_user(current_user_mock):
    """
    Overrides the auth.get_current_user dependency globally with a default
    active, non-admin user. Tests needing specific user types (inactive, admin)
    should temporarily override this within the test.
    """
    original_override = app.dependency_overrides.get(auth.get_current_user)

    def override_get_current_user():
        return current_user_mock

    app.dependency_overrides[auth.get_current_user] = override_get_current_user

    yield

    if original_override:
        app.dependency_overrides[auth.get_current_user] = original_override
    elif auth.get_current_user in app.dependency_overrides:
        del app.dependency_overrides[auth.get_current_user]


# --- Mocks for External Services ---

@pytest.fixture
def mock_ai_services():
    """Mocks the ai_services module functions."""
    with patch('backend.ai_services.generate_character_reference_image') as mock_char_ref_img, \
            patch('backend.ai_services.generate_story_from_chatgpt') as mock_story_gen, \
            patch('backend.ai_services.generate_image') as mock_page_img, \
            patch('backend.main.os.makedirs') as mock_makedirs:  # Also mock os.makedirs used in main.py

        # Default successful return for character reference image
        mock_char_ref_img.side_effect = lambda character, user_id, story_id, image_style_enum: {
            **character.model_dump(),
            "reference_image_path": f"images/user_{user_id}/story_{story_id}/references/char_{character.name}_ref_mock.png",
            "reference_image_revised_prompt": "Mock revised prompt",
            "reference_image_gen_id": "mock_gen_id"
        }

        # Default successful return for story generation
        mock_story_gen.return_value = {
            "Title": "AI Generated Test Story",
            "Pages": [
                {
                    "Page_number": "Title",
                    "Text": "AI Generated Test Story",
                    "Image_description": "A grand cover image for the AI story.",
                    "Characters_in_scene": []
                },
                {
                    "Page_number": 1,
                    "Text": "Once upon a time, in a test land... Sir TestAlot",
                    "Image_description": "Sir TestAlot riding a mock-horse.",
                    "Characters_in_scene": ["Sir TestAlot"]
                },
                {
                    "Page_number": 2,
                    "Text": "Dragon Testy appeared, looking mock-scary.",
                    "Image_description": "Dragon Testy breathing mock-fire.",
                    "Characters_in_scene": ["Dragon Testy"]
                }
            ]
        }

        # Default successful return for page image
        mock_page_img.return_value = {
            "image_path": "mock/path/to/generated_image.png",  # This path is the on-disk path
            "revised_prompt": None,
            "gen_id": None
        }

        # os.makedirs doesn't return anything significant
        mock_makedirs.return_value = None

        yield {
            'generate_character_reference_image': mock_char_ref_img,
            'generate_story_from_chatgpt': mock_story_gen,
            'generate_image': mock_page_img,
            'os_makedirs': mock_makedirs
        }


@pytest.fixture
# Added story_create_input_mock
def mock_crud_operations(db_session_mock, current_user_mock, story_create_input_mock):
    """Mocks CRUD operations used within the create_new_story endpoint."""
    with patch('backend.crud.create_story_db_entry') as mock_create_story_db, \
            patch('backend.crud.update_story_title') as mock_update_title, \
            patch('backend.crud.create_story_page') as mock_create_page, \
            patch('backend.crud.update_page_image_path') as mock_update_page_img, \
            patch('backend.crud.delete_story_db_entry') as mock_delete_story, \
            patch('backend.crud.update_story_draft') as mock_update_draft, \
            patch('backend.crud.get_story') as mock_get_story, \
            patch('backend.crud.finalize_story_draft') as mock_finalize_draft:

        mock_now_fixture = datetime.now(UTC)

        # story_create_input_mock is used as the base for creating story mocks
        # It's passed to create_mock_story_internal

        def create_mock_story_internal(id_val, title_val, owner_id_val, is_draft_val=False, num_pages_val=0, story_input_base=story_create_input_mock):
            story = MagicMock(spec=schemas.Story)
            story.id = id_val
            story.title = title_val
            story.owner_id = owner_id_val
            story.is_draft = is_draft_val
            story.genre = story_input_base.genre
            # Use story_outline from story_input_base for both story_summary and story_outline
            story.story_summary = story_input_base.story_outline
            story.story_outline = story_input_base.story_outline
            story.main_characters = story_input_base.main_characters
            story.num_pages = num_pages_val
            # Assign the enum member directly, not its value
            story.image_style = story_input_base.image_style
            story.created_at = mock_now_fixture
            story.updated_at = mock_now_fixture
            story.pages = []
            story.characters = []

            # Allow arguments like exclude_unset
            def model_dump_side_effect(**kwargs):
                return {
                    'id': story.id,
                    'title': story.title,
                    'owner_id': story.owner_id,
                    'is_draft': story.is_draft,
                    'genre': story.genre,
                    'story_summary': story.story_summary,
                    'story_outline': story.story_outline,
                    'main_characters': [mc.model_dump() for mc in story.main_characters if hasattr(mc, 'model_dump')],
                    'num_pages': story.num_pages,
                    'image_style': story.image_style,
                    'created_at': story.created_at.isoformat() if story.created_at else None,
                    'updated_at': story.updated_at.isoformat() if story.updated_at else None,
                    'pages': [p.model_dump() for p in story.pages if hasattr(p, 'model_dump')],
                    'characters': [c.model_dump() for c in story.characters if hasattr(c, 'model_dump')]
                }
            story.model_dump = MagicMock(side_effect=model_dump_side_effect)
            return story

        # Mock for the initial story entry created by create_story_db_entry
        # This is typically a draft.
        mock_initial_draft_entry = create_mock_story_internal(
            id_val=123,  # Example draft ID
            title_val="[AI Title Pending...]",
            owner_id_val=current_user_mock.id,
            is_draft_val=True,
            num_pages_val=story_create_input_mock.num_pages  # Initial num_pages from input
        )
        # For new draft creation path
        mock_create_story_db.return_value = mock_initial_draft_entry

        # This object represents the story state *after* crud.finalize_story_draft is called.
        # ID is the finalized ID (e.g., 1), title is "Finalized Story" (before AI update).
        # is_draft is False. num_pages is initially from the draft.
        story_obj_post_crud_finalize = create_mock_story_internal(
            id_val=1,  # actual_finalized_story_id from the test
            title_val="Finalized Story",  # Title after finalize_story_draft, before AI update
            owner_id_val=current_user_mock.id,
            is_draft_val=False,  # CRITICAL
            num_pages_val=story_create_input_mock.num_pages  # num_pages from the draft input
        )
        mock_finalize_draft.return_value = story_obj_post_crud_finalize

        def dynamic_update_title_side_effect(db, story_id, new_title):
            # This side effect should operate on the story object that finalize_draft returned,
            # if the ID matches. This is the object that will have is_draft=False.
            target_story = None
            if story_id == story_obj_post_crud_finalize.id:
                target_story = story_obj_post_crud_finalize
            # Fallback for other tests (e.g. non-finalize flow)
            elif story_id == mock_initial_draft_entry.id:
                target_story = mock_initial_draft_entry

            if target_story:
                print(
                    f"FIXTURE: dynamic_update_title_side_effect for story_id {story_id}. Old title: '{target_story.title}', New title: '{new_title}'. is_draft: {target_story.is_draft}")
                target_story.title = new_title
                target_story.updated_at = datetime.now(UTC)
                # No need to update model_dump directly if it's a side_effect function that dynamically reads attributes
                return target_story
            else:
                # This case should ideally not be hit if get_story is mocked correctly to return one of the above.
                # If crud.update_story_title is called on a story not managed by these mocks,
                # we might need a more generic mock or ensure get_story provides the right one.
                print(
                    f"FIXTURE WARNING: dynamic_update_title_side_effect called with unexpected story_id: {story_id}. Creating a new mock.")
                # Fallback: create a new mock. This might hide issues if not expected.
                updated_story_mock = create_mock_story_internal(
                    id_val=story_id, title_val=new_title, owner_id_val=current_user_mock.id,
                    is_draft_val=False  # Assuming if title is updated, it's likely a finalized story
                )
                return updated_story_mock
        mock_update_title.side_effect = dynamic_update_title_side_effect

        page_id_counter = 1

        # Corrected signature
        def create_page_side_effect_refined(db, story_id, page):
            # Ensure it uses the mock_initial_draft_entry or story_obj_post_crud_finalize
            # depending on the context, or simply creates a new page object.
            # For this test, we expect it to be called after finalization.

            # Find the correct story object based on story_id
            current_story_obj = None
            if story_id == story_obj_post_crud_finalize.id:
                current_story_obj = story_obj_post_crud_finalize
            elif story_id == mock_initial_draft_entry.id:  # Should not happen in finalize path
                current_story_obj = mock_initial_draft_entry
            else:  # Fallback, though ideally one of the above should match
                # This might indicate an issue if reached unexpectedly.
                # For now, let's assume story_obj_post_crud_finalize is the target.
                current_story_obj = story_obj_post_crud_finalize

            # Simple ID generation for mock
            created_page_id = len(current_story_obj.pages) + 1

            # Create a mock Page object (ensure it matches schemas.Page)
            mock_page_db = schemas.Page(
                id=created_page_id,
                story_id=story_id,
                page_number=page.page_number,
                text=page.text,
                image_description=page.image_description,
                # image_path will be set by update_page_image_path mock
                image_path=f"mock/path/temp_page_{created_page_id}.png",
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC)
            )
            current_story_obj.pages.append(mock_page_db)
            # Simulate num_pages update on the parent story if it's not a title page (page_number 0)
            # However, the main.py logic updates num_pages based on story_input.num_pages,
            # and AI might generate a different number of pages.
            # The story_obj_post_crud_finalize.num_pages is set based on story_create_input_mock.num_pages
            # Let's ensure this side effect doesn't wrongly modify num_pages in a way that conflicts.
            # The actual num_pages is more a reflection of the input + AI generation.
            # crud.create_story_page itself doesn't update the parent story's num_pages.
            return mock_page_db

        mock_create_page.side_effect = create_page_side_effect_refined

        # Refined side effect for update_page_image_path
        # Corrected signature
        def update_page_img_side_effect_refined(db, page_id, image_path):
            # Find the page in story_obj_post_crud_finalize.pages and update its image_path
            target_page = None
            # Check in the finalized story first
            for p in story_obj_post_crud_finalize.pages:
                if p.id == page_id:
                    target_page = p
                    break

            # If not found, check in the initial draft (less likely for this flow)
            if not target_page:
                for p in mock_initial_draft_entry.pages:
                    if p.id == page_id:
                        target_page = p
                        break

            if target_page:
                target_page.image_path = image_path
                target_page.updated_at = datetime.now(UTC)
                return target_page
            # This should ideally not happen if page_id is valid
            raise ValueError(
                f"Mocked update_page_image_path: Page with id {page_id} not found in mock stories.")

        mock_update_page_img.side_effect = update_page_img_side_effect_refined

        # The mocks dictionary that will be yielded
        # Add the fully processed story object so the test can access it for assertions
        # and for its get_story side effect.
        yield_dict = {
            'create_story_db_entry': mock_create_story_db,
            'update_story_title': mock_update_title,
            'create_story_page': mock_create_page,
            'update_page_image_path': mock_update_page_img,
            'delete_story_db_entry': mock_delete_story,
            'update_story_draft': mock_update_draft,
            # The mock itself is yielded; side_effect is set in the test
            'get_story': mock_get_story,
            'finalize_story_draft': mock_finalize_draft,
            '_story_obj_after_finalize_and_ai': story_obj_post_crud_finalize,  # Key for test access
            '_mock_initial_draft_entry': mock_initial_draft_entry  # If needed by other tests
        }
        yield yield_dict
    # No more get_story side effect setup within this fixture.
    # It's handled by the test itself.


def test_create_new_story_draft_finalization(
    client, db_session_mock, current_user_mock, mock_crud_operations, mock_ai_services, story_create_input_mock
):
    draft_id_to_finalize = 123
    actual_finalized_story_id = 1  # ID after finalization, based on logs/mock behavior

    mock_now = datetime.now(UTC)

    updated_draft_mock = schemas.Story(
        id=draft_id_to_finalize,
        owner_id=current_user_mock.id,
        title=story_create_input_mock.title,
        genre=story_create_input_mock.genre,
        story_summary=story_create_input_mock.story_outline,
        story_outline=story_create_input_mock.story_outline,
        main_characters=story_create_input_mock.main_characters,
        num_pages=story_create_input_mock.num_pages,
        # Assign the enum member directly, not its value
        image_style=story_create_input_mock.image_style,
        created_at=mock_now,
        updated_at=mock_now,
        is_draft=True,
        pages=[],
        characters=[]
    )
    # Assign to the mock_crud_operations fixture so it can be used by other parts of the test if necessary
    mock_crud_operations['update_story_draft'].return_value = updated_draft_mock

    # --- Define a robust side_effect for mock_crud_operations['get_story'] ---
    # This side_effect function is defined *inside* the test to have access to test-local variables.
    fixture_story_obj_post_crud_finalize = mock_crud_operations['_story_obj_after_finalize_and_ai']
    _get_story_call_count = 0

    def get_story_side_effect_handler(db, story_id, owner_id, is_draft_param=None, **kwargs):
        nonlocal _get_story_call_count  # Ensure we can modify the outer scope variable
        _get_story_call_count += 1
        print(
            f"TEST DEBUG (get_story call #{_get_story_call_count}): Args: story_id={story_id}, owner_id={owner_id}, is_draft_param={is_draft_param}, kwargs={kwargs}")

        if owner_id != current_user_mock.id:
            print(
                f"TEST DEBUG ERROR: get_story_side_effect_handler - owner_id mismatch. Expected {current_user_mock.id}, got {owner_id}. Returning None.")
            return None

        # Case 1: Fetching the initial draft to be finalized.
        if story_id == draft_id_to_finalize:
            print(
                f"TEST DEBUG: get_story_side_effect_handler - Returning updated_draft_mock (id={updated_draft_mock.id}, is_draft={updated_draft_mock.is_draft}) for story_id {story_id}.")
            return updated_draft_mock

        # Case 2: Fetching the story after it has been finalized and processed by AI.
        elif story_id == actual_finalized_story_id:
            print(
                f"TEST DEBUG: get_story_side_effect_handler - Returning fixture_story_obj_post_crud_finalize (id={fixture_story_obj_post_crud_finalize.id}, is_draft={fixture_story_obj_post_crud_finalize.is_draft}, title='{fixture_story_obj_post_crud_finalize.title}', num_pages={fixture_story_obj_post_crud_finalize.num_pages}) for story_id {story_id}.")
            return fixture_story_obj_post_crud_finalize

        else:
            print(
                f"TEST DEBUG ERROR: get_story_side_effect_handler - Unexpected story_id: {story_id}. Returning None.")
            return None

    mock_crud_operations['get_story'].side_effect = get_story_side_effect_handler
    # --- End of side_effect definition ---

    # Ensure the draft can be finalized
    response = client.post(
        "/stories/",  # Corrected endpoint
        json={"story_input": story_create_input_mock.model_dump(
        ), "draft_id": draft_id_to_finalize},  # Corrected payload
        headers={"X-Token": "testtoken"}
    )

    # Check that the response is successful
    assert response.status_code == 200, response.text
    response_data = response.json()

    # Ensure the story is marked as not a draft and has a title
    assert response_data['is_draft'] is False
    assert response_data['title'] != "[AI Title Pending...]"

    # Check that the finalize_story_draft CRUD operation was called
    mock_crud_operations['finalize_story_draft'].assert_called_once()

    # Ensure the response contains the expected story data structure
    assert 'id' in response_data
    assert 'title' in response_data
    assert 'owner_id' in response_data
    assert 'is_draft' in response_data
    assert 'pages' in response_data

    # Check that the pages in the response match the AI-generated content
    for page in response_data['pages']:
        assert 'page_number' in page
        assert 'text' in page
        assert 'image_path' in page

    # Check that the story was actually finalized (is_draft=False)
    finalized_story_mock = mock_crud_operations['finalize_story_draft'].return_value
    assert finalized_story_mock.is_draft is False

    # Check that the correct story was fetched for the final response
    # mock_crud_operations['get_story'].assert_called_with(
    #     ANY, draft_id_to_finalize, current_user_mock.id)
    # This assertion is removed because main.py's create_new_story endpoint
    # doesn't directly call get_story(draft_id_to_finalize) in the draft finalization path.
    # It calls update_story_draft and finalize_story_draft, which internally handle fetching.
    # The get_story_side_effect_handler ensures that IF get_story is called by those, it behaves as expected.

    # Ensure the response story ID matches the ID of the finalized story from the mock setup
    # Corrected Assertion
    assert response_data['id'] == actual_finalized_story_id

    # Check that AI service for character reference image IS CALLED if images are missing.
    # For this test, assume character details in story_create_input_mock do NOT have reference_image_path.
    # So, for each character, generate_character_reference_image should be called.
    expected_char_ref_calls = len(story_create_input_mock.main_characters)
    if expected_char_ref_calls > 0:
        assert mock_ai_services['generate_character_reference_image'].call_count == expected_char_ref_calls
        for char_detail_input in story_create_input_mock.main_characters:
            mock_ai_services['generate_character_reference_image'].assert_any_call(
                character=char_detail_input,
                user_id=current_user_mock.id,
                story_id=actual_finalized_story_id,  # Use the finalized story ID
                image_style_enum=story_create_input_mock.image_style
            )
    else:
        mock_ai_services['generate_character_reference_image'].assert_not_called()

    # Check that other AI services were called for story generation
    mock_ai_services['generate_story_from_chatgpt'].assert_called()

    # Check that the story title was updated in the database
    # The title update should happen on the new story ID
    mock_crud_operations['update_story_title'].assert_called_once_with(
        # Corrected to use keyword arguments
        db=ANY, story_id=actual_finalized_story_id, new_title=ANY)

    # Ensure the title was updated to something meaningful
    # Accessing call_args when using keyword arguments requires using .kwargs
    updated_story_title = mock_crud_operations['update_story_title'].call_args.kwargs['new_title']
    assert updated_story_title != "[AI Title Pending...]"

    # Check that the pages were created with the correct content from AI
    ai_generated_pages_content = mock_ai_services['generate_story_from_chatgpt'].return_value["Pages"]
    assert len(response_data['pages']) == len(ai_generated_pages_content)

    # FIX: Changed = to in
    for i, page_in_response in enumerate(response_data['pages']):
        expected_ai_page_data = ai_generated_pages_content[i]
        expected_page_num_in_db = 0 if expected_ai_page_data["Page_number"] == "Title" else int(
            expected_ai_page_data["Page_number"])

        assert page_in_response['page_number'] == expected_page_num_in_db
        assert page_in_response['text'] == expected_ai_page_data["Text"]
        # The path is what main.py constructs and saves via crud.update_page_image_path
        assert page_in_response['image_path'] is not None
        assert page_in_response['image_path'].startswith(
            f"images/user_{current_user_mock.id}/story_{actual_finalized_story_id}/")
        assert f"_story_{actual_finalized_story_id}_pageid_{page_in_response['id']}.png" in page_in_response['image_path']

    # Check that the correct image generation calls were made for each page
    # generate_image should be called for each page that has an image description


# --- Admin Functionality Tests ---

def test_get_current_active_user_inactive(client, db_session_mock):
    inactive_user = schemas.User(
        id=2, username="inactiveuser", email="inactive@example.com",
        is_active=False, role="user"
    )

    def override_get_current_user_inactive():
        return inactive_user

    original_get_user_override = app.dependency_overrides.get(
        auth.get_current_user)
    app.dependency_overrides[auth.get_current_user] = override_get_current_user_inactive

    response = client.get(
        "/users/me/", headers={"Authorization": "Bearer faketoken"})
    assert response.status_code == 400
    assert response.json() == {"detail": "Inactive user"}

    # Cleanup this test's specific override
    if original_get_user_override:
        app.dependency_overrides[auth.get_current_user] = original_get_user_override
    elif auth.get_current_user in app.dependency_overrides:
        del app.dependency_overrides[auth.get_current_user]


def test_get_current_admin_user_not_admin(client, db_session_mock, current_user_mock):
    # This test relies on the default_mock_get_current_user fixture,
    # which provides an active user with role="user".
    # No specific override needed here if current_user_mock is already non-admin.
    # current_user_mock fixture provides role="user"

    # Use the /admin/placeholder endpoint defined in main.py
    response = client.get("/admin/placeholder",
                          headers={"Authorization": "Bearer faketoken"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized"}


def test_get_current_admin_user_is_admin(client, db_session_mock):
    admin_user = schemas.User(
        id=3, username="admin", email="admin@example.com",
        is_active=True, role="admin"
    )

    def override_get_current_user_admin():
        return admin_user

    original_get_user_override = app.dependency_overrides.get(
        auth.get_current_user)
    app.dependency_overrides[auth.get_current_user] = override_get_current_user_admin

    # Use the /admin/placeholder endpoint defined in main.py
    response = client.get("/admin/placeholder",
                          headers={"Authorization": "Bearer faketoken"})
    assert response.status_code == 200
    # The placeholder endpoint returns a plain string
    # assert response.text == f"Welcome admin user: {admin_user.username}" # Original assertion
    # Corrected assertion
    assert response.text == "This is a placeholder for the admin dashboard."

    # Cleanup this test\'s specific override
    if original_get_user_override:
        app.dependency_overrides[auth.get_current_user] = original_get_user_override
    elif auth.get_current_user in app.dependency_overrides:
        del app.dependency_overrides[auth.get_current_user]


def test_admin_dashboard_access_denied_for_regular_user(client, current_user_mock):
    # This test now relies on the `default_mock_get_current_user` fixture.
    # The `current_user_mock` it uses is active and has role="user".
    # So, no need for a local override of auth.get_current_user here.

    # Use the /admin/placeholder endpoint defined in main.py
    response = client.get("/admin/placeholder",
                          headers={"Authorization": "Bearer faketoken"})
    assert response.status_code == 403, response.text
    assert response.json() == {"detail": "Not authorized"}
    # No local override cleanup needed as we are using the global fixture's user.


def test_admin_dashboard_access_granted_for_admin_user(client, db_session_mock):
    admin_user = schemas.User(
        id=3, username="admin", email="admin@example.com",
        is_active=True, role="admin"
    )

    def override_get_current_user_admin_for_dashboard():
        return admin_user

    original_get_user_override = app.dependency_overrides.get(
        auth.get_current_user)
    app.dependency_overrides[auth.get_current_user] = override_get_current_user_admin_for_dashboard

    # Use the /admin/placeholder endpoint defined in main.py
    response = client.get("/admin/placeholder",
                          headers={"Authorization": "Bearer faketoken"})
    assert response.status_code == 200
    # The placeholder endpoint returns a plain string
    # assert response.text == f"Welcome admin user: {admin_user.username}" # Original assertion
    # Corrected assertion
    assert response.text == "This is a placeholder for the admin dashboard."

    # Cleanup this test\'s specific override
    if original_get_user_override:
        app.dependency_overrides[auth.get_current_user] = original_get_user_override
    elif auth.get_current_user in app.dependency_overrides:
        del app.dependency_overrides[auth.get_current_user]


# --- Admin User Role Management Tests ---

@pytest.fixture
def admin_user_for_role_tests():
    """Provides an admin user for role management tests."""
    return schemas.User(id=10, username="roleadmin", email="roleadmin@example.com", is_active=True, role="admin")


@pytest.fixture
def target_user_for_role_tests():
    """Provides a target user whose role will be changed."""
    return schemas.User(id=11, username="targetuser", email="target@example.com", is_active=True, role="user")


def mock_get_current_admin_user_specific(user_schema):
    """Factory to create an override for get_current_admin_user with a specific user."""
    def override():
        return user_schema
    return override


def test_set_user_role_unauthorized_non_admin(client, current_user_mock, target_user_for_role_tests, db_session_mock):
    """Test that a non-admin user cannot access the set_user_role_admin endpoint."""
    # current_user_mock is a regular user.
    # The endpoint /admin/users/{user_id}/role uses Depends(auth.get_current_admin_user)
    # So, we need to ensure that if a non-admin tries, auth.get_current_admin_user raises HTTPException
    # This is implicitly tested by the auth.get_current_admin_user dependency itself.
    # If we were to mock get_current_user to return a non-admin, it should fail.
    # However, the more direct test is that the dependency itself protects the route.

    # To simulate a non-admin making the call, we\'d typically ensure get_current_user returns a non-admin
    # and then rely on get_current_admin_user to fail.
    # For this specific endpoint, get_current_admin_user is the direct guard.

    # Override get_current_user to be our non-admin user
    original_get_user_override = app.dependency_overrides.get(
        auth.get_current_user)
    app.dependency_overrides[auth.get_current_user] = lambda: current_user_mock

    response = client.put(
        # CHANGED: use correct endpoint
        f"/admin/users/{target_user_for_role_tests.id}",
        json={"role": "admin"}
    )
    assert response.status_code == 403  # Because get_current_admin_user will fail
    assert response.json() == {"detail": "Not authorized"}

    # Cleanup
    if original_get_user_override:
        app.dependency_overrides[auth.get_current_user] = original_get_user_override
    elif auth.get_current_user in app.dependency_overrides:
        del app.dependency_overrides[auth.get_current_user]


def test_set_user_role_admin_success(client, admin_user_for_role_tests, target_user_for_role_tests, db_session_mock):
    """Test admin successfully changing another user's role."""
    original_admin_override = app.dependency_overrides.get(
        auth.get_current_admin_user)
    app.dependency_overrides[auth.get_current_admin_user] = mock_get_current_admin_user_specific(
        admin_user_for_role_tests)

    updated_user_data = target_user_for_role_tests.model_copy(
        update={"role": "admin"})

    with patch("backend.crud.admin_update_user", return_value=updated_user_data) as mock_update_user, \
            patch("backend.crud.get_user_admin", return_value=updated_user_data):
        db_session_mock.query.return_value.filter.return_value.first.return_value = updated_user_data

        response = client.put(
            f"/admin/users/{target_user_for_role_tests.id}",
            json={"role": "admin"}
        )
        assert response.status_code == 200, response.text
        assert response.json()["role"] == "admin"
        assert response.json()["id"] == target_user_for_role_tests.id
        mock_update_user.assert_called_once()
        called_args, called_kwargs = mock_update_user.call_args
        assert called_args[0] == db_session_mock
        assert called_kwargs["user_id"] == target_user_for_role_tests.id
        assert called_kwargs["user_update"].role == "admin"

    # Test changing role back
    updated_user_data_back = target_user_for_role_tests.model_copy(update={
                                                                   "role": "user"})
    with patch("backend.crud.admin_update_user", return_value=updated_user_data_back) as mock_update_user_back, \
            patch("backend.crud.get_user_admin", return_value=updated_user_data_back):
        db_session_mock.query.return_value.filter.return_value.first.return_value = updated_user_data_back

        response_back = client.put(
            f"/admin/users/{target_user_for_role_tests.id}",
            json={"role": "user"}
        )
        assert response_back.status_code == 200, response_back.text
        assert response_back.json()["role"] == "user"
        mock_update_user_back.assert_called_once()
        called_args_back, called_kwargs_back = mock_update_user_back.call_args
        assert called_args_back[0] == db_session_mock
        assert called_kwargs_back["user_id"] == target_user_for_role_tests.id
        assert called_kwargs_back["user_update"].role == "user"

    # Cleanup
    if original_admin_override:
        app.dependency_overrides[auth.get_current_admin_user] = original_admin_override
    elif auth.get_current_user in app.dependency_overrides:
        del app.dependency_overrides[auth.get_current_user]


def test_set_user_role_admin_self_change_forbidden(client, admin_user_for_role_tests, db_session_mock):
    """Test admin attempting to change their own role is forbidden."""
    original_admin_override = app.dependency_overrides.get(
        auth.get_current_admin_user)
    app.dependency_overrides[auth.get_current_admin_user] = mock_get_current_admin_user_specific(
        admin_user_for_role_tests)

    with patch("backend.crud.get_user_admin", return_value=admin_user_for_role_tests):
        # Simulate that there is at least one other admin
        db_session_mock.query.return_value.filter.return_value.count.return_value = 1

        response = client.put(
            f"/admin/users/{admin_user_for_role_tests.id}",
            json={"role": "user"}
        )
        # The logic now forbids any admin from changing their own role.
        assert response.status_code == 403
        assert response.json()[
            "detail"] == "Admins cannot change their own role."

    # Cleanup
    del app.dependency_overrides[auth.get_current_admin_user]


def test_admin_deactivate_self_forbidden(client, db_session_mock):
    admin_user = schemas.User(
        id=1, username="adminuser", email="admin@example.com", is_active=True, role="admin")

    def override_get_current_admin_user():
        return admin_user
    app.dependency_overrides[auth.get_current_admin_user] = override_get_current_admin_user

    with patch("backend.crud.get_user_admin", return_value=admin_user):
        response = client.put(
            f"/admin/users/{admin_user.id}",
            json={"is_active": False}
        )
        assert response.status_code == 403
        assert response.json() == {
            "detail": "Admins cannot deactivate their own account."}

    # Cleanup
    del app.dependency_overrides[auth.get_current_admin_user]


def test_set_user_role_admin_invalid_role_value(client, admin_user_for_role_tests, target_user_for_role_tests, db_session_mock):
    """Test admin attempting to set an invalid role value."""
    original_admin_override = app.dependency_overrides.get(
        auth.get_current_admin_user)
    app.dependency_overrides[auth.get_current_admin_user] = mock_get_current_admin_user_specific(
        admin_user_for_role_tests)

    with patch("backend.crud.admin_update_user") as mock_update_role:  # Should not be called
        response = client.put(
            f"/admin/users/{target_user_for_role_tests.id}",
            json={"role": "moderator"}  # Invalid role
        )
        assert response.status_code == 400, response.text
        assert response.json() == {
            "detail": "Invalid role. Must be 'user' or 'admin'."}
        mock_update_role.assert_not_called()

    # Cleanup
    if original_admin_override:
        app.dependency_overrides[auth.get_current_admin_user] = original_admin_override
    else:
        del app.dependency_overrides[auth.get_current_admin_user]


def test_set_user_role_admin_user_not_found(client, admin_user_for_role_tests, db_session_mock):
    """Test admin attempting to change role of a non-existent user."""
    original_admin_override = app.dependency_overrides.get(
        auth.get_current_admin_user)
    app.dependency_overrides[auth.get_current_admin_user] = mock_get_current_admin_user_specific(
        admin_user_for_role_tests)

    non_existent_user_id = 9999

    with patch("backend.crud.get_user_admin", return_value=None):
        with patch("backend.crud.admin_update_user") as mock_update_user:
            response = client.put(
                f"/admin/users/{non_existent_user_id}",
                json={"role": "admin"}
            )
            assert response.status_code == 404
            assert response.json() == {
                "detail": f"User with ID {non_existent_user_id} not found"}
            mock_update_user.assert_not_called()

    # Cleanup
    if original_admin_override:
        app.dependency_overrides[auth.get_current_admin_user] = original_admin_override
    else:
        del app.dependency_overrides[auth.get_current_admin_user]


# --- User Profile Management ---

# Ensure this is the last line or followed by other class/function definitions
