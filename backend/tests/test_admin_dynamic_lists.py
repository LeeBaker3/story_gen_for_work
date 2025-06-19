import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session  # Added for type hinting
from backend.main import app
# Ensure Base and engine are imported if needed for setup/teardown
from backend.database import SessionLocal, Base, engine
# Ensure all necessary modules are imported
from backend import database, crud, schemas

# Test client fixture (if not already in conftest.py and scoped appropriately)
# @pytest.fixture(scope="module")
# def client():
#     # Setup: Create tables (if not already handled globally or by autouse fixtures)
#     # Base.metadata.create_all(bind=engine)
#     with TestClient(app) as c:
#         yield c
#     # Teardown: Drop tables (if managing test DB lifecycle here)
#     # Base.metadata.drop_all(bind=engine)

# @pytest.fixture(scope="session")  # Or module, depending on when you want it to run
# def db_session():
#     # This fixture can provide a DB session if tests need direct DB interaction
#     # Ensure this aligns with how your app gets its DB session (e.g., dependency override for tests)
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# Utility to create a test list and ensure it exists for subsequent item tests


def ensure_dynamic_list_exists(client: TestClient, list_name: str, admin_token: str, list_label: str = None):
    response = client.get(
        f"/admin/dynamic-lists/{list_name}", headers={"Authorization": f"Bearer {admin_token}"})
    if response.status_code == 404:
        list_payload = {"list_name": list_name, "description": f"Test list {list_name}"}
        if list_label:
            list_payload["list_label"] = list_label
        create_response = client.post(
            "/admin/dynamic-lists/",
            json=list_payload,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        # FastAPI returns 200 for POST if resource created
        if create_response.status_code not in [200, 201]:
            raise Exception(
                f"Failed to create dynamic list \'{list_name}\' for testing: {create_response.text}")
    elif response.status_code != 200:
        raise Exception(
            f"Failed to check/ensure dynamic list \'{list_name}\' exists: {response.text}")

# 1. Admin can create a new dynamic list item


def test_admin_create_dynamic_list_item(client: TestClient, admin_token: str):
    list_name = "test_list_for_create"
    ensure_dynamic_list_exists(client, list_name, admin_token)

    payload = {
        "list_name": list_name,
        "item_value": "testval_create",
        "item_label": "Test Value Create",
        "is_active": True,
        "sort_order": 1
    }
    response = client.post(
        f"/admin/dynamic-lists/{list_name}/items",  # Corrected endpoint
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 201  # Corrected expected status code
    data = response.json()
    assert data["item_value"] == "testval_create"
    assert data["item_label"] == "Test Value Create"
    assert data["list_name"] == list_name

# 2. Admin can edit a dynamic list item


def test_admin_edit_dynamic_list_item(client: TestClient, admin_token: str):
    list_name = "test_list_for_edit"
    ensure_dynamic_list_exists(client, list_name, admin_token)

    # Create item first
    create_payload = {
        "list_name": list_name,
        "item_value": "editval_initial",
        "item_label": "Edit Value Initial",
        "is_active": True,
        "sort_order": 2
    }
    create_response = client.post(f"/admin/dynamic-lists/{list_name}/items", json=create_payload,  # Corrected endpoint
                                  headers={"Authorization": f"Bearer {admin_token}"})
    assert create_response.status_code == 201  # Corrected expected status code
    item_id = create_response.json()["id"]

    # Edit the created item
    update_payload = {
        "item_value": "editval_updated",
        "item_label": "Edit Value Updated",
        "is_active": False,
        "sort_order": 3
    }
    response = client.put(
        f"/admin/dynamic-lists/items/{item_id}",  # Corrected endpoint
        json=update_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["item_value"] == "editval_updated"
    assert data["item_label"] == "Edit Value Updated"
    assert data["is_active"] is False
    assert data["sort_order"] == 3

# 3. Admin can delete a dynamic list item if not in use


def test_admin_delete_dynamic_list_item_not_in_use(client: TestClient, admin_token: str):
    list_name = "test_list_for_delete"
    ensure_dynamic_list_exists(client, list_name, admin_token)

    # Create item
    create_payload = {
        "list_name": list_name,
        "item_value": "delval_not_in_use",
        "item_label": "Delete Value Not In Use",
    }
    create_response = client.post(f"/admin/dynamic-lists/{list_name}/items", json=create_payload,  # Corrected endpoint
                                  headers={"Authorization": f"Bearer {admin_token}"})
    assert create_response.status_code == 201  # Corrected expected status code
    item_id = create_response.json()["id"]

    # Delete
    response = client.delete(
        f"/admin/dynamic-lists/items/{item_id}",  # Corrected endpoint
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 204

# 4. Admin cannot delete a dynamic list item if in use
# This test requires a db_session fixture that provides the same session context as the app for CRUD operations.
# Ensure your conftest.py or test setup provides such a fixture.


def test_admin_cannot_delete_in_use_dynamic_list_item(client: TestClient, admin_token: str, db_session: Session):
    # Use a list name that crud.is_dynamic_list_item_in_use checks
    list_name = "genres"
    item_value_in_use = "in_use_genre_value_for_real_genre_list"
    ensure_dynamic_list_exists(client, list_name, admin_token)

    # Create item
    create_payload = {
        "list_name": list_name,
        "item_value": item_value_in_use,
        "item_label": "In Use Genre Label",
    }
    create_response = client.post(f"/admin/dynamic-lists/{list_name}/items", json=create_payload,  # Corrected endpoint
                                  headers={"Authorization": f"Bearer {admin_token}"})
    # Corrected expected status code
    assert create_response.status_code == 201, f"Failed to create item: {create_response.text}"
    item_id = create_response.json()["id"]

    # Create a story using this genre item_value directly via CRUD
    # Ensure adminuser exists or use a known user
    admin_user = crud.get_user_by_username(db_session, "adminuser")
    if not admin_user:
        # Fallback or create if necessary, though ideally adminuser is seeded by conftest
        admin_user = crud.create_user(db_session, schemas.UserCreate(
            username="adminuser", password="adminpassword", email="admin_usage_test@example.com", role="admin"))

    # Create a story that uses the item_value
    # Note: Story.genre expects the item_value, not the label.
    story_data = schemas.StoryCreate(
        title="Story Using Dynamic Item",
        genre=item_value_in_use,  # This is the crucial part for the usage check
        story_outline="An outline.",
        main_characters=[],
        num_pages=1,
        # Provide defaults for other required StoryCreate fields if not nullable
        image_style=schemas.ImageStyle.DEFAULT,
        word_to_picture_ratio=schemas.WordToPictureRatio.PER_PAGE,
        text_density=schemas.TextDensity.CONCISE,
    )
    # Use create_story_draft or a similar CRUD that directly sets genre
    created_story = crud.create_story_draft(
        db=db_session, story_data=story_data, user_id=admin_user.id)
    assert created_story is not None
    db_session.commit()  # Ensure story is committed

    # Try to delete the item - should fail because it\'s in use
    delete_response = client.delete(
        f"/admin/dynamic-lists/items/{item_id}",  # Corrected endpoint
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    # Corrected based on router logic for in-use item
    assert delete_response.status_code == 409
    # assert "cannot delete item" in delete_response.json()["detail"].lower()
    assert f"item '{item_value_in_use.lower()}'" in delete_response.json()["detail"].lower() or \
        f"item '{create_payload['item_label'].lower()}'" in delete_response.json()[
        "detail"].lower()
    assert "is currently in use and cannot be deleted" in delete_response.json()[
        "detail"].lower()

    # Cleanup: delete the story to make the item deletable for other tests if needed, or handle DB rollback
    if created_story:
        crud.delete_story_db_entry(db_session, created_story.id)
        db_session.commit()


# 5. Admin can deactivate an item even if in use
def test_admin_can_deactivate_in_use_dynamic_list_item(client: TestClient, admin_token: str, db_session: Session):
    list_name = "genres_for_deactivate_test"
    item_value_to_deactivate = "deactivate_genre_value"
    ensure_dynamic_list_exists(client, list_name, admin_token)

    # Create item
    create_payload = {
        "list_name": list_name,
        "item_value": item_value_to_deactivate,
        "item_label": "Deactivate Genre Label",
        "is_active": True
    }
    create_response = client.post(f"/admin/dynamic-lists/{list_name}/items", json=create_payload,  # Corrected endpoint
                                  headers={"Authorization": f"Bearer {admin_token}"})
    assert create_response.status_code == 201  # Corrected expected status code
    item_id = create_response.json()["id"]

    # Create a story using this genre item_value
    admin_user = crud.get_user_by_username(db_session, "adminuser")
    if not admin_user:
        admin_user = crud.create_user(db_session, schemas.UserCreate(
            username="adminuser_deact", password="adminpassword", email="admin_deact_test@example.com", role="admin"))

    story_data = schemas.StoryCreate(
        title="Story For Deactivating Item",
        genre=item_value_to_deactivate,
        story_outline="Outline.",
        main_characters=[],
        num_pages=1,
        image_style=schemas.ImageStyle.DEFAULT,
        word_to_picture_ratio=schemas.WordToPictureRatio.PER_PAGE,
        text_density=schemas.TextDensity.CONCISE,
    )
    created_story_for_deactivation = crud.create_story_draft(
        db=db_session, story_data=story_data, user_id=admin_user.id)
    assert created_story_for_deactivation is not None
    db_session.commit()

    # Deactivate the item (is_active: False)
    update_payload = {"is_active": False}
    response = client.put(
        f"/admin/dynamic-lists/items/{item_id}",  # Corrected endpoint
        json=update_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False

    # Cleanup
    if created_story_for_deactivation:
        crud.delete_story_db_entry(
            db_session, created_story_for_deactivation.id)
        db_session.commit()

# 6. Non-admin cannot access these endpoints


def test_non_admin_cannot_manage_dynamic_list_items(client: TestClient, regular_user_token: str):
    list_name = "test_list_for_non_admin"
    # Admin needs to create the list first for the non-admin to attempt to add an item to it
    # This requires an admin_token. If not available, this part of the test might need rethinking
    # or the list creation should be part of a global setup.
    # For now, assuming admin_token is accessible or list is pre-existing.
    # A better approach: non-admin tries to create a list first, which should also fail.

    # Non-admin tries to create a list
    list_create_payload = {"list_name": list_name,
                           "description": "Attempt by non-admin"}
    response_list_create = client.post(
        "/admin/dynamic-lists/",
        json=list_create_payload,
        headers={"Authorization": f"Bearer {regular_user_token}"}
    )
    assert response_list_create.status_code == 403  # Forbidden

    # Non-admin tries to create an item (assuming list might exist or to test item endpoint directly)
    item_payload = {
        "list_name": list_name,
        "item_value": "failval_non_admin",
        "item_label": "Should Fail Non-Admin",
    }
    response_item_create = client.post(
        f"/admin/dynamic-lists/{list_name}/items",  # Corrected endpoint
        json=item_payload,
        headers={"Authorization": f"Bearer {regular_user_token}"}
    )
    assert response_item_create.status_code == 403

    # Non-admin tries to PUT (update) an item - needs an item_id, so this is harder to test in isolation
    # without first creating an item as admin. For simplicity, we can skip or mock.
    # Let's assume an item with ID 1 exists for the sake of testing the endpoint protection.
    response_item_update = client.put(
        f"/admin/dynamic-lists/items/1",  # Corrected endpoint
        json={"item_label": "Attempted Update"},
        headers={"Authorization": f"Bearer {regular_user_token}"}
    )
    assert response_item_update.status_code == 403

    # Non-admin tries to DELETE an item
    response_item_delete = client.delete(
        f"/admin/dynamic-lists/items/1",  # Corrected endpoint
        headers={"Authorization": f"Bearer {regular_user_token}"}
    )
    assert response_item_delete.status_code == 403  # Forbidden (or 404)


# 7. Cannot create duplicate item_value in the same list
def test_cannot_create_duplicate_item_value_in_list(client: TestClient, admin_token: str):
    list_name = "test_list_for_duplicates"
    ensure_dynamic_list_exists(client, list_name, admin_token)

    item_payload = {
        "list_name": list_name,
        "item_value": "duplicate_val",
        "item_label": "Duplicate Value 1",
        "sort_order": 1
    }
    # Create first item
    response1 = client.post(f"/admin/dynamic-lists/{list_name}/items", json=item_payload,  # Corrected endpoint
                            headers={"Authorization": f"Bearer {admin_token}"})
    assert response1.status_code == 201  # Corrected expected status code

    # Attempt to create second item with same list_name and item_value
    item_payload_duplicate = {
        "list_name": list_name,
        "item_value": "duplicate_val",
        "item_label": "Duplicate Value 2",
        "sort_order": 2
    }
    response2 = client.post(f"/admin/dynamic-lists/{list_name}/items", json=item_payload_duplicate,  # Corrected endpoint
                            headers={"Authorization": f"Bearer {admin_token}"})
    assert response2.status_code == 400
    assert "already exists" in response2.json()["detail"].lower()
    assert f"value \'{item_payload_duplicate['item_value']}\'" in response2.json()[
        "detail"].lower()
    assert f"list \'{list_name}\'" in response2.json()["detail"].lower()

# 8. Admin can retrieve all items for a list


def test_admin_get_all_items_for_list(client: TestClient, admin_token: str):
    list_name = "test_list_for_get_all"
    ensure_dynamic_list_exists(client, list_name, admin_token)

    # Create a couple of items
    client.post(f"/admin/dynamic-lists/{list_name}/items", json={"list_name": list_name, "item_value": "val1",  # Corrected endpoint
                "item_label": "Label1"}, headers={"Authorization": f"Bearer {admin_token}"})
    client.post(f"/admin/dynamic-lists/{list_name}/items", json={"list_name": list_name, "item_value": "val2",  # Corrected endpoint
                "item_label": "Label2", "is_active": False}, headers={"Authorization": f"Bearer {admin_token}"})
    client.post(f"/admin/dynamic-lists/{list_name}/items", json={"list_name": list_name, "item_value": "val3",  # Corrected endpoint
                "item_label": "Label3"}, headers={"Authorization": f"Bearer {admin_token}"})

    # Get all items
    response_all = client.get(f"/admin/dynamic-lists/{list_name}/items", headers={
                              "Authorization": f"Bearer {admin_token}"})
    assert response_all.status_code == 200
    items = response_all.json()
    # GTE because other tests might use the same list if not isolated
    assert len(items) >= 3

    # Get only active items
    response_active = client.get(
        f"/admin/dynamic-lists/{list_name}/items?only_active=true", headers={"Authorization": f"Bearer {admin_token}"})
    assert response_active.status_code == 200
    active_items = response_active.json()
    assert len(active_items) >= 2  # val2 is inactive
    for item in active_items:
        assert item["is_active"] is True

    # Get only inactive items
    response_inactive = client.get(
        f"/admin/dynamic-lists/{list_name}/items?only_active=false", headers={"Authorization": f"Bearer {admin_token}"})
    assert response_inactive.status_code == 200
    inactive_items = response_inactive.json()
    assert len(inactive_items) >= 1  # val2 is inactive
    for item in inactive_items:
        assert item["is_active"] is False

# 9. Admin can get a specific item by ID


def test_admin_get_specific_item_by_id(client: TestClient, admin_token: str):
    list_name = "test_list_for_get_specific"
    ensure_dynamic_list_exists(client, list_name, admin_token)

    create_payload = {"list_name": list_name,
                      "item_value": "specific_val", "item_label": "Specific Label"}
    create_response = client.post(f"/admin/dynamic-lists/{list_name}/items", json=create_payload,  # Corrected endpoint
                                  headers={"Authorization": f"Bearer {admin_token}"})
    assert create_response.status_code == 201  # Corrected expected status code
    item_id = create_response.json()["id"]

    response = client.get(
        # Corrected endpoint
        f"/admin/dynamic-lists/items/{item_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item_id
    assert data["item_value"] == "specific_val"

# 10. Admin gets 404 for non-existent item ID


def test_admin_get_non_existent_item_returns_404(client: TestClient, admin_token: str):
    response = client.get("/admin/dynamic-lists/items/999999", headers={  # Corrected endpoint
                          "Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 404


def test_admin_create_edit_image_style_item_with_openai_style(client: TestClient, admin_token: str):
    list_name = "image_styles"
    ensure_dynamic_list_exists(client, list_name, admin_token)

    item_value_vivid = "test_style_vivid_openai_dynamic"
    item_label_vivid = "Test Style Vivid OpenAI Dynamic"

    create_payload = {
        "list_name": list_name,
        "item_value": item_value_vivid,
        "item_label": item_label_vivid,
        "is_active": True,
        "sort_order": 100,
        "additional_config": {"openai_style": "vivid"}
    }
    create_response = client.post(f"/admin/dynamic-lists/{list_name}/items", json=create_payload,  # Corrected endpoint
                                  headers={"Authorization": f"Bearer {admin_token}"})
    # Corrected expected status code
    assert create_response.status_code == 201, f"Failed to create item: {create_response.text}"
    created_item = create_response.json()
    item_id = created_item["id"]

    assert created_item["list_name"] == list_name
    assert created_item["item_value"] == item_value_vivid
    assert created_item["item_label"] == item_label_vivid
    assert created_item["is_active"] is True
    assert created_item["sort_order"] == 100
    assert created_item["additional_config"] == {"openai_style": "vivid"}

    # 2. Edit the item to change openai_style to "natural" and other fields
    item_label_natural_updated = "Test Style Natural OpenAI Updated Dynamic"
    update_payload = {
        "item_label": item_label_natural_updated,
        "is_active": False,
        "additional_config": {"openai_style": "natural"},
        "sort_order": 101
    }
    edit_response = client.put(
        f"/admin/dynamic-lists/items/{item_id}",  # Corrected endpoint
        json=update_payload,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert edit_response.status_code == 200, f"Failed to edit item: {edit_response.text}"
    edited_item = edit_response.json()

    assert edited_item["id"] == item_id
    assert edited_item["list_name"] == list_name
    # item_value is not changed here
    assert edited_item["item_value"] == item_value_vivid
    assert edited_item["item_label"] == item_label_natural_updated
    assert edited_item["is_active"] is False
    assert edited_item["sort_order"] == 101
    assert edited_item["additional_config"] == {"openai_style": "natural"}

    # 3. Test editing additional_config to include other keys
    update_payload_other_config = {
        "additional_config": {"openai_style": "vivid", "other_key": "other_value"}
    }
    edit_response_other_config = client.put(
        f"/admin/dynamic-lists/items/{item_id}",  # Corrected endpoint
        json=update_payload_other_config,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert edit_response_other_config.status_code == 200, f"Failed to edit item with other config: {edit_response_other_config.text}"
    edited_item_other_config = edit_response_other_config.json()
    assert edited_item_other_config["additional_config"] == {
        "openai_style": "vivid", "other_key": "other_value"}

    # 4. Test editing additional_config to be an empty dict
    update_payload_empty_config = {
        "additional_config": {}
    }
    edit_response_empty_config = client.put(
        f"/admin/dynamic-lists/items/{item_id}",  # Corrected endpoint
        json=update_payload_empty_config,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert edit_response_empty_config.status_code == 200, f"Failed to edit item with empty config: {edit_response_empty_config.text}"
    edited_item_empty_config = edit_response_empty_config.json()
    assert edited_item_empty_config["additional_config"] == {}

    # Cleanup: Delete the created item
    delete_response = client.delete(
        f"/admin/dynamic-lists/items/{item_id}",  # Corrected endpoint
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert delete_response.status_code == 204


# 11. Check item usage endpoint


def test_check_item_usage(client: TestClient, admin_token: str, db_session: Session):
    list_name_usage = "genres"
    item_value_usage = "usage_check_genre_for_real_genre_list"
    ensure_dynamic_list_exists(client, list_name_usage, admin_token)

    create_payload = {"list_name": list_name_usage,
                      "item_value": item_value_usage, "item_label": "Usage Check Label"}
    item_res = client.post(f"/admin/dynamic-lists/{list_name_usage}/items", json=create_payload,  # Corrected endpoint
                           headers={"Authorization": f"Bearer {admin_token}"})
    assert item_res.status_code == 201  # Corrected expected status code
    item_id = item_res.json()["id"]

    # Check usage (should not be in use yet)
    usage_res_before = client.get(
        # Corrected endpoint
        f"/admin/dynamic-lists/items/{item_id}/in-use", headers={"Authorization": f"Bearer {admin_token}"})
    assert usage_res_before.status_code == 200
    usage_data_before = usage_res_before.json()
    assert usage_data_before["is_in_use"] is False

    # Create a story using the item
    admin_user = crud.get_user_by_username(db_session, "adminuser")
    if not admin_user:
        admin_user = crud.create_user(db_session, schemas.UserCreate(
            username="adminuser_usage", password="adminpassword", email="admin_usage_check@example.com", role="admin"))

    story_data = schemas.StoryCreate(
        title="Story for Usage Check", genre=item_value_usage, story_outline="Outline.", main_characters=[], num_pages=1,
        image_style=schemas.ImageStyle.DEFAULT, word_to_picture_ratio=schemas.WordToPictureRatio.PER_PAGE, text_density=schemas.TextDensity.CONCISE,
    )
    story_for_usage = crud.create_story_draft(
        db=db_session, story_data=story_data, user_id=admin_user.id)
    db_session.commit()
    assert story_for_usage is not None

    # Check usage again (should be in use)
    usage_res_after = client.get(
        # Corrected endpoint
        f"/admin/dynamic-lists/items/{item_id}/in-use", headers={"Authorization": f"Bearer {admin_token}"})
    assert usage_res_after.status_code == 200
    usage_data_after = usage_res_after.json()
    assert usage_data_after["is_in_use"] is True

    # Verify the details mention the story that was created for this test
    assert any(
        story_for_usage.title in detail_string for detail_string in usage_data_after["details"])

    # Cleanup: delete the story to make the item deletable for other tests if needed, or handle DB rollback
    if story_for_usage:
        crud.delete_story_db_entry(db_session, story_for_usage.id)
        db_session.commit()

# 12. Public endpoint for active items


# admin_token to set up list & items
def test_public_get_active_list_items(client: TestClient, admin_token: str):
    list_name_public = "public_list_test"
    ensure_dynamic_list_exists(client, list_name_public, admin_token)

    client.post(f"/admin/dynamic-lists/{list_name_public}/items", json={"list_name": list_name_public, "item_value": "pub_active1",  # Corrected endpoint
                "item_label": "Public Active 1", "is_active": True, "sort_order": 1}, headers={"Authorization": f"Bearer {admin_token}"})
    client.post(f"/admin/dynamic-lists/{list_name_public}/items", json={"list_name": list_name_public, "item_value": "pub_inactive",  # Corrected endpoint
                "item_label": "Public Inactive", "is_active": False, "sort_order": 2}, headers={"Authorization": f"Bearer {admin_token}"})
    client.post(f"/admin/dynamic-lists/{list_name_public}/items", json={"list_name": list_name_public, "item_value": "pub_active2", "item_label": "Public Active 2",  # Corrected endpoint
                                                                        "is_active": True, "sort_order": 0}, headers={"Authorization": f"Bearer {admin_token}"})

    response = client.get(
        f"/dynamic-lists/{list_name_public}/active-items")  # No auth needed
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 2
    assert items[0]["item_value"] == "pub_active2"  # Check sort_order
    assert items[1]["item_value"] == "pub_active1"
    for item in items:
        assert item["is_active"] is True


def test_public_get_active_items_for_non_existent_list(client: TestClient):
    response = client.get(
        "/dynamic-lists/non_existent_list_abc123/active-items")
    assert response.status_code == 404

# Ensure conftest.py has fixtures for `client`, `admin_token`, `regular_user_token`, and `db_session`.
# `db_session` should provide a SQLAlchemy session that can be used for direct CRUD operations
# in tests, and it should ideally be the same session or configured similarly to what the
# FastAPI app uses (e.g., via dependency overrides for testing).
# Example conftest.py structure might include:
# @pytest.fixture(scope="session")
# def test_db_setup_teardown():
#     Base.metadata.create_all(bind=engine) # Create tables once per session
#     yield
#     Base.metadata.drop_all(bind=engine) # Drop tables once after all tests

# @pytest.fixture(scope="function") # Or module, if preferred
# def db_session(test_db_setup_teardown): # Depends on setup/teardown
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.rollback() # Rollback changes after each test function to ensure isolation
#         db.close()

# @pytest.fixture(scope="module")
# def client(test_db_setup_teardown): # Ensure DB is set up before client is created
#     # Override get_db dependency for TestClient if necessary
#     # def override_get_db():
#     #     try:
#     #         db = SessionLocal()
#     #         yield db
#     #     finally:
#     #         db.close()
#     # app.dependency_overrides[database.get_db] = override_get_db
#     with TestClient(app) as c:
#         yield c
#     # app.dependency_overrides.clear() # Clean up overrides

# (admin_token and regular_user_token fixtures would also be defined in conftest.py)


def test_admin_create_dynamic_list(client: TestClient, admin_token: str):
    payload = {"list_name": "new_test_list_label", "list_label": "New Test List Label", "description": "A new test list with a label"}
    response = client.post("/admin/dynamic-lists/", json=payload,
                           headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 201
    data = response.json()
    assert data["list_name"] == "new_test_list_label"
    assert data["list_label"] == "New Test List Label"
    assert data["description"] == "A new test list with a label"


def test_admin_edit_dynamic_list(client: TestClient, admin_token: str):
    list_name = "list_to_edit_label_unique_name"  # Ensure unique name
    list_label_initial = "Initial Label"
    # Ensure list exists or create it
    ensure_dynamic_list_exists(client, list_name, admin_token, list_label=list_label_initial)

    update_payload = {"description": "Updated description for edit test with label", "list_label": "Updated Label"}
    response = client.put(f"/admin/dynamic-lists/{list_name}", json=update_payload,
                          headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["list_name"] == list_name
    assert data["list_label"] == "Updated Label"
    assert data["description"] == "Updated description for edit test with label"

    # Test updating only description (list_label should remain)
    update_payload_desc_only = {"description": "Only description updated"}
    response_desc_only = client.put(f"/admin/dynamic-lists/{list_name}", json=update_payload_desc_only,
                                    headers={"Authorization": f"Bearer {admin_token}"})
    assert response_desc_only.status_code == 200
    data_desc_only = response_desc_only.json()
    assert data_desc_only["list_label"] == "Updated Label" # Should persist
    assert data_desc_only["description"] == "Only description updated"

    # Test updating only list_label (description should remain)
    update_payload_label_only = {"list_label": "Label Only Updated"}
    response_label_only = client.put(f"/admin/dynamic-lists/{list_name}", json=update_payload_label_only,
                                     headers={"Authorization": f"Bearer {admin_token}"})
    assert response_label_only.status_code == 200
    data_label_only = response_label_only.json()
    assert data_label_only["list_label"] == "Label Only Updated"
    assert data_label_only["description"] == "Only description updated" # Should persist

    # Test sending empty string for list_label (should be allowed, becomes null or empty based on model)
    update_payload_empty_label = {"list_label": ""}
    response_empty_label = client.put(f"/admin/dynamic-lists/{list_name}", json=update_payload_empty_label,
                                     headers={"Authorization": f"Bearer {admin_token}"})
    assert response_empty_label.status_code == 200
    data_empty_label = response_empty_label.json()
    assert data_empty_label["list_label"] == "" # Or None, depending on Pydantic/DB model handling

    # Test sending null for list_label (should be allowed)
    update_payload_null_label = {"list_label": None}
    response_null_label = client.put(f"/admin/dynamic-lists/{list_name}", json=update_payload_null_label,
                                     headers={"Authorization": f"Bearer {admin_token}"})
    assert response_null_label.status_code == 200
    data_null_label = response_null_label.json()
    assert data_null_label["list_label"] is None

def test_admin_delete_dynamic_list(client: TestClient, admin_token: str):
    # Ensure this list name is unique for this test run or cleaned up
    list_name = "list_to_delete"
    # Ensure list exists
    create_res = client.post("/admin/dynamic-lists/", json={
                             "list_name": list_name, "description": "To be deleted"}, headers={"Authorization": f"Bearer {admin_token}"})
    assert create_res.status_code == 201  # Corrected expected status code

    # Add an item to it to test cascade delete (optional, but good)
    item_payload = {"list_name": list_name,
                    "item_value": "item_in_deleted_list", "item_label": "Test Item"}
    item_res = client.post(f"/admin/dynamic-lists/{list_name}/items", json=item_payload,  # Corrected endpoint
                           headers={"Authorization": f"Bearer {admin_token}"})
    assert item_res.status_code == 201  # Corrected expected status code
    item_id = item_res.json()["id"]

    delete_response = client.delete(
        f"/admin/dynamic-lists/{list_name}", headers={"Authorization": f"Bearer {admin_token}"})
    assert delete_response.status_code == 204

    # Verify list is gone
    get_response = client.get(
        f"/admin/dynamic-lists/{list_name}", headers={"Authorization": f"Bearer {admin_token}"})
    assert get_response.status_code == 404

    # Verify item is also gone (due to cascade)
    get_item_response = client.get(
        f"/admin/dynamic-list-items/{item_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert get_item_response.status_code == 404


def test_admin_cannot_create_duplicate_dynamic_list(client: TestClient, admin_token: str):
    list_name = "duplicate_list_name"
    payload = {"list_name": list_name, "description": "First instance"}
    # Clean up if it exists from a previous failed run
    client.delete(f"/admin/dynamic-lists/{list_name}",
                  headers={"Authorization": f"Bearer {admin_token}"})

    response1 = client.post("/admin/dynamic-lists/", json=payload,
                            headers={"Authorization": f"Bearer {admin_token}"})
    assert response1.status_code == 201  # Corrected expected status code

    payload2 = {"list_name": list_name,
                "description": "Second instance attempt"}
    response2 = client.post("/admin/dynamic-lists/", json=payload2,
                            headers={"Authorization": f"Bearer {admin_token}"})
    assert response2.status_code == 400  # Expecting conflict or bad request
    assert "already exists" in response2.json()["detail"].lower()


def test_admin_get_all_dynamic_lists(client: TestClient, admin_token: str):
    # Create a couple of lists to ensure there's something to fetch
    client.post("/admin/dynamic-lists/", json={"list_name": "list_alpha_label", "list_label": "Alpha Label",
                "description": "Alpha"}, headers={"Authorization": f"Bearer {admin_token}"})
    client.post("/admin/dynamic-lists/", json={"list_name": "list_beta_label", "list_label": "Beta Label",
                "description": "Beta"}, headers={"Authorization": f"Bearer {admin_token}"})

    response = client.get("/admin/dynamic-lists/",
                          headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    fetched_lists = {lst["list_name"]: lst for lst in data}
    assert "list_alpha_label" in fetched_lists
    assert fetched_lists["list_alpha_label"]["list_label"] == "Alpha Label"
    assert "list_beta_label" in fetched_lists
    assert fetched_lists["list_beta_label"]["list_label"] == "Beta Label"
    
    list_names_fetched = [lst["list_name"] for lst in data]
    # Check sorting by list_name (as per crud.get_dynamic_lists)
    if len(data) >= 2 and "list_alpha_label" in list_names_fetched and "list_beta_label" in list_names_fetched:
        # This assertion depends on the exact list names and their alphabetical order
        # Adjust if list_names are different or sorting changes
        sorted_test_list_names = sorted(["list_alpha_label", "list_beta_label"])
        # Find the indices of our test lists in the fetched data
        idx_alpha = -1
        idx_beta = -1
        for i, lst in enumerate(data):
            if lst["list_name"] == "list_alpha_label":
                idx_alpha = i
            elif lst["list_name"] == "list_beta_label":
                idx_beta = i
        
        # Only assert order if both are found and their expected order is known
        if idx_alpha != -1 and idx_beta != -1:
             if "list_alpha_label" == sorted_test_list_names[0]: # if alpha comes before beta
                 assert idx_alpha < idx_beta
             else:
                 assert idx_beta < idx_alpha


def test_admin_get_specific_dynamic_list(client: TestClient, admin_token: str):
    list_name = "specific_list_test_label"
    list_label = "Specific Label for Test"
    description = "Specific list for testing get by name with label"
    client.post("/admin/dynamic-lists/", json={"list_name": list_name, "list_label": list_label,
                "description": description}, headers={"Authorization": f"Bearer {admin_token}"})

    response = client.get(
        f"/admin/dynamic-lists/{list_name}", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["list_name"] == list_name
    assert data["list_label"] == list_label
    assert data["description"] == description


def test_admin_get_non_existent_dynamic_list_returns_404(client: TestClient, admin_token: str):
    response = client.get("/admin/dynamic-lists/non_existent_list_name_xyz",
                          headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 404


def test_non_admin_cannot_manage_dynamic_lists(client: TestClient, regular_user_token: str):
    list_name = "list_non_admin_test"
    # Create
    response_create = client.post("/admin/dynamic-lists/", json={
                                  "list_name": list_name, "description": "Non-admin attempt"}, headers={"Authorization": f"Bearer {regular_user_token}"})
    assert response_create.status_code == 403

    # Edit (assuming a list name that might exist, or just testing endpoint protection)
    response_edit = client.put(f"/admin/dynamic-lists/{list_name}", json={
                               "description": "Update attempt"}, headers={"Authorization": f"Bearer {regular_user_token}"})
    # Or 404 if list doesn't exist, but 403 should be checked first
    assert response_edit.status_code == 403

    # Delete
    response_delete = client.delete(f"/admin/dynamic-lists/{list_name}", headers={
                                    "Authorization": f"Bearer {regular_user_token}"})
    assert response_delete.status_code == 403  # Or 404

    # Get specific (should also be admin only)
    response_get_specific = client.get(
        f"/admin/dynamic-lists/{list_name}", headers={"Authorization": f"Bearer {regular_user_token}"})
    assert response_get_specific.status_code == 403  # Or 404

    # Get all (should also be admin only)
    response_get_all = client.get(
        "/admin/dynamic-lists/", headers={"Authorization": f"Bearer {regular_user_token}"})
    assert response_get_all.status_code == 403
