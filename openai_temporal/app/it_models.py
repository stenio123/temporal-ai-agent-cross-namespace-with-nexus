"""
IT Operation Input Models
Pydantic models for IT Nexus operation inputs
Following Temporal best practice: always use objects for parameters
"""
from pydantic import BaseModel, Field


class JiraMetricsInput(BaseModel):
    """Input for jira_metrics operation"""
    project: str = Field(description="JIRA project identifier")
