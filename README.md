# Story Generator API

## Project Overview

This project is a FastAPI-based backend application that allows users to generate stories with accompanying images based on various inputs. Users can define story outlines, characters, genres, and desired image styles. The application leverages AI services (specifically OpenAI's GPT for text generation and DALL-E for image generation) to create unique story content.

The system supports:
- User authentication (signup and login).
- Creating new stories from scratch.
- Saving story ideas as drafts.
- Finalizing drafts into complete stories.
- Using existing stories as templates for new ones.
- Generating character reference images.
- Generating images for each page of the story.
- Viewing and browsing created stories.
- Exporting stories to PDF.

The frontend is a single-page application built with HTML, CSS, and JavaScript, interacting with the backend API.

## Environment Setup

### Prerequisites

- Python 3.13 (as indicated by the project's virtual environment)
- An OpenAI API Key

### Backend Setup

1.  **Clone the repository (if you haven't already):**
    ```bash
    git clone <your-repository-url>
    cd story_gen_for_work
    ```

2.  **Create and activate a Python virtual environment:**
    The project appears to use a virtual environment located in a directory named `#` (or potentially `.venv` if created with standard tools). If you need to recreate it or set it up fresh:

    ```bash
    python3.13 -m venv .venv 
    source .venv/bin/activate
    ```
    *(On Windows, use `.venv\Scripts\activate`)*

3.  **Install dependencies:**
    Navigate to the backend directory and install the required packages.
    ```bash
    cd backend
    pip install -r requirements.txt
    cd .. 
    ```

4.  **Set up Environment Variables:**
    The application requires an OpenAI API key. Create a `.env` file in the `backend` directory (`story_gen_for_work/backend/.env`) and add your API key:
    ```env
    OPENAI_API_KEY="your_openai_api_key_here"
    ```

## Running the Application

1.  **Start the FastAPI Backend Server:**
    Navigate to the `backend` directory and run Uvicorn:
    ```bash
    cd backend
    uvicorn main:app --reload
    ```
    The backend server will typically start on `http://127.0.0.1:8000`.

2.  **Access the Frontend:**
    Open the `index.html` file from the `frontend` directory in your web browser:
    ```
    file:///path/to/your/project/story_gen_for_work/frontend/index.html
    ```
    Or, if you serve the `frontend` directory via a simple HTTP server, access it through that server's address. The application is configured to serve static files, so once the backend is running, the frontend should be able to make API calls to `http://127.0.0.1:8000`.

## Testing

The project uses Pytest for running automated tests.

1.  **Ensure your virtual environment is activated** and you are in the root directory of the project (`story_gen_for_work`).

2.  **Run the tests:**
    Navigate to the `backend` directory and execute Pytest:
    ```bash
    cd backend
    pytest
    ```
    This command will discover and run all tests located in the `backend/tests` directory.

## Project Structure

-   `backend/`: Contains the FastAPI application (Python).
    -   `main.py`: Main FastAPI application file with API endpoints.
    -   `crud.py`: Functions for database interactions (Create, Read, Update, Delete).
    -   `schemas.py`: Pydantic models for data validation and serialization.
    -   `ai_services.py`: Modules for interacting with OpenAI (GPT and DALL-E).
    -   `auth.py`: Authentication logic (OAuth2).
    -   `database.py`: Database setup and session management.
    -   `pdf_generator.py`: Logic for creating PDF versions of stories.
    -   `requirements.txt`: Python dependencies for the backend.
    -   `tests/`: Contains Pytest unit and integration tests.
    -   `.env` (to be created by user): For storing environment variables like API keys.
-   `frontend/`: Contains the static HTML, CSS, and JavaScript files for the user interface.
    -   `index.html`: The main HTML file.
    -   `script.js`: JavaScript logic for frontend interactions and API calls.
    -   `style.css`: CSS styles for the frontend.
-   `data/`: Directory for storing generated data.
    -   `images/`: Stores generated images for stories and characters.
    -   `logs/`: Stores application logs.
-   `story_generator.db`: SQLite database file (created automatically).
-   `README.md`: This file.
