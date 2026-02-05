"""
Pydantic Models
Input models for IT operations
Following Temporal best practice: always use objects for parameters
"""
from pydantic import BaseModel, Field


class JiraMetricsInput(BaseModel):
    """Input for jira_metrics operation"""
    project: str = Field(description="JIRA project identifier (e.g., PROJ-123)")
