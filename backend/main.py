import os
from contextlib import asynccontextmanager
from time import perf_counter
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend import auth, crud, database, schemas, storage_paths
from backend.admin_router import admin_router
from backend.characters_router import router as characters_router
from backend.database import SessionLocal, get_db
from backend.database_seeding import seed_database
from backend.logging_config import app_logger, error_logger
from backend.metrics import (
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    normalize_http_path,
)
from backend.monitoring_router import monitoring_router
from backend.public_router import public_router
from backend.rate_limiting import limiter
from backend.settings import get_settings


database.create_db_and_tables()

settings = get_settings()


class PublicStaticContentFiles(StaticFiles):
    """Serve public data assets while withholding private story image paths."""

    async def get_response(self, path, scope):
        try:
            normalized_path = storage_paths.normalize_data_relative_path(path)
        except ValueError as exc:
            raise StarletteHTTPException(status_code=404) from exc

        if storage_paths.is_private_story_asset_path(normalized_path):
            raise StarletteHTTPException(status_code=404)

        return await super().get_response(normalized_path, scope)


def _recover_stuck_generation_tasks(db: Session) -> int:
    """Mark generation tasks left mid-flight by a server restart as failed."""

    stuck_tasks = db.query(database.StoryGenerationTask).filter(
        database.StoryGenerationTask.status.in_(
            [
                schemas.GenerationTaskStatus.PENDING.value,
                schemas.GenerationTaskStatus.IN_PROGRESS.value,
            ]
        )
    ).all()

    for task in stuck_tasks:
        crud.update_story_generation_task(
            db,
            task.id,
            status=schemas.GenerationTaskStatus.FAILED,
            error_message="Server restarted during generation",
        )
    return len(stuck_tasks)


def _assert_secure_secret_key() -> None:
    """Fail startup outside tests when JWT signing uses a missing or known key."""

    _secret = os.getenv("SECRET_KEY", "")
    if _secret in ("", "your-default-secret-key") and os.getenv("TESTING") != "true":
        raise RuntimeError(
            "SECRET_KEY environment variable is not set or uses the insecure default. "
            "Set a strong SECRET_KEY before starting the application."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_logger.info("Application startup: Checking database for initial data.")
    db = SessionLocal()
    try:
        seed_database(db)
        recovered_count = _recover_stuck_generation_tasks(db)
        if recovered_count:
            app_logger.warning(
                "Marked %s stuck story generation task(s) as failed during startup.",
                recovered_count,
            )
        _assert_secure_secret_key()
    finally:
        db.close()
    yield


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def prometheus_http_metrics(request, call_next):
    """Record basic HTTP request metrics for Prometheus."""

    start = perf_counter()
    response = await call_next(request)
    duration = perf_counter() - start

    route = request.scope.get("route")
    route_template = getattr(route, "path", None)
    path_label = normalize_http_path(
        raw_path=str(request.url.path),
        route_template=route_template if isinstance(route_template, str) else None,
    )

    method = str(request.method)
    status_code = str(getattr(response, "status_code", 0))

    HTTP_REQUESTS_TOTAL.labels(
        method=method,
        path=path_label,
        status_code=status_code,
    ).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(
        method=method,
        path=path_label,
    ).observe(duration)
    return response


admin_prefix = f"{settings.api_prefix}/admin"
app.include_router(admin_router, prefix=admin_prefix, tags=["admin"])
app.include_router(public_router, prefix=settings.api_prefix, tags=["public"])
app.include_router(
    characters_router,
    prefix=settings.api_prefix,
    tags=["characters"],
)
app.include_router(
    monitoring_router,
    prefix=admin_prefix,
    tags=["admin-monitoring"],
)


if settings.mount_frontend_static:
    frontend_dir = settings.frontend_static_dir
    if not os.path.exists(frontend_dir) or not os.path.isdir(frontend_dir):
        app_logger.warning(
            "Frontend directory '%s' not found. Static files for frontend will not be served.",
            frontend_dir,
        )
    else:
        app.mount(
            "/static",
            StaticFiles(directory=frontend_dir),
            name="static_frontend",
        )
        app_logger.info(
            "Mounted frontend static files from directory: %s",
            frontend_dir,
        )

if settings.mount_data_static:
    data_dir = settings.data_dir
    if not os.path.exists(data_dir) or not os.path.isdir(data_dir):
        app_logger.warning(
            "Data directory '%s' not found. Static content will not be served.",
            data_dir,
        )
    else:
        app.mount(
            "/static_content",
            PublicStaticContentFiles(directory=data_dir),
            name="static_content",
        )
        app_logger.info("Mounted static content from directory: %s", data_dir)

if not settings.mount_frontend_static or not settings.mount_data_static:
    app_logger.info(
        "Skipping one or more static mounts based on environment settings."
    )


@app.get("/healthz", tags=["health"])
def healthz():
    """Lightweight liveness/readiness probe."""

    return {"status": "ok"}


@app.get("/")
async def root():
    """Return the root API message."""

    return {"message": "Story Generator API"}


@app.get("/admin/placeholder")
async def admin_placeholder_endpoint(
    current_user: schemas.User = Depends(auth.get_current_admin_user),
):
    """Return a placeholder admin dashboard response."""

    return PlainTextResponse(
        "This is a placeholder for the admin dashboard.",
        media_type="text/plain",
    )


@app.post("/stories/backfill-characters", status_code=status.HTTP_200_OK)
async def backfill_characters_for_user(
    include_drafts: bool = True,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
):
    """Backfill a user's character library from their existing stories."""

    try:
        count = crud.upsert_characters_from_user_stories(
            db,
            current_user.id,
            include_drafts=include_drafts,
        )
        return {"upserted": count}
    except Exception as exc:
        error_logger.error(
            "Failed to backfill characters for user %s: %s",
            current_user.id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred.",
        ) from exc


@app.post("/stories/drafts/", response_model=schemas.Story)
async def create_story_draft_endpoint(
    story_input: schemas.StoryCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user),
):
    """Create a draft story for the current user."""

    app_logger.info(
        "User %s creating a new story draft with input: %s",
        current_user.username,
        story_input.model_dump(exclude_none=True),
    )
    try:
        db_story_draft = crud.create_story_draft(
            db=db,
            story_data=story_input,
            user_id=current_user.id,
        )
        app_logger.info(
            "Story draft created with ID: %s for user %s",
            db_story_draft.id,
            current_user.username,
        )
        return db_story_draft
    except Exception as exc:
        error_logger.error(
            "Error creating story draft for user %s: %s",
            current_user.username,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create story draft.",
        ) from exc


