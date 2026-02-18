"""
MCP Helper Functions

Utilities for discovering and creating MCP tools from Nexus endpoints.
Used by workflows that integrate with MCP Gateway via WorkflowTransport.
"""
import json

import mcp.types as types
from agents.tool_context import ToolContext
from mcp import ClientSession
from nexusmcp import WorkflowTransport
from temporalio import workflow
from temporalio.contrib.openai_agents.workflow import FunctionTool


async def discover_tools_from_endpoint(
    transport: WorkflowTransport,
    endpoint_name: str,
) -> list:
    """
    Dynamically discover tools from an MCP endpoint.

    This is deterministic because it happens once during workflow init
    and uses Nexus RPC (recorded in workflow history).

    Args:
        transport: WorkflowTransport instance connected to the endpoint
        endpoint_name: Human-readable name for logging (e.g., "IT", "Finance")

    Returns:
        List of MCP Tool objects discovered from the endpoint
    """
    try:
        async with transport.connect() as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                # List available tools from this endpoint
                tools_response = await session.list_tools()
                workflow.logger.info(
                    f"Discovered {len(tools_response.tools)} tools from {endpoint_name}: "
                    f"{[t.name for t in tools_response.tools]}"
                )
                return tools_response.tools
    except Exception as e:
        workflow.logger.error(f"Failed to discover tools from {endpoint_name}: {e}")
        return []


def create_mcp_gateway_tool_from_schema(
    mcp_tool: types.Tool,
    transport: WorkflowTransport,
) -> FunctionTool:
    """
    Creates a FunctionTool that calls MCP Gateway via WorkflowTransport.

    Uses the dynamically discovered tool schema from MCP.
    This uses Nexus RPC (deterministic) rather than HTTP (non-deterministic),
    ensuring tool calls are properly tracked in workflow history.

    Args:
        mcp_tool: MCP Tool schema discovered from the gateway
        transport: WorkflowTransport instance to use for calls

    Returns:
        FunctionTool configured for OpenAI Agents SDK
    """
    async def tool_function(ctx: ToolContext, arguments: str):
        # Parse JSON arguments
        args = json.loads(arguments) if arguments else {}
        workflow.logger.info(f"Calling MCP Gateway tool: {mcp_tool.name} with args: {args}")
        try:
            async with transport.connect() as (read, write):
                async with ClientSession(read, write) as session:
                    result = await session.call_tool(mcp_tool.name, args)
                    workflow.logger.info(f"MCP Gateway tool {mcp_tool.name} returned: {result}")
                    return result.content[0].text if result.content else str(result)
        except Exception as e:
            workflow.logger.error(f"Error calling MCP Gateway tool {mcp_tool.name}: {e}")
            return f"Error: {str(e)}"

    return FunctionTool(
        name=mcp_tool.name,
        description=mcp_tool.description or f"Tool: {mcp_tool.name}",
        params_json_schema=(
            mcp_tool.inputSchema if mcp_tool.inputSchema
            else {"type": "object", "properties": {}}
        ),
        on_invoke_tool=tool_function,
    )
