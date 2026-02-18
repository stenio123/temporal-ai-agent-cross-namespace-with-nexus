"""
IT Nexus Handler
Exposes IT tools to other namespaces via Nexus (individual operations)
Based on: https://docs.temporal.io/develop/python/nexus

Following Temporal best practice: Nexus operations backed by workflows (not activities)
"""
import uuid
import nexusrpc
from nexusrpc.handler import StartOperationContext, sync_operation
from temporalio.client import Client

from nexusmcp import MCPServiceHandler

from app.it_models import GetIPInput, JiraMetricsInput
from app.it_service import ITService
from app.it_workflows import GetIPWorkflow, GetJiraMetricsWorkflow
from app.shared import QUEUE_IT


# Create MCPServiceHandler registry for tool discovery
mcp_service = MCPServiceHandler()


@mcp_service.register
@nexusrpc.handler.service_handler(service=ITService)
class ITNexusHandler:
    """
    Nexus handler for IT namespace.
    Each tool is a separate operation with explicit types.
    Operations start durable workflows (Temporal best practice).
    """

    def __init__(self, client: Client):
        """
        Initialize handler with Temporal client for workflow execution.

        Args:
            client: Temporal client for starting workflows
        """
        self.client = client

    @sync_operation
    async def jira_metrics(
        self,
        ctx: StartOperationContext,
        input: JiraMetricsInput
    ) -> str:
        """
        Get JIRA project metrics.
        Starts a durable workflow for execution.

        Args:
            input: JIRA metrics input with project identifier

        Returns:
            JIRA metrics result
        """
        result = await self.client.execute_workflow(
            GetJiraMetricsWorkflow.run,
            input,
            id=f"jira-metrics-{input.project}-{uuid.uuid4()}",
            task_queue=QUEUE_IT,
        )
        return result

    @sync_operation
    async def get_ip(
        self,
        ctx: StartOperationContext,
        input: GetIPInput
    ) -> str:
        """
        Get current IP address.
        Starts a durable workflow for execution.

        Args:
            input: Empty input model (no parameters needed)

        Returns:
            IP address result
        """
        result = await self.client.execute_workflow(
            GetIPWorkflow.run,
            id=f"get-ip-{uuid.uuid4()}",
            task_queue=QUEUE_IT,
        )
        return result
