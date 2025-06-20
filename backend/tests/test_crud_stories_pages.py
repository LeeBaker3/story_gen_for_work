import pytest
from sqlalchemy.orm import Session
from backend import crud, schemas
# For type hinting and instance checks
from backend.database import Story, Page, User
from fastapi.encoders import jsonable_encoder

# Helper to create a dummy user for story ownership


@pytest.fixture
def test_user(db_session: Session) -> User:
    user_in = schemas.UserCreate(
        username="storyowner", password="securepassword", email="owner@example.com")
    return crud.create_user(db=db_session, user=user_in)

# Test Story Creation


def test_create_story_db_entry(db_session: Session, test_user: User):
    character1 = schemas.CharacterDetail(
        name="Hero", description="Brave knight")
    story_data = schemas.StoryBase(
        title="The Dragon Slayer",
        genre=schemas.StoryGenre.FANTASY,
        story_outline="A quest to defeat a dragon.",
        main_characters=[character1],
        num_pages=5,
        tone="Epic",
        setting="Medieval kingdom",
        image_style=schemas.ImageStyle.FANTASY_ART,
        word_to_picture_ratio=schemas.WordToPictureRatio.PER_PAGE,
        text_density=schemas.TextDensity.STANDARD
    )
    title = "The Dragon Slayer"
    # When creating a finalized story directly, is_draft should be False
    db_story = crud.create_story_db_entry(
        db=db_session, story_data=story_data, user_id=test_user.id, title=title, is_draft=False)

    assert db_story is not None
    assert db_story.title == title
    assert db_story.owner_id == test_user.id
    assert db_story.genre == schemas.StoryGenre.FANTASY.value
    assert db_story.num_pages == 5
    assert len(db_story.main_characters) == 1
    assert db_story.main_characters[0]['name'] == "Hero"
    assert isinstance(db_story, Story)
    assert db_story.is_draft is False
    assert db_story.generated_at is not None

# Test Get Story by ID


def test_get_story(db_session: Session, test_user: User):
    story_data = schemas.StoryBase(
        title="Galaxy Quest", genre="Sci-Fi", story_outline="Space adventure", main_characters=[], num_pages=3)
    created_story = crud.create_story_db_entry(
        db=db_session, story_data=story_data, user_id=test_user.id, title="Galaxy Quest")
    retrieved_story = crud.get_story(db=db_session, story_id=created_story.id)

    assert retrieved_story is not None
    assert retrieved_story.id == created_story.id
    assert retrieved_story.title == "Galaxy Quest"


def test_get_story_non_existent(db_session: Session):
    retrieved_story = crud.get_story(db=db_session, story_id=9999)
    assert retrieved_story is None

# Test Get Stories by User


def test_get_stories_by_user(db_session: Session, test_user: User):
    story_data1 = schemas.StoryBase(
        title="Haha Time", genre="Comedy", story_outline="Funny story", main_characters=[], num_pages=2)
    crud.create_story_db_entry(
        db=db_session, story_data=story_data1, user_id=test_user.id, title="Haha Time")
    story_data2 = schemas.StoryBase(
        title="Tear Jerker", genre="Drama", story_outline="Sad story", main_characters=[], num_pages=4)
    crud.create_story_db_entry(
        db=db_session, story_data=story_data2, user_id=test_user.id, title="Tear Jerker")

    stories = crud.get_stories_by_user(db=db_session, user_id=test_user.id)
    assert len(stories) == 2
    titles = {s.title for s in stories}
    assert "Haha Time" in titles
    assert "Tear Jerker" in titles

# Test Get Stories by User - including drafts


def test_get_stories_by_user_with_drafts(db_session: Session, test_user: User):
    # Create a finalized story
    story_data1 = schemas.StoryBase(genre="Comedy", story_outline="Funny story", main_characters=[
    ], num_pages=2, title="Haha Time")
    crud.create_story_db_entry(db=db_session, story_data=story_data1,
                               user_id=test_user.id, title="Haha Time", is_draft=False)

    # Create a draft story
    story_data2 = schemas.StoryCreate(title="Tear Jerker Draft", genre="Drama",
                                      story_outline="Sad story draft", main_characters=[], num_pages=4)
    crud.create_story_draft(
        db=db_session, story_data=story_data2, user_id=test_user.id)

    # Get stories including drafts
    stories_with_drafts = crud.get_stories_by_user(
        db=db_session, user_id=test_user.id, include_drafts=True)
    assert len(stories_with_drafts) == 2
    titles_with_drafts = {s.title for s in stories_with_drafts}
    assert "Haha Time" in titles_with_drafts
    assert "Tear Jerker Draft" in titles_with_drafts

    # Get stories excluding drafts (default behavior if we change it, or explicitly False)
    stories_without_drafts = crud.get_stories_by_user(
        db=db_session, user_id=test_user.id, include_drafts=False)
    assert len(stories_without_drafts) == 1
    assert stories_without_drafts[0].title == "Haha Time"
    assert stories_without_drafts[0].is_draft is False

# Test Update Story Title


