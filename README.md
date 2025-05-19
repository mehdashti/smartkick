# SmartKick Football API ⚽️

A FastAPI-based backend application designed to fetch, process, store, and serve football (soccer) data, primarily using the [API-Football](https://www.api-football.com/) external API.

---

## Architecture Overview 🏗️

The project follows a layered architecture to ensure modularity, scalability, and maintainability. Below is a summary of the key layers and their responsibilities:

### 1. **Router Layer**
- **Purpose:** Handles HTTP requests and responses.
- **Responsibilities:**
  - Defines API endpoints using FastAPI.
  - Validates user input and returns appropriate responses.
  - Delegates business logic to the service layer or queues tasks for Celery.
- **Example:**
  - Endpoint `/admin/venues/update-by-country` queues a Celery task to update venue data for a specific country.

---

### 2. **Task Layer**
- **Purpose:** Manages long-running or background tasks using Celery.
- **Responsibilities:**
  - Executes operations that are time-consuming or need to run asynchronously.
  - Uses `asyncio.run` to execute asynchronous methods in synchronous Celery tasks.
  - Handles errors and returns task results.
- **Example:**
  - Task `update_venues_by_country_task` fetches venue data for a country and updates the database.

---

### 3. **Service Layer**
- **Purpose:** Implements business logic.
- **Responsibilities:**
  - Processes data and applies business rules.
  - Interacts with the repository layer to perform database operations.
- **Example:**
  - A service method fetches venue data from an external API, processes it, and calls the repository to update the database.

---

### 4. **Repository Layer**
- **Purpose:** Handles direct interactions with the database.
- **Responsibilities:**
  - Executes CRUD operations using SQLAlchemy.
  - Uses `AsyncSession` for asynchronous database interactions.
  - Delegates transaction management to the caller (e.g., service or task layer).
- **Example:**
  - The `VenueRepository` class provides methods like `upsert_venue` and `bulk_upsert_venues` for efficient database updates.

---

### 5. **Database Layer**
- **Purpose:** Manages database connections and sessions.
- **Responsibilities:**
  - Configures the database engine and session maker.
  - Provides `AsyncSession` instances for use in other layers.
  - Implements FastAPI dependencies like `get_async_db_session`.
- **Example:**
  - The `async_session` method creates and returns an `AsyncSession`.

---

## Data Flow 🔄

1. **User Request:**
   - A user sends an HTTP request to a FastAPI endpoint.
   - The router validates the request and either calls a service method or queues a Celery task.

2. **Task Execution:**
   - Celery executes the task, which interacts with the service and repository layers to perform the required operations.

3. **Database Interaction:**
   - The repository layer executes database queries using `AsyncSession`.
   - Transaction management (e.g., `commit` or `rollback`) is handled by the service or task layer.

4. **Response:**
   - The result of the operation is returned to the user or stored in Redis for later retrieval.

---

## Key Features ✨

- **FastAPI Backend:** High-performance web framework for building APIs.
- **Asynchronous Programming:** Uses `async` and `await` for non-blocking I/O operations.
- **Celery Integration:** Handles background tasks like data fetching and processing.
- **Database Support:** Uses SQLAlchemy with PostgreSQL for relational data storage.
- **Interactive API Docs:** Automatically generated Swagger UI and ReDoc documentation.
- **Environment Configuration:** Manages settings using `.env` files and Pydantic.

---

## Tech Stack 🛠️

- **Backend Framework:** FastAPI
- **Task Queue:** Celery (with Redis as the broker and backend)
- **Database:** PostgreSQL (via SQLAlchemy async)
- **HTTP Client:** HTTPX
- **Configuration Management:** Pydantic
- **Language:** Python 3.10+

---

## Getting Started 🚀

### Prerequisites

- Python 3.10 or higher
- Redis (for Celery)
- PostgreSQL (or another supported database)
- API Key from [API-Football](https://www.api-football.com/)

### Installation

1. **Clone the repository:**
    ```bash
    git clone https://github.com/mehdashti/smartkick.git
    cd smartkick
    ```

2. **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    # .\venv\Scripts\activate  # On Windows
    ```

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Configure environment variables:**
    - Create a `.env` file in the project root.
    - Add the required variables (e.g., `DATABASE_URL`, `CELERY_BROKER_URL`, `API_FOOTBALL_KEY`).

5. **Run database migrations (if applicable):**
    ```bash
    alembic upgrade head
    ```

---

## Running the Application

1. **Start the FastAPI server:**
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```

2. **Start the Celery worker:**
    ```bash
    celery -A app.core.celery_app worker --loglevel=info
    ```

3. **Start Celery Beat (if using scheduled tasks):**
    ```bash
    celery -A app.core.celery_app beat --loglevel=info
    ```

---

## API Documentation 📚

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## Environment Variables ⚙️

- `API_FOOTBALL_KEY`: API key for API-Football.
- `DATABASE_URL`: Connection string for the database.
- `CELERY_BROKER_URL`: Connection string for the Celery broker.
- *(Add other variables as needed.)*

---

## Running Tests ✅

To run the test suite:
```bash
pytest
```

---

## Notes 📝

- This project uses a hybrid architecture combining synchronous Celery tasks with asynchronous FastAPI endpoints and database interactions.
- For fully asynchronous Celery tasks, additional configuration and testing are required.