"""
IT Nexus Handler
Exposes IT tools to other namespaces via Nexus
Based on: https://docs.temporal.io/develop/python/nexus
"""
from typing import Any, Dict, List

import nexusrpc

from app.it_service import ITService


@nexusrpc.handler.service_handler(service=ITService)
class ITNexusHandler:
    """
    Nexus handler for IT namespace.
    Exposes tools to orchestrator via Nexus operations.

    Pattern: Synchronous operations for simple, fast tool execution.
    Reference: nexusrpc.handler.sync_operation docs
    """

    @nexusrpc.handler.sync_operation
    async def list_tools(
        self,
        ctx: nexusrpc.handler.StartOperationContext,
        input: None
    ) -> List[Dict[str, Any]]:
        """
        Returns list of available IT tools.
        Called once by orchestrator at workflow startup.

        Synchronous operation - must complete quickly (< 10s).
        """
        tools = [
            {
                "name": "jira_metrics",
                "description": "Get JIRA project metrics and statistics",
                "parameters": {"project": "string"},
                "output": "string",
                "namespace_id": "it"
            },
            {
                "name": "get_ip",
                "description": "Get current IP address",
                "parameters": {},
                "output": "string",
                "namespace_id": "it"
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
        Execute an IT tool synchronously.
        Called by orchestrator when routing to IT namespace.

        Pattern: Call activity directly from handler (simple demo).
        Production: Start a workflow that executes the activity.
        """
        tool_name = input.get("tool_name")
        args = input.get("args", {})

        # For this demo, we call activities directly
        # In production, you'd start a workflow
        from app.it_activities import ITActivities

        activities = ITActivities()

        # Route to appropriate activity
        try:
            if tool_name == "jira_metrics":
                result = await activities.jira_metrics(args.get("project", ""))
            elif tool_name == "get_ip":
                result = await activities.get_ip()
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

            return {
                "tool_name": tool_name,
                "result": result,
                "success": True
            }

        except Exception as e:
            # Return error in result format (don't raise exception)
            return {
                "tool_name": tool_name,
                "result": f"Error: {str(e)}",
                "success": False
            }
