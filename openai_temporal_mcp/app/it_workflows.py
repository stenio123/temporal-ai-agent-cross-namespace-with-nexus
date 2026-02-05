"""
IT Workflows
Temporal workflows for IT MCP tools (stateless pattern)
Each tool has its own workflow for durability

Following Temporal best practice: Using Pydantic models for all workflow inputs
"""
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

import app.it_activities as it_activities
from app.it_models import JiraMetricsInput


@workflow.defn
class GetIPWorkflow:
    """
    Workflow for getting current IP address.
    Stateless pattern - completes immediately after fetching result.
    """

    @workflow.run
    async def run(self) -> str:
        """
        Get current IP address.

        Returns:
            IP address as formatted string
        """
        result = await workflow.execute_activity(
            it_activities.get_ip,
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=5),
                backoff_coefficient=2.0,
            ),
        )
        return result


@workflow.defn
class GetJiraMetricsWorkflow:
    """
    Workflow for getting JIRA metrics.
    Stateless pattern - completes immediately after fetching result.
    Uses Pydantic model for input (Temporal best practice).
    """

    @workflow.run
    async def run(self, input: JiraMetricsInput) -> str:
        """
        Get JIRA metrics for a project.

        Args:
            input: JIRA metrics input containing project identifier

        Returns:
            JIRA metrics as formatted string
        """
        result = await workflow.execute_activity(
            it_activities.jira_metrics,
            input.project,
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                maximum_attempts=5,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                backoff_coefficient=2.0,
            ),
        )
        return result
