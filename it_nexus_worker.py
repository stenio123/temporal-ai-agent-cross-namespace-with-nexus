"""
IT Nexus Worker - runs in it-namespace
Handles IT tools and exposes them via Nexus
Based on: https://docs.temporal.io/develop/python/nexus
"""
import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

# Configure logging to show INFO level messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from app.it_activities import ITActivities
from app.it_nexus_handler import ITNexusHandler
from app.shared import NAMESPACE_IT, QUEUE_IT, TEMPORAL_ADDRESS


async def main():
    """Start the IT worker in it-namespace"""

    # Connect to IT namespace
    client = await Client.connect(TEMPORAL_ADDRESS, namespace=NAMESPACE_IT)

    # Create activity instances
    it_activities = ITActivities()

    # Create Nexus service handler instance
    nexus_handler = ITNexusHandler()

    # Create worker
    # Note: nexus_service_handlers (not nexus_handler) per docs
    worker = Worker(
        client,
        task_queue=QUEUE_IT,
        workflows=[],  # No workflows needed for simple demo
        activities=[
            it_activities.jira_metrics,
            it_activities.get_ip,
        ],
        nexus_service_handlers=[nexus_handler],  # List of service handlers
    )

    print("=" * 60)
    print("IT Worker started!")
    print(f"Namespace: {NAMESPACE_IT}")
    print(f"Task Queue: {QUEUE_IT}")
    print(f"Nexus Service: it-tools")
    print(f"Available tools: jira_metrics, get_ip")
    print("=" * 60)
    print("Press Ctrl+C to stop")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
