import pytest
from sqlalchemy.orm import Session
from backend import crud, schemas
from backend.database import Story, Page, User # For type hinting and instance checks
from fastapi.encoders import jsonable_encoder

# Helper to create a dummy user for story ownership
@pytest.fixture
def test_user(db_session: Session) -> User:
    user_in = schemas.UserCreate(username="storyowner", password="securepassword", email="owner@example.com")
    return crud.create_user(db=db_session, user=user_in)

# Test Story Creation
def test_create_story_db_entry(db_session: Session, test_user: User):
    character1 = schemas.CharacterDetail(name="Hero", description="Brave knight")
    story_data = schemas.StoryBase(
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
    db_story = crud.create_story_db_entry(db=db_session, story_data=story_data, user_id=test_user.id, title=title)
    
    assert db_story is not None
    assert db_story.title == title
    assert db_story.owner_id == test_user.id
    assert db_story.genre == schemas.StoryGenre.FANTASY.value
    assert db_story.num_pages == 5
    assert len(db_story.main_characters) == 1
    assert db_story.main_characters[0]['name'] == "Hero"
    assert isinstance(db_story, Story)

# Test Get Story by ID
def test_get_story(db_session: Session, test_user: User):
    story_data = schemas.StoryBase(genre="Sci-Fi", story_outline="Space adventure", main_characters=[], num_pages=3)
    created_story = crud.create_story_db_entry(db=db_session, story_data=story_data, user_id=test_user.id, title="Galaxy Quest")
    retrieved_story = crud.get_story(db=db_session, story_id=created_story.id)
    
    assert retrieved_story is not None
    assert retrieved_story.id == created_story.id
    assert retrieved_story.title == "Galaxy Quest"

def test_get_story_non_existent(db_session: Session):
    retrieved_story = crud.get_story(db=db_session, story_id=9999)
    assert retrieved_story is None

# Test Get Stories by User
def test_get_stories_by_user(db_session: Session, test_user: User):
    story_data1 = schemas.StoryBase(genre="Comedy", story_outline="Funny story", main_characters=[], num_pages=2)
    crud.create_story_db_entry(db=db_session, story_data=story_data1, user_id=test_user.id, title="Haha Time")
    story_data2 = schemas.StoryBase(genre="Drama", story_outline="Sad story", main_characters=[], num_pages=4)
    crud.create_story_db_entry(db=db_session, story_data=story_data2, user_id=test_user.id, title="Tear Jerker")

    stories = crud.get_stories_by_user(db=db_session, user_id=test_user.id)
    assert len(stories) == 2
    titles = {s.title for s in stories}
    assert "Haha Time" in titles
    assert "Tear Jerker" in titles

# Test Update Story Title
def test_update_story_title(db_session: Session, test_user: User):
    story_data = schemas.StoryBase(genre="Mystery", story_outline="Whodunit", main_characters=[], num_pages=10)
    original_title = "The Initial Clue"
    story = crud.create_story_db_entry(db=db_session, story_data=story_data, user_id=test_user.id, title=original_title)
    
    new_title = "The Final Revelation"
    updated_story = crud.update_story_title(db=db_session, story_id=story.id, new_title=new_title)
    
    assert updated_story is not None
    assert updated_story.title == new_title
    
    refetched_story = crud.get_story(db=db_session, story_id=story.id)
    assert refetched_story.title == new_title

def test_update_story_title_non_existent(db_session: Session):
    updated_story = crud.update_story_title(db=db_session, story_id=8888, new_title="No Such Story")
    assert updated_story is None

# Test Create Story Page
def test_create_story_page(db_session: Session, test_user: User):
    story_data = schemas.StoryBase(genre="Action", story_outline="Big boom", main_characters=[], num_pages=1)
    story = crud.create_story_db_entry(db=db_session, story_data=story_data, user_id=test_user.id, title="Explosion Man")
    
    page_data = schemas.PageCreate(page_number=1, text="First page content", image_description="A big explosion")
    image_path = "/static/images/explosion.jpg"
    db_page = crud.create_story_page(db=db_session, page=page_data, story_id=story.id, image_path=image_path)
    
    assert db_page is not None
    assert db_page.story_id == story.id
    assert db_page.page_number == 1
    assert db_page.text == "First page content"
    assert db_page.image_path == image_path
    assert isinstance(db_page, Page)

# Test Update Story with Pages (Batch Page Creation)
def test_update_story_with_pages(db_session: Session, test_user: User):
    story_data = schemas.StoryBase(genre="Horror", story_outline="Scary stuff", main_characters=[], num_pages=2)
    story = crud.create_story_db_entry(db=db_session, story_data=story_data, user_id=test_user.id, title="Night Terrors")

    pages_create_data = [
        schemas.PageCreate(page_number=1, text="Page 1 text", image_description="Scary monster 1"),
        schemas.PageCreate(page_number=2, text="Page 2 text", image_description="Scary monster 2")
    ]
    image_paths = ["/images/monster1.png", "/images/monster2.png"]
    
    crud.update_story_with_pages(db=db_session, story_id=story.id, pages_data=pages_create_data, image_paths=image_paths)
    
    db_session.refresh(story) # Refresh to load the pages relationship
    assert len(story.pages) == 2
    assert story.pages[0].page_number == 1
    assert story.pages[0].image_path == "/images/monster1.png"
    assert story.pages[1].page_number == 2
    assert story.pages[1].image_path == "/images/monster2.png"

# Test Delete Story DB Entry
def test_delete_story_db_entry(db_session: Session, test_user: User):
    story_data = schemas.StoryBase(genre="Fantasy", story_outline="To be deleted", main_characters=[], num_pages=1)
    story = crud.create_story_db_entry(db=db_session, story_data=story_data, user_id=test_user.id, title="Ephemeral Tale")
    page_data = schemas.PageCreate(page_number=1, text="A page to delete", image_description="fleeting image")
    crud.create_story_page(db=db_session, page=page_data, story_id=story.id, image_path="/img/temp.png")
    
    story_id_to_delete = story.id
    # Verify story and page exist before deletion
    assert crud.get_story(db=db_session, story_id=story_id_to_delete) is not None
    assert db_session.query(Page).filter(Page.story_id == story_id_to_delete).count() == 1
    
    delete_successful = crud.delete_story_db_entry(db=db_session, story_id=story_id_to_delete)
    assert delete_successful is True
    
    # Verify story and page are deleted
    assert crud.get_story(db=db_session, story_id=story_id_to_delete) is None
    assert db_session.query(Page).filter(Page.story_id == story_id_to_delete).count() == 0

def test_delete_story_db_entry_non_existent(db_session: Session):
    delete_successful = crud.delete_story_db_entry(db=db_session, story_id=7777)
    assert delete_successful is False

# Test Update Page Image Path
def test_update_page_image_path(db_session: Session, test_user: User):
    story_data = schemas.StoryBase(genre="Childrens", story_outline="A cute story", main_characters=[], num_pages=1)
    story = crud.create_story_db_entry(db=db_session, story_data=story_data, user_id=test_user.id, title="Picture Book")
    page_data = schemas.PageCreate(page_number=1, text="Once upon a time...", image_description="A friendly sun")
    page = crud.create_story_page(db=db_session, page=page_data, story_id=story.id, image_path="/img/initial.png")
    
    new_image_path = "/img/updated_sun.png"
    updated_page = crud.update_page_image_path(db=db_session, page_id=page.id, image_path=new_image_path)
    
    assert updated_page is not None
    assert updated_page.image_path == new_image_path
    
    refetched_page = db_session.query(Page).filter(Page.id == page.id).first()
    assert refetched_page.image_path == new_image_path

def test_update_page_image_path_non_existent(db_session: Session):
    updated_page = crud.update_page_image_path(db=db_session, page_id=6666, image_path="/img/no_page.png")
    assert updated_page is None
