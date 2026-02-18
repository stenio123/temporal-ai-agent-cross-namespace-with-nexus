"""
Finance Activities - Tools for Finance namespace
Simple implementations, called via Nexus from orchestrator
"""
import logging

from temporalio import activity

logger = logging.getLogger(__name__)


class FinanceActivities:
    """Finance department activities"""

    @activity.defn(name="stock_price")
    async def stock_price(self, ticker: str) -> str:
        """Get stock price for a ticker symbol"""
        logger.info(f"Getting stock price for: {ticker}")

        # Mock implementation
        return f"Stock price for {ticker}: $152.34 (as of market close)"

    @activity.defn(name="calculate_roi")
    async def calculate_roi(self, principal: float, rate: float, years: int) -> str:
        """Calculate return on investment"""
        logger.info(f"Calculating ROI: principal={principal}, rate={rate}, years={years}")

        # Simple calculation
        roi = principal * ((1 + rate) ** years)
        return f"ROI calculation: ${roi:.2f} after {years} years (initial investment: ${principal})"
    
    # @activity.defn(name="new_tool")
    # async def new_tool(self, ticker: str) -> str:
    #     """New tool for calculation symbol"""
    #     logger.info(f"New tool for: {ticker}")

    #     # Mock implementation
    #     return f"New tool for {ticker}: $999.34 (as of market close)"
