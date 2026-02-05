"""
IT Worker - runs in it-namespace
Handles IT tool workflows - triggered by IT MCP HTTP server
"""
import asyncio
import logging

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

# Configure logging to show INFO level messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

import app.it_activities as it_activities
from app.it_workflows import GetIPWorkflow, GetJiraMetricsWorkflow
from app.shared import NAMESPACE_IT, QUEUE_IT, TEMPORAL_ADDRESS


async def main():
    """Start the IT worker"""

    # Connect to IT namespace with Pydantic data converter
    client = await Client.connect(
        TEMPORAL_ADDRESS,
        namespace=NAMESPACE_IT,
        data_converter=pydantic_data_converter,
    )

    # Create worker with workflows and activities
    worker = Worker(
        client,
        task_queue=QUEUE_IT,
        workflows=[
            GetIPWorkflow,
            GetJiraMetricsWorkflow,
        ],
        activities=[
            it_activities.jira_metrics,
            it_activities.get_ip,
        ],
    )

    print("=" * 60)
    print("IT Worker started!")
    print(f"Namespace: {NAMESPACE_IT}")
    print(f"Task Queue: {QUEUE_IT}")
    print(f"Workflows: GetIPWorkflow, GetJiraMetricsWorkflow")
    print(f"Activities: jira_metrics, get_ip")
    print(f"Triggered by: IT MCP HTTP server (port 8002)")
    print("=" * 60)
    print("Press Ctrl+C to stop")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
