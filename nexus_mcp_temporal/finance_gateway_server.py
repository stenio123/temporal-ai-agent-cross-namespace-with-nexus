"""
Finance MCP Gateway Server - Exposes Finance Nexus operations as MCP tools

This server runs the InboundGateway from nexus-mcp-python for Finance namespace:
1. Connects to Temporal cluster (default namespace)
2. Exposes Finance Nexus operations as MCP tools
3. Allows external MCP clients (Claude Desktop) to call Finance operations
4. Enables workflows to call Finance MCP tools via WorkflowTransport

Run this server to enable the bidirectional MCP ↔ Finance Nexus bridge.
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

from app.shared import NAMESPACE_DEFAULT, QUEUE_FINANCE, TEMPORAL_ADDRESS, ENDPOINT_FINANCE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """
    Start the Finance MCP Gateway server.

    This creates an InboundGateway that:
    - Connects to Temporal using the default namespace
    - Exposes Finance Nexus endpoint as MCP tools
    - Runs an MCP server that Claude Desktop (or workflows) can connect to
    """
    logger.info("Starting Finance MCP Gateway Server...")

    # Connect to Temporal
    logger.info(f"Connecting to Temporal at {TEMPORAL_ADDRESS}")
    client = await Client.connect(
        TEMPORAL_ADDRESS,
        namespace=NAMESPACE_DEFAULT,
    )
    logger.info("Connected to Temporal")

    # Create MCP server
    server = Server("finance-nexus-mcp-gateway")
    logger.info("Created MCP server: finance-nexus-mcp-gateway")

    # Create InboundGateway for Finance namespace
    logger.info(f"Creating InboundGateway for Finance endpoint: {ENDPOINT_FINANCE}")
    finance_gateway = InboundGateway(
        client=client,
        endpoint=ENDPOINT_FINANCE,
    )
    finance_gateway._task_queue = QUEUE_FINANCE
    finance_gateway.register(server)
    logger.info("Registered Finance Nexus endpoint as MCP tools")

    # Run the gateway
    logger.info("=" * 60)
    logger.info("Finance MCP Gateway Server running!")
    logger.info("=" * 60)
    logger.info("Available MCP tools:")
    logger.info("  Finance Namespace:")
    logger.info("    - stock_price (via Finance Nexus endpoint)")
    logger.info("    - calculate_roi (via Finance Nexus endpoint)")
    logger.info("=" * 60)
    logger.info("This gateway can be used by:")
    logger.info("  1. External MCP clients (Claude Desktop, etc.)")
    logger.info("  2. Workflows via WorkflowTransport")
    logger.info("=" * 60)
    logger.info(f"Task Queue: {QUEUE_FINANCE}")
    logger.info("Press Ctrl+C to stop")

    # Run gateway
    async with finance_gateway.run():
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down Finance MCP Gateway Server...")


if __name__ == "__main__":
    asyncio.run(main())
