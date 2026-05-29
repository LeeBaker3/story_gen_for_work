from types import SimpleNamespace

from backend import database


def test_create_db_and_tables_runs_local_runtime_bootstrap(monkeypatch):
    """Dev/test posture should still apply runtime bootstrap helpers."""

    calls: list[str] = []

    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: SimpleNamespace(
            runtime_schema_bootstrap_enabled=True,
            database_scheme="sqlite",
        ),
    )
    monkeypatch.setattr(
        database.Base.metadata,
        "create_all",
        lambda bind=None: calls.append("create_all"),
    )
    monkeypatch.setattr(
        database,
        "_ensure_story_generation_task_new_columns",
        lambda: calls.append("task_cols"),
    )
    monkeypatch.setattr(
        database,
        "_ensure_soft_delete_and_moderation_columns",
        lambda: calls.append("moderation_cols"),
    )
    monkeypatch.setattr(
        database,
        "_ensure_story_metadata_columns",
        lambda: calls.append("story_metadata_cols"),
    )
    monkeypatch.setattr(
        database,
        "_ensure_story_editor_columns",
        lambda: calls.append("story_editor_cols"),
    )
    monkeypatch.setattr(
        database,
        "_ensure_user_password_reset_columns",
        lambda: calls.append("password_reset_cols"),
    )

    assert database.create_db_and_tables() is True
    assert calls == [
        "create_all",
        "task_cols",
        "moderation_cols",
        "story_metadata_cols",
        "story_editor_cols",
        "password_reset_cols",
    ]


def test_create_db_and_tables_skips_runtime_bootstrap_in_migration_mode(
    monkeypatch,
):
    """Staging/prod posture should no longer create or repair schema at runtime."""

    calls: list[str] = []

    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: SimpleNamespace(
            runtime_schema_bootstrap_enabled=False,
            database_scheme="postgresql",
        ),
    )
    monkeypatch.setattr(
        database.Base.metadata,
        "create_all",
        lambda bind=None: calls.append("create_all"),
    )
    monkeypatch.setattr(
        database,
        "_ensure_story_generation_task_new_columns",
        lambda: calls.append("task_cols"),
    )

    assert database.create_db_and_tables() is False
    assert calls == []