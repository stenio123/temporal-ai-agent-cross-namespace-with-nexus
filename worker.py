"""
Temporal Worker
Runs the workflow and activity workers to execute the durable agent loop.
"""
import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from activities import AgentActivities
from workflow import DurableAgentWorkflow


async def main():
    """Start the Temporal worker"""
    
    # The worker needs to communicate with the service to poll for tasks.
    client = await Client.connect("localhost:7233")
    
    # Create the activity implementation instances. These hold any necessary
    # state for external connections (like DB pools or API clients).
    activities = AgentActivities()
    
    # We register the Workflow class (Orchestrator Logic) and the Activity
    # methods (Side-Effect Logic) with a specific Task Queue.
    worker = Worker(
        client,
        task_queue="durable-agent-queue",
        workflows=[DurableAgentWorkflow],
        activities=[
            activities.plan_next_action,
            activities.execute_tool,
        ],
    )
    
    # This call blocks this process. The worker will now:
    # - Poll the Task Queue for Workflow Tasks and Activity Tasks
    # - Execute (or Replay) the code in the Workflow/Activity classes
    # - Report results back to the Temporal Cluster
    print("Worker started! Listening on task queue: durable-agent-queue")
    print("Press Ctrl+C to stop")
    
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
