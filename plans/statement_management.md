### Revised Implementation Plan: Concurrent Story Generation State Management & Recovery

This plan ensures that the story generation process is robust, recoverable, and fully capable of handling simultaneous requests from different users.

---

#### **Phase 1: Backend Foundation (Multi-User Ready)**

The backend architecture will be designed to handle concurrent tasks, ensuring that each user's generation process is isolated and tracked independently.

1.  **Database Schema for Concurrency:**
    *   I will introduce a new table, `story_generation_tasks`.
    *   To explicitly support multiple users, this table will include a `user_id` and `story_id`. This ensures that every generation task is tied to a specific user and a specific story, allowing for precise tracking and preventing any data overlap.
    *   The table will contain the following columns:
        *   `task_id`: A unique identifier for the generation job.
        *   `story_id`: Foreign key to the `stories` table.
        *   `user_id`: Foreign key to the `users` table.
        *   `status`: The current status (e.g., `PENDING`, `IN_PROGRESS`, `COMPLETED`, `FAILED`).
        *   `current_step`: The specific step the process is on (e.g., `generating_text`, `generating_character_images`).
        *   `retry_attempts`: The number of retries for the current step.
        *   `last_error`: A log of the last error message.

2.  **Asynchronous Task Execution for Concurrency:**
    *   The core of handling multiple users is to process each story generation request as an independent, asynchronous background task.
    *   I will use FastAPI's built-in `BackgroundTasks` feature. When a user submits a story for generation, the server will immediately create a task in the `story_generation_tasks` table and launch a background process to handle it.
    *   This non-blocking approach allows the server to accept new requests from other users immediately, while previous requests continue to run in the background.

3.  **State Management Service:**
    *   The new state management service will be instantiated for each background task, operating solely on the data for that task's specific `story_id` and `user_id`. This ensures each user's story generation is managed in a completely isolated process.

---

#### **Phase 2: API and Resiliency (User-Specific Endpoints)**

The API will be structured to ensure users can only interact with and monitor their own story generation tasks.

1.  **API Endpoint Modifications:**
    *   The story creation endpoint (`POST /api/v1/stories/`) will trigger the background task for the currently authenticated user.
    *   A new status endpoint, `GET /api/v1/stories/{story_id}/generation-status`, will allow the frontend to poll for updates. The backend logic for this endpoint will verify that the requesting user is the owner of the `story_id`, preventing one user from seeing the status of another's story.

2.  **Smart Retry & Error Handling:**
    *   The retry mechanism will be applied on a per-task basis. If one user's story generation fails and enters a retry loop, it will have no impact on the generation processes running for other users.

---

#### **Phase 3: Frontend Integration (Isolated User Experience)**

The user interface will be updated to provide a seamless and isolated experience for each user.

1.  **UI Polling and Status Display:**
    *   After submitting a story, the frontend will poll the status endpoint using the `story_id` of the story it just created. This ensures the UI only displays progress updates relevant to the current user.

2.  **Process Resume and User-Specific Caching:**
    *   The resume capability will be inherently user-specific. If a task is restarted, it will use its `task_id` to retrieve the correct state for that user's story.
    *   The caching mechanism already uses a user-specific file path (`data/images/user_{user_id}/story_{story_id}/`), which naturally prevents any mixing of generated content between users. The resume process will leverage this existing structure.
