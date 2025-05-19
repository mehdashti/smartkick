# app/schemas/tasks.py
from pydantic import BaseModel

class TaskQueueResponse(BaseModel):
    """Standard response model for endpoints that queue a background task."""
    status: str = "success" # می‌توانید مقدار پیش‌فرض هم بگذارید
    message: str
    task_id: str