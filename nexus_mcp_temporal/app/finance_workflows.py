"""
Finance Workflows
Temporal workflows for Finance tools (stateless pattern)
Each tool has its own workflow for durability

Following Temporal best practice: Using Pydantic models for all workflow inputs
"""
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from app.finance_activities import FinanceActivities
from app.finance_models import ROIInput, StockPriceInput


@workflow.defn
class GetStockPriceWorkflow:
    """
    Workflow for getting stock price.
    Stateless pattern - completes immediately after fetching result.
    Uses Pydantic model for input (Temporal best practice).
    """

    @workflow.run
    async def run(self, input: StockPriceInput) -> str:
        """
        Get stock price for a ticker symbol.

        Args:
            input: Stock price input containing ticker symbol

        Returns:
            Stock price as formatted string
        """
        result = await workflow.execute_activity(
            FinanceActivities.stock_price,
            input.ticker,
            schedule_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                maximum_attempts=5,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=10),
                backoff_coefficient=2.0,
            ),
        )
        return result


@workflow.defn
class CalculateROIWorkflow:
    """
    Workflow for calculating ROI.
    Stateless pattern - completes immediately after calculation.
    Uses Pydantic model for input (Temporal best practice).
    """

    @workflow.run
    async def run(self, input: ROIInput) -> str:
        """
        Calculate return on investment.

        Args:
            input: ROI input containing principal, rate, and years

        Returns:
            ROI calculation result as formatted string
        """
        result = await workflow.execute_activity(
            FinanceActivities.calculate_roi,
            args=[input.principal, input.rate, input.years],
            schedule_to_close_timeout=timedelta(seconds=10),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=1),
                maximum_interval=timedelta(seconds=5),
                backoff_coefficient=2.0,
            ),
        )
        return result
