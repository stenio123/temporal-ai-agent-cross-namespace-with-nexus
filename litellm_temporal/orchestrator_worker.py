"""
Orchestrator Worker
Runs the workflow and activity workers to execute the durable agent loop.
Handles local tools and routes to remote namespaces.
"""
import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.activities import AgentActivities
from app.workflow import DurableAgentWorkflow

# Current litellm version is issuing some pydantic warnings, not impactful to the demo
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

async def main():
    """Start the Temporal worker"""
    
    # Connect to default namespace
    client = await Client.connect("localhost:7233")
    
    # Create the activity implementation instances
    activities = AgentActivities()

    # Register the Workflow class and Activity methods
    # Note: list_remote_tools and execute_remote_tool are no longer activities
    # They are now called directly from the workflow via Nexus SDK
    worker = Worker(
        client,
        task_queue="orchestrator-queue",
        workflows=[DurableAgentWorkflow],
        activities=[
            activities.plan_next_action,
            activities.execute_tool,
        ],
    )
    
    print("Orchestrator worker started! Listening on task queue: orchestrator-queue")
    print("Press Ctrl+C to stop")
    
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
