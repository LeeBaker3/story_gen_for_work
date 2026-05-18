import os
from sqlalchemy import CheckConstraint, create_engine, Column, Integer, String, Text, ForeignKey, JSON, DateTime, Boolean, UniqueConstraint, Enum, text  # Added Boolean and text
# Import declarative_base from sqlalchemy.orm
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func
from dotenv import load_dotenv
from backend.settings import get_settings

# Load .env for local development (harmless in prod/CI)
load_dotenv()

# DATABASE_URL can be provided via environment; default to local SQLite
DATABASE_URL = get_settings().database_url

# For SQLite, we must pass check_same_thread=False for SQLAlchemy in multi-threaded apps
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith(
    "sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()  # Use the imported declarative_base


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    # Made email unique and nullable
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)  # New field
    # Soft delete flag for admin-controlled deletions
    is_deleted = Column(Boolean, default=False)
    role = Column(String, default="user")  # New field (e.g., "user", "admin")
    password_reset_token_hash = Column(String, nullable=True, index=True)
    password_reset_token_expires_at = Column(
        DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    stories = relationship("Story", back_populates="owner")
    entitlement = relationship(
        "AccountEntitlement",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    usage_ledger_entries = relationship(
        "UsageLedgerEntry",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class AccountEntitlement(Base):
    __tablename__ = "account_entitlements"
    __table_args__ = (
        CheckConstraint(
            "access_state IN ('trial', 'paid-active', 'grace', 'suspended')",
            name="ck_account_entitlements_access_state",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False,
                     unique=True, index=True)
    access_state = Column(String, nullable=False, default="trial")
    story_credits_total = Column(Integer, nullable=False, default=0)
    image_credits_total = Column(Integer, nullable=False, default=0)
    stripe_customer_id = Column(String, nullable=True, index=True)
    stripe_subscription_id = Column(String, nullable=True, index=True)
    current_period_started_at = Column(DateTime(timezone=True), nullable=True)
    trial_started_at = Column(DateTime(timezone=True), nullable=True)
    trial_expires_at = Column(DateTime(timezone=True), nullable=True)
    renews_at = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="entitlement")
    usage_ledger_entries = relationship(
        "UsageLedgerEntry",
        back_populates="entitlement",
        cascade="all, delete-orphan",
    )


class UsageLedgerEntry(Base):
    __tablename__ = "usage_ledger_entries"
    __table_args__ = (
        CheckConstraint(
            "credit_bucket IN ('story', 'image')",
            name="ck_usage_ledger_entries_credit_bucket",
        ),
        CheckConstraint(
            "status IN ('reserved', 'consumed', 'released')",
            name="ck_usage_ledger_entries_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False,
                     index=True)
    entitlement_id = Column(Integer, ForeignKey("account_entitlements.id"),
                            nullable=False, index=True)
    action_type = Column(String, nullable=False, index=True)
    credit_bucket = Column(String, nullable=False, index=True)
    credits = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="reserved", index=True)
    billing_period_start = Column(DateTime(timezone=True), nullable=True)
    finalized_at = Column(DateTime(timezone=True), nullable=True)
    release_reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="usage_ledger_entries")
    entitlement = relationship(
        "AccountEntitlement",
        back_populates="usage_ledger_entries",
    )


class Story(Base):
    __tablename__ = "stories"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    cover_subtitle = Column(String, nullable=True)
    cover_author = Column(String, nullable=True)
    story_outline = Column(Text, nullable=True)  # Changed from outline
    genre = Column(String, nullable=False)
    main_characters = Column(JSON, nullable=True)
    num_pages = Column(Integer, nullable=False, default=0)
    tone = Column(String, nullable=True)
    setting = Column(String, nullable=True)
    writing_style = Column(String, nullable=True)
    # FR14: Added image_style column
    image_style = Column(String, nullable=True, default="Default")
    # FR13: Added word_to_picture_ratio column
    word_to_picture_ratio = Column(
        String, nullable=True, default="One image per page")
    # New Req: Added text_density column (align with schema enum values)
    text_density = Column(
        String,
        nullable=True,
        # Align default with schemas.TextDensity.CONCISE.value
        default="Concise (~30-50 words)",
    )
    owner_id = Column(Integer, ForeignKey("users.id"), index=True)
    # Represents draft creation or story generation time
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())
    # Time of actual story generation, null for drafts
    generated_at = Column(DateTime(timezone=True), nullable=True)
    # True if story is a draft, False if generated
    is_draft = Column(Boolean, default=True, nullable=False)
    # Admin moderation flags
    is_hidden = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    editor_settings = Column(JSON, nullable=True)

    owner = relationship("User", back_populates="stories")
    pages = relationship("Page", back_populates="story",
                         cascade="all, delete-orphan")


class Page(Base):
    __tablename__ = "pages"
    id = Column(Integer, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey("stories.id"), index=True)
    page_number = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    image_description = Column(Text, nullable=True)  # Prompt for DALL-E
    image_path = Column(String, nullable=True)  # Path to locally stored image
    editor_state = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())
    story = relationship("Story", back_populates="pages")

