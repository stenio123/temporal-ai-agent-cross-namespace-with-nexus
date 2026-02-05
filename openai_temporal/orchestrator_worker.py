"""
Orchestrator Worker - OpenAI Agents SDK Implementation

Runs the workflow and activity workers with OpenAI Agents SDK integration.
Handles local tools (activities) while remote Nexus tools are called automatically.
"""
import asyncio
from datetime import timedelta

from agents.extensions.models.litellm_provider import LitellmProvider
from temporalio.client import Client
from temporalio.contrib.openai_agents import OpenAIAgentsPlugin, ModelActivityParameters
from temporalio.worker import Worker

from app.activities import AgentActivities
from app.workflow import DurableAgentWorkflow
from app.shared import QUEUE_ORCHESTRATOR

# Current litellm version is issuing some pydantic warnings, not impactful to the demo
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")


async def main():
    """Start the Temporal worker with OpenAI Agents SDK integration"""

    # Connect with OpenAI Agents SDK plugin using LiteLLM
    # The plugin configures serialization and model call execution
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=None,  # Use default retry policy
                ),
                model_provider=LitellmProvider(),
            ),
        ],
    )

    # Create the activity implementation instances
    activities = AgentActivities()

    # Register the Workflow class and Activity methods
    # Only local tool activities are registered here
    # Remote Nexus tools are called automatically by SDK via nexus_operation_as_tool()
    worker = Worker(
        client,
        task_queue=QUEUE_ORCHESTRATOR,
        workflows=[DurableAgentWorkflow],
        activities=[
            # Local tool activities
            activities.calculator,
            activities.weather,
        ],
    )

    print("=" * 60)
    print("Orchestrator worker started with OpenAI Agents SDK!")
    print("=" * 60)
    print("Task queue: orchestrator-queue")
    print("Registered activities:")
    print("  - calculator: Evaluate mathematical expressions")
    print("  - weather: Get weather information")
    print("")
    print("Remote tools (via Nexus):")
    print("  - IT namespace: Discovered dynamically at runtime")
    print("  - Finance namespace: Discovered dynamically at runtime")
    print("")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
