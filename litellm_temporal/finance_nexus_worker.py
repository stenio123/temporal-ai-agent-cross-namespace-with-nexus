"""
Finance Nexus Worker - runs in finance-namespace
Handles Finance tools and exposes them via Nexus
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

from app.finance_activities import FinanceActivities
from app.finance_nexus_handler import FinanceNexusHandler
from app.finance_workflows import CalculateROIWorkflow, GetStockPriceWorkflow
from app.shared import NAMESPACE_FINANCE, QUEUE_FINANCE, TEMPORAL_ADDRESS


async def main():
    """Start the Finance worker in finance-namespace"""

    # Connect to Finance namespace with Pydantic data converter
    client = await Client.connect(
        TEMPORAL_ADDRESS,
        namespace=NAMESPACE_FINANCE,
        data_converter=pydantic_data_converter,
    )

    # Create activity instances
    finance_activities = FinanceActivities()

    # Create Nexus service handler instance
    nexus_handler = FinanceNexusHandler()

    # Create worker with workflows, activities, and Nexus handler
    worker = Worker(
        client,
        task_queue=QUEUE_FINANCE,
        workflows=[
            GetStockPriceWorkflow,
            CalculateROIWorkflow,
        ],
        activities=[
            finance_activities.stock_price,
            finance_activities.calculate_roi,
        ],
        nexus_service_handlers=[nexus_handler],
    )

    print("=" * 60)
    print("Finance Worker started (with durable workflows)!")
    print(f"Namespace: {NAMESPACE_FINANCE}")
    print(f"Task Queue: {QUEUE_FINANCE}")
    print(f"Workflows: GetStockPriceWorkflow, CalculateROIWorkflow")
    print(f"Nexus Service: FinanceService")
    print(f"Available tools: stock_price, calculate_roi")
    print(f"Pattern: Nexus operations backed by durable workflows")
    print("=" * 60)
    print("Press Ctrl+C to stop")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
