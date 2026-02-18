"""
Finance Nexus Handler
Exposes Finance tools to other namespaces via Nexus (individual operations)
Based on: https://docs.temporal.io/develop/python/nexus

Following Temporal best practice: Nexus operations backed by workflows (not activities)
"""
import uuid
import nexusrpc
from nexusrpc.handler import StartOperationContext, sync_operation
from temporalio.client import Client

from nexusmcp import MCPServiceHandler

from app.finance_models import ROIInput, StockPriceInput
from app.finance_service import FinanceService
from app.finance_workflows import CalculateROIWorkflow, GetStockPriceWorkflow
from app.shared import QUEUE_FINANCE


# Create MCPServiceHandler registry for tool discovery
mcp_service = MCPServiceHandler()


@mcp_service.register
@nexusrpc.handler.service_handler(service=FinanceService)
class FinanceNexusHandler:
    """
    Nexus handler for Finance namespace.
    Each tool is a separate operation with explicit types.
    Operations start durable workflows (Temporal best practice).
    """

    def __init__(self, client: Client):
        """
        Initialize handler with Temporal client for workflow execution.

        Args:
            client: Temporal client for starting workflows
        """
        self.client = client

    @sync_operation
    async def stock_price(
        self,
        ctx: StartOperationContext,
        input: StockPriceInput
    ) -> str:
        """
        Get stock price for a ticker symbol.
        Starts a durable workflow for execution.

        Args:
            input: Stock price input with ticker symbol

        Returns:
            Stock price result
        """
        result = await self.client.execute_workflow(
            GetStockPriceWorkflow.run,
            input,
            id=f"stock-price-{input.ticker}-{uuid.uuid4()}",
            task_queue=QUEUE_FINANCE,
        )
        return result

    @sync_operation
    async def calculate_roi(
        self,
        ctx: StartOperationContext,
        input: ROIInput
    ) -> str:
        """
        Calculate return on investment.
        Starts a durable workflow for execution.

        Args:
            input: ROI calculation parameters

        Returns:
            ROI calculation result
        """
        result = await self.client.execute_workflow(
            CalculateROIWorkflow.run,
            input,
            id=f"calculate-roi-{uuid.uuid4()}",
            task_queue=QUEUE_FINANCE,
        )
        return result

    # @sync_operation
    # async def new_tool(
    #     self,
    #     ctx: StartOperationContext,
    #     input: StockPriceInput
    # ) -> str:
    #     """
    #     New tool for testing calculations.
    #     Starts a durable workflow for execution.

    #     Args:
    #         input: Stock price input with ticker symbol

    #     Returns:
    #         Calculations result
    #     """
    #     result = await self.client.execute_workflow(
    #         GetStockPriceWorkflow.run,
    #         input,
    #         id=f"newtool-{input.ticker}-{uuid.uuid4()}",
    #         task_queue=QUEUE_FINANCE,
    #     )
    #     return result