# New Models for Dynamic Lists (FR-ADM-05)


class DynamicList(Base):
    __tablename__ = "dynamic_lists"

    # e.g., "genres", "image_styles"
    list_name = Column(String, primary_key=True, index=True)
    list_label = Column(String, nullable=True)  # User-friendly label
    # Optional description of the list's purpose
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    items = relationship(
        "DynamicListItem", back_populates="parent_list", cascade="all, delete-orphan")


class DynamicListItem(Base):
    __tablename__ = "dynamic_list_items"

    id = Column(Integer, primary_key=True, index=True)
    list_name = Column(String, ForeignKey("dynamic_lists.list_name"))
    item_value = Column(String, nullable=False)  # The actual value of the item
    item_label = Column(String, nullable=True)  # Optional user-friendly label
    is_active = Column(Boolean, default=True)
    # For ordering items within a list
    sort_order = Column(Integer, default=100)
    additional_config = Column(JSON, nullable=True)  # For extra configuration
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    parent_list = relationship("DynamicList", back_populates="items")

    __table_args__ = (UniqueConstraint(
        'list_name', 'item_value', name='_list_value_uc'),)


class StoryGenerationTask(Base):
    __tablename__ = 'story_generation_tasks'
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'failed')",
            name="ck_story_generation_task_status",
        ),
    )

    id = Column(String, primary_key=True, index=True)
    story_id = Column(Integer, ForeignKey('stories.id'),
                      nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'),
                     nullable=False, index=True)
    status = Column(String, nullable=False, default='pending', index=True)
    progress = Column(Integer, default=0)
    current_step = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    # New tracking fields
    # Total retry attempts (incremented on each retry cycle)
    attempts = Column(Integer, nullable=False, default=0)
    # First transition from pending -> in_progress
    started_at = Column(DateTime(timezone=True), nullable=True)
    # When status becomes completed or failed
    completed_at = Column(DateTime(timezone=True), nullable=True)
    # Cached duration (completed_at - started_at) in ms for metrics
    duration_ms = Column(Integer, nullable=True)
    # Persist last encountered error across retries
    last_error = Column(Text, nullable=True)
    retry_counts_by_page = Column(JSON, nullable=True)
    total_retries = Column(Integer, nullable=True)
    failed_pages_count = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        onupdate=func.now(), server_default=func.now())

    story = relationship("Story")
    user = relationship("User")


class AdminBroadcast(Base):
    __tablename__ = "admin_broadcasts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    target_scope = Column(String, nullable=False, default="all_active_users")
    status = Column(String, nullable=False, default="sent")
    recipient_count = Column(Integer, nullable=False, default=0)
    created_by_user_id = Column(
        Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=False,
                     server_default=func.now())

    created_by = relationship("User")


