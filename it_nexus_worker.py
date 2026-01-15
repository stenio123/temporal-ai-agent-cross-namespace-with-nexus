import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from activities import AgentActivities
from workflow import DurableAgentWorkflow
from nexus_handler import AgentNexusHandler

async def main():
    client = await Client.connect("localhost:7233", namespace="it-namespace")

    # 1. Instantiate your Nexus Handler
    nexus_handler = AgentNexusHandler()

    worker = Worker(
        client,
        task_queue="it-task-queue",
        workflows=[DurableAgentWorkflow],
        activities=AgentActivities().execute_tool, # and others...
        # 2. Register the Nexus handler here
        nexus_handler=nexus_handler 
    )

    print("Worker is running and listening for Nexus requests...")
    await worker.run()

if __name__ == "__main__":
    asyncio.run(main())