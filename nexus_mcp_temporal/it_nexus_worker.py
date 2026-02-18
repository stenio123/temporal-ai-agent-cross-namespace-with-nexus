"""
IT Nexus Worker - runs in it-namespace
Handles IT tools and exposes them via Nexus
Based on: https://docs.temporal.io/develop/python/nexus

Following Temporal best practice: Nexus operations backed by workflows
"""
import asyncio
import logging

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

# Configure logging to show INFO level messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from app.it_activities import ITActivities
from app.it_nexus_handler import ITNexusHandler, mcp_service
from app.it_workflows import GetIPWorkflow, GetJiraMetricsWorkflow
from app.shared import NAMESPACE_IT, QUEUE_IT, TEMPORAL_ADDRESS


async def main():
    """Start the IT worker in it-namespace"""

    # Connect to IT namespace with Pydantic data converter
    client = await Client.connect(
        TEMPORAL_ADDRESS,
        namespace=NAMESPACE_IT,
        data_converter=pydantic_data_converter,
    )

    # Create activity instances
    it_activities = ITActivities()

    # Create Nexus service handler instance with client for workflow execution
    nexus_handler = ITNexusHandler(client)

    # Create worker with workflows, activities, and Nexus handlers
    # IMPORTANT: Both nexus_handler and mcp_service are required:
    # - nexus_handler: Provides the actual IT service operations
    # - mcp_service: Provides tool discovery for InboundGateway (list_tools operation)
    worker = Worker(
        client,
        task_queue=QUEUE_IT,
        workflows=[
            GetJiraMetricsWorkflow,
            GetIPWorkflow,
        ],
        activities=[
            it_activities.jira_metrics,
            it_activities.get_ip,
        ],
        nexus_service_handlers=[nexus_handler, mcp_service],
    )

    print("=" * 60)
    print("IT Worker started (with durable workflows)!")
    print(f"Namespace: {NAMESPACE_IT}")
    print(f"Task Queue: {QUEUE_IT}")
    print(f"Workflows: GetJiraMetricsWorkflow, GetIPWorkflow")
    print(f"Nexus Service: ITService")
    print(f"Available tools: jira_metrics, get_ip")
    print(f"Pattern: Nexus operations backed by durable workflows")
    print("=" * 60)
    print("Press Ctrl+C to stop")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
