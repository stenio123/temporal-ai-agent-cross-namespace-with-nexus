"""
IT Nexus Handler
Exposes IT tools to other namespaces via Nexus (individual operations)
Based on: https://docs.temporal.io/develop/python/nexus

Following Temporal best practice: Nexus operations backed by workflows (not activities)
"""
import uuid
import nexusrpc
from temporalio import nexus

from app.it_models import JiraMetricsInput
from app.it_service import ITService
from app.it_workflows import GetIPWorkflow, GetJiraMetricsWorkflow


@nexusrpc.handler.service_handler(service=ITService)
class ITNexusHandler:
    """
    Nexus handler for IT namespace.
    Each tool is a separate operation with explicit types.
    Operations start durable workflows (Temporal best practice).
    """

    @nexus.workflow_run_operation
    async def jira_metrics(
        self,
        ctx: nexus.WorkflowRunOperationContext,
        input: JiraMetricsInput
    ) -> nexus.WorkflowHandle[str]:
        """
        Get JIRA project metrics.
        Starts a durable workflow for execution.

        Args:
            input: JIRA metrics input with project identifier

        Returns:
            Workflow handle for JIRA metrics result
        """
        return await ctx.start_workflow(
            GetJiraMetricsWorkflow.run,
            input,
            id=f"jira-metrics-{input.project}-{uuid.uuid4()}",
        )

    @nexus.workflow_run_operation
    async def get_ip(
        self,
        ctx: nexus.WorkflowRunOperationContext,
        input: None
    ) -> nexus.WorkflowHandle[str]:
        """
        Get current IP address.
        Starts a durable workflow for execution.

        Returns:
            Workflow handle for IP address result
        """
        return await ctx.start_workflow(
            GetIPWorkflow.run,
            id=f"get-ip-{uuid.uuid4()}",
        )
