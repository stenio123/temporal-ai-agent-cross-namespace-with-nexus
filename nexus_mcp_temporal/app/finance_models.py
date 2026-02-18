"""
Finance Operation Input Models
Pydantic models for Finance Nexus operation inputs
Following Temporal best practice: always use objects for parameters
"""
from pydantic import BaseModel, Field


class StockPriceInput(BaseModel):
    """Input for stock_price operation"""
    ticker: str = Field(description="Stock ticker symbol (e.g., AAPL, GOOGL)")


class ROIInput(BaseModel):
    """Input for calculate_roi operation"""
    principal: float = Field(description="Principal investment amount")
    rate: float = Field(description="Annual interest rate (as decimal, e.g., 0.05 for 5%)")
    years: int = Field(description="Number of years")
