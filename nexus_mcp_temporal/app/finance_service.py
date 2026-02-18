"""
Finance Nexus Service Definition
Defines individual operations for each Finance tool (idiomatic Nexus approach)
"""
import nexusrpc

from app.finance_models import ROIInput, StockPriceInput


@nexusrpc.service
class FinanceService:
    """Finance tools service contract - individual operations per tool"""

    # Each tool is its own operation with explicit types
    # Using Pydantic models for all inputs (Temporal best practice)
    stock_price: nexusrpc.Operation[StockPriceInput, str]
    calculate_roi: nexusrpc.Operation[ROIInput, str]
    # new_tool: nexusrpc.Operation[StockPriceInput, str]
