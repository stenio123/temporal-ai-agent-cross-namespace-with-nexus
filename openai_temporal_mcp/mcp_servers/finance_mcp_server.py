"""
Finance MCP Server
Exposes Finance tools via MCP 

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

from app.finance_models import ROIInput, StockPriceInput
from app.finance_workflows import CalculateROIWorkflow, GetStockPriceWorkflow
from app.shared import (
    QUEUE_FINANCE,
    NAMESPACE_FINANCE,
    TEMPORAL_ADDRESS,
    MCP_SERVERS,
)


class FinanceMCPServer:
    """
    MCP server for Finance tools.
    Each tool invocation starts a new workflow that completes immediately.
    """

    def __init__(
        self,
        name: str = "FinanceMCP",
        temporal_address: str = "localhost:7233",
        namespace: str = "finance-namespace",
        task_queue: str = QUEUE_FINANCE,
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
        async def stock_price(ticker: str) -> str:
            """
            Get current stock price for a ticker symbol.

            Args:
                ticker: Stock ticker symbol (e.g., AAPL, GOOGL)

            Returns:
                Current stock price as formatted string
            """
            client = await self.get_client()

            # Create Pydantic model (Temporal best practice)
            input_data = StockPriceInput(ticker=ticker)

            # Start workflow - this is where durability begins
            handle = await client.start_workflow(
                GetStockPriceWorkflow.run,
                input_data,
                id=f"stock-price-{ticker}-{uuid.uuid4()}",
                task_queue=self.task_queue,
            )

            # Wait for result (stateless - completes quickly)
            return await handle.result()

        @self.mcp.tool()
        async def calculate_roi(principal: float, rate: float, years: int) -> str:
            """
            Calculate return on investment.

            Args:
                principal: Principal investment amount (e.g., 10000.0)
                rate: Annual interest rate as decimal (e.g., 0.05 for 5%)
                years: Number of years (e.g., 10)

            Returns:
                ROI calculation result as formatted string
            """
            client = await self.get_client()

            # Create Pydantic model (Temporal best practice)
            input_data = ROIInput(principal=principal, rate=rate, years=years)

            # Start workflow - this is where durability begins
            handle = await client.start_workflow(
                CalculateROIWorkflow.run,
                input_data,
                id=f"calculate-roi-{uuid.uuid4()}",
                task_queue=self.task_queue,
            )

            # Wait for result (stateless - completes quickly)
            return await handle.result()
        
        # Uncomment to test dynamic tool discovery - requires MCP server restart
        @self.mcp.tool()
        # async def retail_eval(ticker: str) -> str:
        #     """
        #     Get retail eval information.

        #     Args:
        #         ticker: Stock ticker symbol (e.g., AAPL, GOOGL)

        #     Returns:
        #         Current stock price as formatted string
        #     """
        #     client = await self.get_client()

        #     # Create Pydantic model (Temporal best practice)
        #     input_data = StockPriceInput(ticker=ticker)

        #     # Start workflow - this is where durability begins
        #     handle = await client.start_workflow(
        #         GetStockPriceWorkflow.run,
        #         input_data,
        #         id=f"stock-price-{ticker}-{uuid.uuid4()}",
        #         task_queue=self.task_queue,
        #     )

        #     # Wait for result (stateless - completes quickly)
        #     return await handle.result()


def create_finance_mcp_server(
    name: str = "FinanceMCP",
    temporal_address: str = "localhost:7233",
    namespace: str = "finance-namespace",
    task_queue: str = QUEUE_FINANCE,
) -> FastMCP:
    """
    Factory function to create Finance MCP server.

    Args:
        name: MCP server name
        temporal_address: Temporal server address
        namespace: Temporal namespace
        task_queue: Task queue name

    Returns:
        FastMCP server instance
    """
    server = FinanceMCPServer(name, temporal_address, namespace, task_queue)
    return server.mcp


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description="Finance MCP Server - supports HTTP and STDIO transports"
    )
    parser.add_argument(
        "--transport",
        choices=["http", "stdio"],
        default=os.getenv("MCP_TRANSPORT", "http"),
        help="Transport protocol: 'http' for orchestrator, 'stdio' for external clients (default: http)",
    )
    args = parser.parse_args()

    # Get configuration from shared.py
    finance_config = next((s for s in MCP_SERVERS if s["name"] == "finance"), None)
    if not finance_config:
        raise ValueError("Finance server not found in MCP_SERVERS configuration")

    # Create server instance
    server = FinanceMCPServer(
        name="FinanceMCP",
        temporal_address=TEMPORAL_ADDRESS,
        namespace=NAMESPACE_FINANCE,
        task_queue=QUEUE_FINANCE,
    )

    # Run with selected transport
    if args.transport == "http":
        print("=" * 60)
        print("Starting Finance MCP Server with HTTP transport")
        print(f"Host: {finance_config['host']}:{finance_config['port']}")
        print(f"MCP Endpoint: {finance_config['url']}/mcp")
        print(f"Namespace: {NAMESPACE_FINANCE}")
        print(f"Task Queue: {QUEUE_FINANCE}")
        print("Available tools: stock_price, calculate_roi")
        print("Transport: Streamable HTTP (native MCP protocol)")
        print("=" * 60)

        server.mcp.run(
            transport="streamable-http",
            host=finance_config["host"],
            port=finance_config["port"],
        )
    else:  # stdio
        print("=" * 60)
        print("Starting Finance MCP Server with STDIO transport")
        print(f"Namespace: {NAMESPACE_FINANCE}")
        print(f"Task Queue: {QUEUE_FINANCE}")
        print("Available tools: stock_price, calculate_roi")
        print("Transport: STDIO (for Claude Desktop, Goose, etc.)")
        print("=" * 60)

        server.mcp.run(transport="stdio")
