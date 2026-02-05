"""
IT MCP Server
Exposes IT tools via MCP 

MCP Tool Discovery:
- FastMCP automatically exposes tools via @mcp.tool() decorator
- Tool metadata (name, description, parameters) extracted from function signature and docstring
- MCP clients can query available tools and their schemas
"""
import uuid
from typing import Optional
import argparse
import os

from fastmcp import FastMCP
from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from app.it_models import JiraMetricsInput
from app.it_workflows import GetIPWorkflow, GetJiraMetricsWorkflow
from app.shared import (
    QUEUE_IT,
    NAMESPACE_IT,
    TEMPORAL_ADDRESS,
    MCP_SERVERS,
)


class ITMCPServer:
    """
    MCP server for IT tools.
    Each tool invocation starts a new workflow that completes immediately.
    """

    def __init__(
        self,
        name: str = "ITMCP",
        temporal_address: str = "localhost:7233",
        namespace: str = "it-namespace",
        task_queue: str = QUEUE_IT,
    ):
        self.name = name
        self.temporal_address = temporal_address
        self.namespace = namespace
        self.task_queue = task_queue
        self.mcp = FastMCP(name)
        self._client: Optional[Client] = None

        # Register tools
        self._register_tools()

    async def get_client(self) -> Client:
        """Get or create Temporal client with Pydantic data converter."""
        if self._client is None:
            self._client = await Client.connect(
                self.temporal_address,
                namespace=self.namespace,
                data_converter=pydantic_data_converter,
            )
        return self._client

    def _register_tools(self):
        """Register MCP tools."""

        @self.mcp.tool()
        async def get_ip() -> str:
            """
            Get the current IP address.

            Returns:
                Current IP address as string
            """
            client = await self.get_client()

            # Start workflow - this is where durability begins
            handle = await client.start_workflow(
                GetIPWorkflow.run,
                id=f"get-ip-{uuid.uuid4()}",
                task_queue=self.task_queue,
            )

            # Wait for result (stateless - completes quickly)
            return await handle.result()

        @self.mcp.tool()
        async def get_jira_metrics(project: str) -> str:
            """
            Get JIRA metrics for a project.

            Args:
                project: JIRA project identifier (e.g., PROJ-123)

            Returns:
                JIRA metrics as formatted string
            """
            client = await self.get_client()

            # Create Pydantic model (Temporal best practice)
            input_data = JiraMetricsInput(project=project)

            # Start workflow - this is where durability begins
            handle = await client.start_workflow(
                GetJiraMetricsWorkflow.run,
                input_data,
                id=f"jira-metrics-{project}-{uuid.uuid4()}",
                task_queue=self.task_queue,
            )

            # Wait for result (stateless - completes quickly)
            return await handle.result()


def create_it_mcp_server(
    name: str = "ITMCP",
    temporal_address: str = "localhost:7233",
    namespace: str = "it-namespace",
    task_queue: str = QUEUE_IT,
) -> FastMCP:
    """
    Factory function to create IT MCP server.

    Args:
        name: MCP server name
        temporal_address: Temporal server address
        namespace: Temporal namespace
        task_queue: Task queue name

    Returns:
        FastMCP server instance
    """
    server = ITMCPServer(name, temporal_address, namespace, task_queue)
    return server.mcp


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="IT MCP Server - supports HTTP and STDIO transports"
    )
    parser.add_argument(
        "--transport",
        choices=["http", "stdio"],
        default=os.getenv("MCP_TRANSPORT", "http"),
        help="Transport protocol: 'http' for orchestrator, 'stdio' for external clients (default: http)",
    )
    args = parser.parse_args()

    # Get configuration from shared.py
    it_config = next((s for s in MCP_SERVERS if s["name"] == "it"), None)
    if not it_config:
        raise ValueError("IT server not found in MCP_SERVERS configuration")

    # Create server instance
    server = ITMCPServer(
        name="ITMCP",
        temporal_address=TEMPORAL_ADDRESS,
        namespace=NAMESPACE_IT,
        task_queue=QUEUE_IT,
    )

    # Run with selected transport
    if args.transport == "http":
        print("=" * 60)
        print("Starting IT MCP Server with HTTP transport")
        print(f"Host: {it_config['host']}:{it_config['port']}")
        print(f"MCP Endpoint: {it_config['url']}")
        print(f"Namespace: {NAMESPACE_IT}")
        print(f"Task Queue: {QUEUE_IT}")
        print("Available tools: get_ip, get_jira_metrics")
        print("Transport: Streamable HTTP (native MCP protocol)")
        print("=" * 60)

        server.mcp.run(
            transport="streamable-http",
            host=it_config["host"],
            port=it_config["port"],
        )
    else:  # stdio
        print("=" * 60)
        print("Starting IT MCP Server with STDIO transport")
        print(f"Namespace: {NAMESPACE_IT}")
        print(f"Task Queue: {QUEUE_IT}")
        print("Available tools: get_ip, get_jira_metrics")
        print("Transport: STDIO (for Claude Desktop, Goose, etc.)")
        print("=" * 60)

        server.mcp.run(transport="stdio")
