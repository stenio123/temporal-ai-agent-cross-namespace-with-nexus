"""
IT MCP Gateway Server - Exposes IT Nexus operations as MCP tools

This server runs the InboundGateway from nexus-mcp-python for IT namespace:
1. Connects to Temporal cluster (default namespace)
2. Exposes IT Nexus operations as MCP tools
3. Allows external MCP clients (Claude Desktop) to call IT operations
4. Enables workflows to call IT MCP tools via WorkflowTransport

Run this server to enable the bidirectional MCP ↔ IT Nexus bridge.
"""
import asyncio
import logging

from mcp.server.lowlevel import Server
from temporalio.client import Client

# Import nexus-mcp components
try:
    from nexusmcp import InboundGateway
except ImportError:
    print("ERROR: nexus-mcp not installed. Install with:")
    print("  uv add 'nexus-mcp @ git+https://github.com/bergundy/nexus-mcp-python.git@main'")
    exit(1)

from app.shared import NAMESPACE_DEFAULT, QUEUE_IT, TEMPORAL_ADDRESS, ENDPOINT_IT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """
    Start the IT MCP Gateway server.

    This creates an InboundGateway that:
    - Connects to Temporal using the default namespace
    - Exposes IT Nexus endpoint as MCP tools
    - Runs an MCP server that Claude Desktop (or workflows) can connect to
    """
    logger.info("Starting IT MCP Gateway Server...")

    # Connect to Temporal
    logger.info(f"Connecting to Temporal at {TEMPORAL_ADDRESS}")
    client = await Client.connect(
        TEMPORAL_ADDRESS,
        namespace=NAMESPACE_DEFAULT,
    )
    logger.info("Connected to Temporal")

    # Create MCP server
    server = Server("it-nexus-mcp-gateway")
    logger.info("Created MCP server: it-nexus-mcp-gateway")

    # Create InboundGateway for IT namespace
    logger.info(f"Creating InboundGateway for IT endpoint: {ENDPOINT_IT}")
    it_gateway = InboundGateway(
        client=client,
        endpoint=ENDPOINT_IT,
    )
    it_gateway._task_queue = QUEUE_IT
    it_gateway.register(server)
    logger.info("Registered IT Nexus endpoint as MCP tools")

    # Run the gateway
    logger.info("=" * 60)
    logger.info("IT MCP Gateway Server running!")
    logger.info("=" * 60)
    logger.info("Available MCP tools:")
    logger.info("  IT Namespace:")
    logger.info("    - jira_metrics (via IT Nexus endpoint)")
    logger.info("    - get_ip (via IT Nexus endpoint)")
    logger.info("=" * 60)
    logger.info("This gateway can be used by:")
    logger.info("  1. External MCP clients (Claude Desktop, etc.)")
    logger.info("  2. Workflows via WorkflowTransport")
    logger.info("=" * 60)
    logger.info(f"Task Queue: {QUEUE_IT}")
    logger.info("Press Ctrl+C to stop")

    # Run gateway
    async with it_gateway.run():
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down IT MCP Gateway Server...")


if __name__ == "__main__":
    asyncio.run(main())