@app.put("/stories/drafts/{story_id}", response_model=schemas.Story)
async def update_story_draft_endpoint(
    story_id: int,
    story_update_data: schemas.StoryCreate,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user),
):
    """Update an existing draft owned by the current user."""

    app_logger.info(
        "User %s updating draft ID %s with data: %s",
        current_user.username,
        story_id,
        story_update_data.model_dump(exclude_none=True),
    )

    existing_draft = crud.get_story(db, story_id=story_id, user_id=current_user.id)
    if (
        existing_draft is None
        or existing_draft.owner_id != current_user.id
        or not existing_draft.is_draft
    ):
        error_logger.warning(
            "User %s attempted to update non-existent or unauthorized draft ID: %s",
            current_user.username,
            story_id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found or not authorized to update",
        )

    try:
        updated_draft = crud.update_story_draft(
            db=db,
            story_id=story_id,
            story_update_data=story_update_data,
            user_id=current_user.id,
        )
        if updated_draft is None:
            error_logger.error(
                "update_story_draft returned None for draft %s for user %s despite initial checks.",
                story_id,
                current_user.username,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft not found during update attempt.",
            )

        app_logger.info(
            "Story draft ID %s updated successfully by user %s",
            updated_draft.id,
            current_user.username,
        )
        return updated_draft
    except HTTPException:
        raise
    except Exception as exc:
        error_logger.error(
            "Error updating story draft ID %s for user %s: %s",
            story_id,
            current_user.username,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update story draft.",
        ) from exc


@app.get("/stories/drafts/{story_id}", response_model=schemas.Story)
async def read_story_draft(
    story_id: int,
    db: Session = Depends(get_db),
    current_user: schemas.User = Depends(auth.get_current_active_user),
):
    """Return one draft story owned by the current user."""

    db_story_draft = crud.get_story_draft(db, story_id=story_id, user_id=current_user.id)
    if db_story_draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    return db_story_draft


@app.get("/tasks/{task_id}", response_model=schemas.StoryGenerationTask)
async def get_story_generation_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: database.User = Depends(auth.get_current_active_user),
):
    """Return the status of a story generation task for the current user."""

    app_logger.info(
        "User %s requested status of story generation task ID: %s",
        current_user.username,
        task_id,
    )
    task = crud.get_story_generation_task(db, task_id=task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to view this task",
        )
    return task


@app.get(
    "/dynamic-lists/{list_name}/items",
    response_model=List[schemas.DynamicListItemPublic],
)
def get_public_list_items_endpoint(
    list_name: str,
    db: Session = Depends(get_db),
):
    """Fetch public-facing items for a dynamic list."""

    db_list = crud.get_dynamic_list(db, list_name=list_name)
    if not db_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dynamic list '{list_name}' not found.",
        )

    return crud.get_public_list_items(db, list_name=list_name)


@app.get(
    "/dynamic-lists/{list_name}/active-items",
    response_model=List[schemas.DynamicListItem],
)
def get_active_list_items(
    list_name: str,
    db: Session = Depends(get_db),
):
    """Fetch active sorted items for a dynamic list."""

    db_list = crud.get_dynamic_list(db, list_name=list_name)
    if not db_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dynamic list '{list_name}' not found.",
        )

    return crud.get_active_dynamic_list_items(db, list_name=list_name)
