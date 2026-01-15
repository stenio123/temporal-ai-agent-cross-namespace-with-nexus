"""
Finance Nexus Handler
Exposes Finance tools to other namespaces via Nexus
Based on: https://docs.temporal.io/develop/python/nexus
"""
from typing import Any, Dict, List

import nexusrpc

from app.finance_service import FinanceService


@nexusrpc.handler.service_handler(service=FinanceService)
class FinanceNexusHandler:
    """
    Nexus handler for Finance namespace.
    Exposes tools to orchestrator via Nexus operations.
    """

    @nexusrpc.handler.sync_operation
    async def list_tools(
        self,
        ctx: nexusrpc.handler.StartOperationContext,
        input: None
    ) -> List[Dict[str, Any]]:
        """
        Returns list of available Finance tools.
        Called once by orchestrator at workflow startup.
        """
        tools = [
            {
                "name": "stock_price",
                "description": "Get stock price for a ticker symbol",
                "parameters": {"ticker": "string"},
                "output": "string",
                "namespace_id": "finance"
            },
            {
                "name": "calculate_roi",
                "description": "Calculate return on investment",
                "parameters": {"principal": "number", "rate": "number", "years": "number"},
                "output": "string",
                "namespace_id": "finance"
            },
        ]

        return tools

    @nexusrpc.handler.sync_operation
    async def execute_tool(
        self,
        ctx: nexusrpc.handler.StartOperationContext,
        input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a Finance tool synchronously.
        Called by orchestrator when routing to Finance namespace.
        """
        tool_name = input.get("tool_name")
        args = input.get("args", {})

        from app.finance_activities import FinanceActivities

        activities = FinanceActivities()

        try:
            if tool_name == "stock_price":
                result = await activities.stock_price(args.get("ticker", ""))
            elif tool_name == "calculate_roi":
                result = await activities.calculate_roi(
                    args.get("principal", 0.0),
                    args.get("rate", 0.0),
                    args.get("years", 0)
                )
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            return {
                "tool_name": tool_name,
                "result": result,
                "success": True
            }

        except Exception as e:
            return {
                "tool_name": tool_name,
                "result": f"Error: {str(e)}",
                "success": False
            }