# --- Characters Domain (Phase 2) ---


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"),
                     nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    clothing_style = Column(String, nullable=True)
    key_traits = Column(Text, nullable=True)
    image_style = Column(String, nullable=True)
    # use_alter=True marks this FK as part of a known cycle so metadata.drop/create won't warn
    current_image_id = Column(
        Integer,
        ForeignKey("character_images.id", use_alter=True,
                   name="fk_characters_current_image_id"),
        nullable=True,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True),
                        server_default=func.now(), onupdate=func.now())

    owner = relationship("User")
    images = relationship(
        "CharacterImage",
        back_populates="character",
        cascade="all, delete-orphan",
        # Disambiguate: CharacterImage.character_id points to Character.id
        foreign_keys="CharacterImage.character_id",
        primaryjoin=lambda: Character.id == CharacterImage.character_id,
    )
    current_image = relationship(
        "CharacterImage",
        foreign_keys=[current_image_id],
        post_update=True,
        uselist=False,
    )


class CharacterImage(Base):
    __tablename__ = "character_images"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(
        Integer,
        ForeignKey("characters.id", use_alter=True,
                   name="fk_character_images_character_id"),
        nullable=False,
        index=True,
    )
    # Relative to data/ (e.g., images/user_1/characters/5/uuid.png)
    file_path = Column(String, nullable=False)
    prompt_used = Column(Text, nullable=True)
    image_style = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Disambiguate relationship path back to Character
    character = relationship(
        "Character",
        back_populates="images",
        foreign_keys=[character_id],
        primaryjoin=lambda: CharacterImage.character_id == Character.id,
    )


class ProcessedStripeEvent(Base):
    __tablename__ = "processed_stripe_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, nullable=False, unique=True, index=True)
    event_type = Column(String, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=False,
                          server_default=func.now())


def create_db_and_tables():
    """Apply runtime schema bootstrap only in local dev/test posture."""

    settings = get_settings()
    if not settings.runtime_schema_bootstrap_enabled:
        return False

    Base.metadata.create_all(bind=engine)
    if settings.database_scheme == "sqlite":
        _ensure_story_generation_task_new_columns()
        _ensure_soft_delete_and_moderation_columns()
        _ensure_story_metadata_columns()
        _ensure_story_editor_columns()
        _ensure_user_password_reset_columns()
        _ensure_billing_columns()
    return True


