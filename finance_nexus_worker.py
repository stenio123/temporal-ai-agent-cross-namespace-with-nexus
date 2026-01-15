"""
Finance Nexus Worker - runs in finance-namespace
Handles Finance tools and exposes them via Nexus
Based on: https://docs.temporal.io/develop/python/nexus
"""
import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

# Configure logging to show INFO level messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from app.finance_activities import FinanceActivities
from app.finance_nexus_handler import FinanceNexusHandler
from app.shared import NAMESPACE_FINANCE, QUEUE_FINANCE, TEMPORAL_ADDRESS


async def main():
    """Start the Finance worker in finance-namespace"""

    # Connect to Finance namespace
    client = await Client.connect(TEMPORAL_ADDRESS, namespace=NAMESPACE_FINANCE)

    # Create activity instances
    finance_activities = FinanceActivities()

    # Create Nexus service handler instance
    nexus_handler = FinanceNexusHandler()

    # Create worker
    worker = Worker(
        client,
        task_queue=QUEUE_FINANCE,
        workflows=[],  # No workflows needed for simple demo
        activities=[
            finance_activities.stock_price,
            finance_activities.calculate_roi,
        ],
        nexus_service_handlers=[nexus_handler],  # List of service handlers
    )

    print("=" * 60)
    print("Finance Worker started!")
    print(f"Namespace: {NAMESPACE_FINANCE}")
    print(f"Task Queue: {QUEUE_FINANCE}")
    print(f"Nexus Service: finance-tools")
    print(f"Available tools: stock_price, calculate_roi")
    print("=" * 60)
    print("Press Ctrl+C to stop")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
