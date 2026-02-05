"""
Finance Worker - runs in finance-namespace
Handles Finance tool workflows - triggered by Finance MCP HTTP server
"""
import asyncio
import logging

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

# Configure logging to show INFO level messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

import app.finance_activities as finance_activities
from app.finance_workflows import CalculateROIWorkflow, GetStockPriceWorkflow
from app.shared import NAMESPACE_FINANCE, QUEUE_FINANCE, TEMPORAL_ADDRESS


async def main():
    """Start the Finance worker"""

    # Connect to Finance namespace with Pydantic data converter
    client = await Client.connect(
        TEMPORAL_ADDRESS,
        namespace=NAMESPACE_FINANCE,
        data_converter=pydantic_data_converter,
    )

    # Create worker with workflows and activities
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
    )

    print("=" * 60)
    print("Finance Worker started!")
    print(f"Namespace: {NAMESPACE_FINANCE}")
    print(f"Task Queue: {QUEUE_FINANCE}")
    print(f"Workflows: GetStockPriceWorkflow, CalculateROIWorkflow")
    print(f"Activities: stock_price, calculate_roi")
    print(f"Triggered by: Finance MCP HTTP server (port 8001)")
    print("=" * 60)
    print("Press Ctrl+C to stop")

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