def _ensure_story_generation_task_new_columns():
    """Idempotently add newly introduced tracking columns for StoryGenerationTask in SQLite.

    This avoids a hard migration requirement for development/test environments. In production, a
    proper migration (Alembic) should be applied instead. Safe to run repeatedly.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return
    required_columns = {
        "attempts": "INTEGER DEFAULT 0",
        "started_at": "TIMESTAMP NULL",
        "completed_at": "TIMESTAMP NULL",
        "duration_ms": "INTEGER NULL",
        "last_error": "TEXT NULL",
        "retry_counts_by_page": "JSON NULL",
        "total_retries": "INTEGER NULL",
        "failed_pages_count": "INTEGER NULL",
    }
    with engine.connect() as conn:
        try:
            existing = set()
            for row in conn.execute(text("PRAGMA table_info(story_generation_tasks)")):
                # row[1] is the column name in PRAGMA output
                existing.add(row[1])
            for col, ddl in required_columns.items():
                if col not in existing:
                    try:
                        conn.execute(
                            text(f"ALTER TABLE story_generation_tasks ADD COLUMN {col} {ddl}"))
                    except Exception:
                        # Ignore if racing or not supported
                        pass
        except Exception:
            # Swallow any inspection errors silently (non-fatal for app start)
            pass


def _ensure_soft_delete_and_moderation_columns():
    """Idempotently add soft-delete/moderation columns for Users and Stories in SQLite.

    This mirrors the approach used for StoryGenerationTask new columns to keep
    dev/test environments working without formal migrations. In production,
    prefer Alembic migrations.
    """
    if not DATABASE_URL.startswith("sqlite"):
        return
    tables_required_cols = {
        "users": {
            "is_deleted": "BOOLEAN DEFAULT 0",
        },
        "stories": {
            "is_hidden": "BOOLEAN DEFAULT 0",
            "is_deleted": "BOOLEAN DEFAULT 0",
        },
    }
    with engine.connect() as conn:
        for table_name, cols in tables_required_cols.items():
            try:
                existing = set()
                for row in conn.execute(text(f"PRAGMA table_info({table_name})")):
                    existing.add(row[1])
                for col, ddl in cols.items():
                    if col not in existing:
                        try:
                            conn.execute(
                                text(
                                    f"ALTER TABLE {table_name} ADD COLUMN {col} {ddl}")
                            )
                        except Exception:
                            # Ignore if racing or not supported
                            pass
            except Exception:
                # Non-fatal in dev/test
                pass


def _ensure_story_metadata_columns():
    """Idempotently add newer story metadata columns for SQLite dev/test use."""

    if not DATABASE_URL.startswith("sqlite"):
        return

    tables_required_cols = {
        "stories": {
            "writing_style": "TEXT NULL",
            "cover_subtitle": "TEXT NULL",
            "cover_author": "TEXT NULL",
        },
    }

    with engine.connect() as conn:
        for table_name, cols in tables_required_cols.items():
            try:
                existing = set()
                for row in conn.execute(text(f"PRAGMA table_info({table_name})")):
                    existing.add(row[1])
                for col, ddl in cols.items():
                    if col not in existing:
                        try:
                            conn.execute(
                                text(
                                    f"ALTER TABLE {table_name} ADD COLUMN {col} {ddl}"
                                )
                            )
                        except Exception:
                            pass
            except Exception:
                pass


def _ensure_story_editor_columns():
    """Idempotently add story/page editor columns for SQLite dev/test use."""

    if not DATABASE_URL.startswith("sqlite"):
        return

    tables_required_cols = {
        "stories": {
            "editor_settings": "JSON NULL",
        },
        "pages": {
            "editor_state": "JSON NULL",
        },
    }

    with engine.connect() as conn:
        for table_name, cols in tables_required_cols.items():
            try:
                existing = set()
                for row in conn.execute(text(f"PRAGMA table_info({table_name})")):
                    existing.add(row[1])
                for col, ddl in cols.items():
                    if col not in existing:
                        try:
                            conn.execute(
                                text(
                                    f"ALTER TABLE {table_name} ADD COLUMN {col} {ddl}")
                            )
                        except Exception:
                            pass
            except Exception:
                pass


def _ensure_user_password_reset_columns():
    """Idempotently add password reset columns for SQLite dev/test use."""

    if not DATABASE_URL.startswith("sqlite"):
        return

    required_columns = {
        "password_reset_token_hash": "TEXT NULL",
        "password_reset_token_expires_at": "TIMESTAMP NULL",
    }

    with engine.connect() as conn:
        try:
            existing = set()
            for row in conn.execute(text("PRAGMA table_info(users)")):
                existing.add(row[1])
            for col, ddl in required_columns.items():
                if col not in existing:
                    try:
                        conn.execute(
                            text(f"ALTER TABLE users ADD COLUMN {col} {ddl}")
                        )
                    except Exception:
                        pass
        except Exception:
            pass


def _ensure_billing_columns():
    """Idempotently add billing-related columns for SQLite dev/test use."""

    if not DATABASE_URL.startswith("sqlite"):
        return

    tables_required_cols = {
        "account_entitlements": {
            "stripe_customer_id": "TEXT NULL",
            "stripe_subscription_id": "TEXT NULL",
            "current_period_started_at": "TIMESTAMP NULL",
            "cancel_at_period_end": "BOOLEAN DEFAULT 0 NOT NULL",
        },
        "usage_ledger_entries": {
            "billing_period_start": "TIMESTAMP NULL",
        },
    }

    with engine.connect() as conn:
        for table_name, cols in tables_required_cols.items():
            try:
                existing = set()
                for row in conn.execute(text(f"PRAGMA table_info({table_name})")):
                    existing.add(row[1])
                for col, ddl in cols.items():
                    if col not in existing:
                        try:
                            conn.execute(
                                text(f"ALTER TABLE {table_name} ADD COLUMN {col} {ddl}")
                            )
                        except Exception:
                            pass
            except Exception:
                pass
