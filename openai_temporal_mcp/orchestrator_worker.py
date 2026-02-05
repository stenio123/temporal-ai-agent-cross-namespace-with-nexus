"""
Orchestrator Worker - OpenAI Agents SDK with Native MCP Integration

Runs the workflow and activity workers with OpenAI Agents SDK integration.
Uses native MCP protocol integration with StatelessMCPServerProvider.
"""
import asyncio
from datetime import timedelta

from agents.extensions.models.litellm_provider import LitellmProvider
from agents.mcp import MCPServerStreamableHttp
from temporalio.client import Client
from temporalio.contrib.openai_agents import (
    OpenAIAgentsPlugin,
    ModelActivityParameters,
    StatelessMCPServerProvider,
)
from temporalio.worker import Worker

import app.activities as activities
from app.workflow import DurableAgentWorkflow
from app.shared import QUEUE_ORCHESTRATOR, MCP_SERVERS

# Current litellm version is issuing some pydantic warnings, not impactful to the demo
import warnings

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

async def main():
    """Start the Temporal worker with native MCP integration"""

    # Create MCP server providers from configuration
    def create_server_factory(server_config):
        def factory(_):
            return MCPServerStreamableHttp(
                name=server_config["name"],
                params={"url": server_config["url"]}
            )
        return factory

    mcp_server_providers = [
        StatelessMCPServerProvider(
            name=server["name"],
            server_factory=create_server_factory(server)
        )
        for server in MCP_SERVERS
    ]

    # Connect with OpenAI Agents SDK plugin using LiteLLM
    client = await Client.connect(
        "localhost:7233",
        plugins=[
            OpenAIAgentsPlugin(
                model_params=ModelActivityParameters(
                    start_to_close_timeout=timedelta(seconds=60),
                    retry_policy=None,  # Use default retry policy
                ),
                model_provider=LitellmProvider(),
                mcp_server_providers=mcp_server_providers,
            ),
        ],
    )

    # Create worker with workflows and local activities
    # MCP tools are automatically registered by the plugin
    worker = Worker(
        client,
        task_queue=QUEUE_ORCHESTRATOR,
        workflows=[DurableAgentWorkflow],
        activities=[activities.calculator, activities.weather],
    )

    print("=" * 60)
    print("✓ Orchestrator worker started successfully!")
    print("=" * 60)
    print(f"Task queue: {QUEUE_ORCHESTRATOR}")
    print("")
    print("Local tools (activities):")
    print("  - calculator: Evaluate mathematical expressions")
    print("  - weather: Get weather information")
    print("")
    print("MCP servers:")
    for server in MCP_SERVERS:
        print(f"  - {server['name']}: {server['description']}")
    print("")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