def test_update_story_title(db_session: Session, test_user: User):
    story_data = schemas.StoryBase(
        title="The Initial Clue", genre="Mystery", story_outline="Whodunit", main_characters=[], num_pages=10)
    original_title = "The Initial Clue"
    story = crud.create_story_db_entry(
        db=db_session, story_data=story_data, user_id=test_user.id, title=original_title)

    new_title = "The Final Revelation"
    updated_story = crud.update_story_title(
        db=db_session, story_id=story.id, new_title=new_title)

    assert updated_story is not None
    assert updated_story.title == new_title

    refetched_story = crud.get_story(db=db_session, story_id=story.id)
    assert refetched_story.title == new_title


def test_update_story_title_non_existent(db_session: Session):
    updated_story = crud.update_story_title(
        db=db_session, story_id=8888, new_title="No Such Story")
    assert updated_story is None

# Test Create Story Page


def test_create_story_page(db_session: Session, test_user: User):
    story_data = schemas.StoryBase(
        title="Explosion Man", genre="Action", story_outline="Big boom", main_characters=[], num_pages=1)
    story = crud.create_story_db_entry(
        db=db_session, story_data=story_data, user_id=test_user.id, title="Explosion Man")

    page_data = schemas.PageCreate(
        page_number=1, text="First page content", image_description="A big explosion")
    image_path = "/static/images/explosion.jpg"
    db_page = crud.create_story_page(
        db=db_session, page=page_data, story_id=story.id, image_path=image_path)

    assert db_page is not None
    assert db_page.story_id == story.id
    assert db_page.page_number == 1
    assert db_page.text == "First page content"
    assert db_page.image_path == image_path
    assert isinstance(db_page, Page)

# Test Update Story with Pages (Batch Page Creation)


def test_update_story_with_pages(db_session: Session, test_user: User):
    story_data = schemas.StoryBase(
        title="Night Terrors", genre="Horror", story_outline="Scary stuff", main_characters=[], num_pages=2)
    story = crud.create_story_db_entry(
        db=db_session, story_data=story_data, user_id=test_user.id, title="Night Terrors")

    pages_create_data = [
        schemas.PageCreate(page_number=1, text="Page 1 text",
                           image_description="Scary monster 1"),
        schemas.PageCreate(page_number=2, text="Page 2 text",
                           image_description="Scary monster 2")
    ]
    image_paths = ["/images/monster1.png", "/images/monster2.png"]

    crud.update_story_with_pages(
        db=db_session, story_id=story.id, pages_data=pages_create_data, image_paths=image_paths)

    db_session.refresh(story)  # Refresh to load the pages relationship
    assert len(story.pages) == 2
    assert story.pages[0].page_number == 1
    assert story.pages[0].image_path == "/images/monster1.png"
    assert story.pages[1].page_number == 2
    assert story.pages[1].image_path == "/images/monster2.png"

# Test Delete Story DB Entry


def test_delete_story_db_entry(db_session: Session, test_user: User):
    story_data = schemas.StoryBase(
        title="Ephemeral Tale", genre="Fantasy", story_outline="To be deleted", main_characters=[], num_pages=1)
    story = crud.create_story_db_entry(
        db=db_session, story_data=story_data, user_id=test_user.id, title="Ephemeral Tale")
    page_data = schemas.PageCreate(
        page_number=1, text="A page to delete", image_description="fleeting image")
    crud.create_story_page(db=db_session, page=page_data,
                           story_id=story.id, image_path="/img/temp.png")

    story_id_to_delete = story.id
    # Verify story and page exist before deletion
    assert crud.get_story(
        db=db_session, story_id=story_id_to_delete) is not None
    assert db_session.query(Page).filter(
        Page.story_id == story_id_to_delete).count() == 1

    delete_successful = crud.delete_story_db_entry(
        db=db_session, story_id=story_id_to_delete)
    assert delete_successful is True

    # Verify story and page are deleted
    assert crud.get_story(db=db_session, story_id=story_id_to_delete) is None
    assert db_session.query(Page).filter(
        Page.story_id == story_id_to_delete).count() == 0


def test_delete_story_db_entry_non_existent(db_session: Session):
    delete_successful = crud.delete_story_db_entry(
        db=db_session, story_id=7777)
    assert delete_successful is False

# Test Update Page Image Path


def test_update_page_image_path(db_session: Session, test_user: User):
    story_data = schemas.StoryBase(
        title="Picture Book", genre="Childrens", story_outline="A cute story", main_characters=[], num_pages=1)
    story = crud.create_story_db_entry(
        db=db_session, story_data=story_data, user_id=test_user.id, title="Picture Book")
    page_data = schemas.PageCreate(
        page_number=1, text="Once upon a time...", image_description="A friendly sun")
    page = crud.create_story_page(
        db=db_session, page=page_data, story_id=story.id, image_path="/img/initial.png")

    new_image_path = "/img/updated_sun.png"
    updated_page = crud.update_page_image_path(
        db=db_session, page_id=page.id, image_path=new_image_path)

    assert updated_page is not None
    assert updated_page.image_path == new_image_path

    refetched_page = db_session.query(Page).filter(Page.id == page.id).first()
    assert refetched_page.image_path == new_image_path


