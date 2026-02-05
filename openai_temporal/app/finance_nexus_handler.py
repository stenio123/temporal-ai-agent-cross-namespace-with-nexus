"""
Finance Nexus Handler
Exposes Finance tools to other namespaces via Nexus (individual operations)
Based on: https://docs.temporal.io/develop/python/nexus

Following Temporal best practice: Nexus operations backed by workflows (not activities)
"""
import uuid
import nexusrpc
from temporalio import nexus

from app.finance_models import ROIInput, StockPriceInput
from app.finance_service import FinanceService
from app.finance_workflows import CalculateROIWorkflow, GetStockPriceWorkflow


@nexusrpc.handler.service_handler(service=FinanceService)
class FinanceNexusHandler:
    """
    Nexus handler for Finance namespace.
    Each tool is a separate operation with explicit types.
    Operations start durable workflows (Temporal best practice).
    """

    @nexus.workflow_run_operation
    async def stock_price(
        self,
        ctx: nexus.WorkflowRunOperationContext,
        input: StockPriceInput
    ) -> nexus.WorkflowHandle[str]:
        """
        Get stock price for a ticker symbol.
        Starts a durable workflow for execution.

        Args:
            input: Stock price input with ticker symbol

        Returns:
            Workflow handle for stock price result
        """
        return await ctx.start_workflow(
            GetStockPriceWorkflow.run,
            input,
            id=f"stock-price-{input.ticker}-{uuid.uuid4()}",
        )

    @nexus.workflow_run_operation
    async def calculate_roi(
        self,
        ctx: nexus.WorkflowRunOperationContext,
        input: ROIInput
    ) -> nexus.WorkflowHandle[str]:
        """
        Calculate return on investment.
        Starts a durable workflow for execution.

        Args:
            input: ROI calculation parameters

        Returns:
            Workflow handle for ROI calculation result
        """
        return await ctx.start_workflow(
            CalculateROIWorkflow.run,
            input,
            id=f"calculate-roi-{uuid.uuid4()}",
        )
