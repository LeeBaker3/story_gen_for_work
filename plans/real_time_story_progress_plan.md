# Real-Time Story Generation Progress Plan (FastAPI)

## 1. Backend Changes

### a. Database Model
- **Add `status` and `status_message` fields** to the `Story` model (or a related `StoryGenerationTask` model).
- **Status values** (enum or string):
  - `PENDING`
  - `GENERATING_OUTLINE`
  - `GENERATING_REFERENCE_IMAGES`
  - `GENERATING_PAGE_IMAGE_{n}`
  - `COMPLETE`
  - `FAILED`

### b. State Machine
- Update the story's `status` and `status_message` in the DB at each major step in the generation process.

### c. Background Task
- Move story generation to a FastAPI `BackgroundTasks` task.
- The `/stories/` endpoint should return immediately with the new story ID and initial status.

### d. Status Endpoint
- Add a new endpoint: `GET /stories/{story_id}/status`
- Returns:
  ```json
  {
    "status": "GENERATING_PAGE_IMAGE_2",
    "status_message": "Generating image for page 2"
  }
  ```

### e. Naming Consistency
- Use consistent naming (snake_case or camelCase) for status keys/values in both backend and frontend.
- Document all possible status values in a shared location (e.g., a constants file).

---

## 2. Frontend Changes

### a. Trigger Story Generation
- On story creation, **store the returned story ID**.

### b. Polling for Status
- Implement polling (e.g., every 2 seconds) to `/stories/{story_id}/status`.
- Update the info/message window with the latest `status_message` from the backend.

### c. UI Updates
- Show intermediate messages (e.g., "Generating outline...", "Generating image for page 1...").
- Stop polling and show the final result when status is `COMPLETE` or `FAILED`.

### d. Naming Consistency
- Ensure the frontend expects and displays the same status keys/values as the backend.

---

## 3. Integration Points & Naming

- **API contract:**
  - `/stories/` (POST): returns `{ story_id, status, status_message }`
  - `/stories/{story_id}/status` (GET): returns `{ status, status_message }`
- **Status values:**
  - Use a shared enum or documented list for both frontend and backend.
- **Status message:**
  - Always provide a human-readable message for the frontend to display.

---

## 4. Test Case Updates

### a. Backend
- Test that the story's status is updated correctly at each step.
- Test the `/status` endpoint returns the correct status and message.
- Test error handling (e.g., status becomes `FAILED` on exceptions).

### b. Frontend
- Test that the UI polls and updates messages as the status changes.
- Test that polling stops and the UI updates correctly on `COMPLETE` or `FAILED`.
- Mock backend responses for various status values.

---

## 5. Summary Table

| Step                | Backend Change                        | Frontend Change                | Integration Point                |
|---------------------|---------------------------------------|-------------------------------|----------------------------------|
| DB Model            | Add `status`, `status_message` fields |                               |                                  |
| State Machine       | Update status at each step            |                               | Shared status values             |
| Background Task     | Move generation to background         |                               |                                  |
| Status Endpoint     | Add `/stories/{id}/status`            | Poll this endpoint            | `/stories/{id}/status`           |
| Naming Consistency  | Use consistent status keys/values     | Use same keys/values          | Documented/shared enum           |
| UI Polling          |                                       | Poll and update message window| `/stories/{id}/status`           |
| Test Cases          | Test status updates and endpoint      | Test polling and UI updates   | Mocked API responses             |

---

**Next Steps:**
- Confirm your preferred background task approach (FastAPI `BackgroundTasks`).
- Decide on the status values and naming convention.
- Implement backend changes, then frontend polling, then update tests.

---

*This plan ensures no duplication or loss of functionality and provides a clear path for real-time progress updates in story generation.*