def test_update_page_image_path_non_existent(db_session: Session):
    updated_page = crud.update_page_image_path(
        db=db_session, page_id=6666, image_path="/img/no_page.png")
    assert updated_page is None

# --- Draft Specific Tests ---


def test_create_story_draft(db_session: Session, test_user: User):
    draft_data = schemas.StoryCreate(  # Changed to StoryCreate
        title="The Unsolved Case",  # Added title to StoryCreate
        genre=schemas.StoryGenre.MYSTERY,
        story_outline="A detective solves a case.",
        main_characters=[schemas.CharacterDetail(name="Detective X")],
        num_pages=3,
        # Changed to a valid style, NOIR was added to schema
        image_style=schemas.ImageStyle.NOIR
    )
    db_draft = crud.create_story_draft(
        db=db_session, story_data=draft_data, user_id=test_user.id)

    assert db_draft is not None
    assert db_draft.title == draft_data.title  # Compare with title from draft_data
    assert db_draft.owner_id == test_user.id
    assert db_draft.is_draft is True
    assert db_draft.generated_at is None  # Drafts are not generated yet
    assert db_draft.genre == schemas.StoryGenre.MYSTERY.value


def test_update_story_draft(db_session: Session, test_user: User):
    # First, create a draft
    initial_draft_data = schemas.StoryCreate(
        title="Space Draft v1", genre="Sci-Fi", story_outline="Initial outline", main_characters=[], num_pages=1)
    # initial_title = "Space Draft v1" # Title is in initial_draft_data
    draft_story = crud.create_story_draft(
        db=db_session, story_data=initial_draft_data, user_id=test_user.id)

    # Now, update it
    updated_draft_data = schemas.StoryCreate(  # Changed to StoryCreate
        title="Action Draft v2",  # Added title
        genre=schemas.StoryGenre.ACTION,  # Changed genre
        story_outline="Updated action-packed outline!",  # Changed outline
        main_characters=[schemas.CharacterDetail(
            name="Action Hero")],  # Added character
        num_pages=2,  # Changed num_pages
        tone="Exciting"
    )
    # updated_title = "Action Draft v2" # Title is in updated_draft_data

    updated_db_draft = crud.update_story_draft(
        db=db_session, story_id=draft_story.id, story_update_data=updated_draft_data, user_id=test_user.id)  # Pass user_id

    assert updated_db_draft is not None
    assert updated_db_draft.id == draft_story.id
    # Compare with title from updated_draft_data
    assert updated_db_draft.title == updated_draft_data.title
    assert updated_db_draft.genre == schemas.StoryGenre.ACTION.value
    assert updated_db_draft.story_outline == "Updated action-packed outline!"
    assert len(updated_db_draft.main_characters) == 1
    assert updated_db_draft.main_characters[0]['name'] == "Action Hero"
    assert updated_db_draft.num_pages == 2
    assert updated_db_draft.tone == "Exciting"
    assert updated_db_draft.is_draft is True  # Still a draft
    assert updated_db_draft.generated_at is None


def test_finalize_story_draft(db_session: Session, test_user: User):
    # Create a draft first
    draft_data = schemas.StoryCreate(title="Journey Begins (Draft)", genre="Adventure",
                                     story_outline="A grand journey.", main_characters=[], num_pages=5)
    # draft_title = "Journey Begins (Draft)" # Title is in draft_data
    draft_story = crud.create_story_draft(
        db=db_session, story_data=draft_data, user_id=test_user.id)

    # Finalize it (simulating the process where story_input might be slightly different or confirmed)
    # For this test, we'll assume the draft's current data is what's being finalized.
    # The actual finalize_story_draft function in crud.py takes the story_id and updates its state.
    # It doesn't re-take all story_data as input, but rather marks the existing draft as non-draft.

    finalized_story = crud.finalize_story_draft(
        # Pass user_id and title
        db=db_session, story_id=draft_story.id, user_id=test_user.id, title=draft_data.title)

    assert finalized_story is not None
    assert finalized_story.id == draft_story.id
    # Title remains the same unless explicitly changed by another operation
    assert finalized_story.title == draft_data.title
    assert finalized_story.is_draft is False
    assert finalized_story.generated_at is not None  # Should be set upon finalization
    assert finalized_story.genre == "Adventure"  # Other fields remain


def test_update_story_draft_non_existent(db_session: Session):
    story_update_data = schemas.StoryCreate(
        title="Non Existent Update", genre="Horror", story_outline="test", main_characters=[], num_pages=1)
    updated_draft = crud.update_story_draft(
        # Pass a dummy user_id
        db=db_session, story_id=998877, story_update_data=story_update_data, user_id=12345)
    assert updated_draft is None


def test_finalize_story_draft_non_existent(db_session: Session):
    finalized_story = crud.finalize_story_draft(
        # Pass dummy user_id and title
        db=db_session, story_id=998877, user_id=12345, title="Non Existent Finalization")
    assert finalized_story is None
