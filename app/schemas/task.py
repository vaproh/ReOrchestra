from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    action_type: str = Field(..., description="Action type from ACTION_TYPES")
    target_url: str = Field(..., description="Target URL for the action")
    workers_needed: int = Field(default=1, ge=1, description="Number of workers needed")
    priority: int = Field(default=0, description="Priority level")
