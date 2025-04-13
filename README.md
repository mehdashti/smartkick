# SmartKick Football API ⚽️

A FastAPI-based backend application designed to fetch, process, store, and serve football (soccer) data, primarily using the [API-Football](https://www.api-football.com/) external API.

## Description

This project provides a RESTful API interface to access football data such as player information, team details, game fixtures, live game events (potentially via background tasks), and supported timezones. It leverages asynchronous programming with FastAPI and `httpx` for efficient handling of I/O operations, especially when dealing with external API calls and database interactions. It also potentially utilizes Celery for background task processing, like periodically fetching live game data.

## Features ✨

*   **FastAPI Backend:** Modern, fast (high-performance) web framework for building APIs.
*   **Asynchronous:** Built with `async` and `await` for non-blocking I/O.
*   **API-Football Integration:** Fetches data from the v3 API-Football service.
*   **Endpoints:**
    *   `/players/{player_id}`: Get details for a specific player.
    *   `/teams/{team_id}`: Get details for a specific team.
    *   `/games/{game_id}`: Get details for a specific game (potentially including live data).
    *   `/meta/timezones`: Get a list of supported timezones from API-Football.
    *   *(Potentially more endpoints for leagues, fixtures, live scores, etc.)*
*   **Background Tasks (Celery):** For scheduled or long-running tasks like fetching live game data periodically without blocking API responses.
*   **Database Integration:** (Assumed) Stores fetched data for caching and serving frequently requested information efficiently (e.g., using SQLAlchemy async, Motor for MongoDB).
*   **Configuration Management:** Uses `.env` files and Pydantic settings for managing configuration and secrets.
*   **Automatic API Docs:** Interactive API documentation available via Swagger UI (`/docs`) and ReDoc (`/redoc`).

## Tech Stack 🛠️

*   **Backend:** FastAPI, Uvicorn
*   **HTTP Client:** HTTPX (for async requests)
*   **Data Validation:** Pydantic
*   **Task Queue:** Celery (with a broker like Redis or RabbitMQ)
*   **Database:** (Specify your database, e.g., PostgreSQL with SQLAlchemy async, MongoDB with Motor)
*   **Configuration:** Pydantic-Settings
*   **Language:** Python 3.10+

## Getting Started 🚀

Follow these instructions to set up the project locally or on your server.

### Prerequisites

*   Python 3.10 or higher
*   Pip package manager
*   Git
*   A message broker installed and running (e.g., Redis or RabbitMQ) if using Celery.
*   A database system installed and running (e.g., PostgreSQL, MongoDB).
*   An API Key from [API-Football](https://www.api-football.com/).

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/mehdashti/smartkick.git
    cd smartkick
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    # On Linux/macOS
    source venv/bin/activate
    # On Windows
    # .\venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    *   Create a `.env` file in the project root directory.
    *   Copy the contents of `.env.example` (if you create one) or add the required variables manually.
    *   **Example `.env` content:**
        ```dotenv
        # API-Football Credentials
        API_FOOTBALL_KEY="YOUR_API_FOOTBALL_KEY_HERE"
        API_FOOTBALL_HOST="v3.football.api-sports.io"

        # Database URL (Adjust based on your DB)
        # Example for async PostgreSQL:
        DATABASE_URL="postgresql+asyncpg://user:password@host:port/dbname"
        # Example for MongoDB:
        # DATABASE_URL="mongodb://user:password@host:port/"

        # Celery Broker URL (Adjust based on your broker)
        # Example for Redis:
        CELERY_BROKER_URL="redis://localhost:6379/0"
        # Example for RabbitMQ:
        # CELERY_BROKER_URL="amqp://guest:guest@localhost:5672//"

        # (Add any other necessary environment variables)
        ```
    *   **Important:** Replace placeholders with your actual credentials and settings. **Never commit your `.env` file to Git!** Ensure it's listed in your `.gitignore` file.

5.  **Database Setup:**
    *   Ensure your database server is running.
    *   If using a relational database with migrations (e.g., Alembic with SQLAlchemy), run the migrations:
        ```bash
        # Example command (adjust if needed)
        # alembic upgrade head
        ```
    *   *(Add specific instructions here if needed for database creation or seeding)*

### Running the Application

1.  **Run the FastAPI server:**
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    *   `--reload` is useful for development as it automatically restarts the server on code changes.
    *   The API will be accessible at `http://localhost:8000` (or your server's IP).

2.  **Run the Celery worker (if using background tasks):**
    Open a **new terminal window**, activate the virtual environment, and run:
    ```bash
    celery -A worker.celery_app worker --loglevel=info
    ```

3.  **Run Celery Beat (if using scheduled tasks):**
    Open **another new terminal window**, activate the virtual environment, and run:
    ```bash
    celery -A worker.celery_app beat --loglevel=info
    ```

## API Documentation 📚

Once the FastAPI server is running, you can access the interactive API documentation:

*   **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
*   **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Environment Variables ⚙️

The following environment variables are required (typically set in the `.env` file):

*   `API_FOOTBALL_KEY`: Your secret API key for API-Football.
*   `API_FOOTBALL_HOST`: The host for the API-Football service (usually `v3.football.api-sports.io`).
*   `DATABASE_URL`: The connection string for your database.
*   `CELERY_BROKER_URL`: The connection string for your Celery message broker.
*   *(List any other custom environment variables)*

## Running Tests ✅

*(Assuming you will use pytest)*

To run the test suite:

```bash
pytest