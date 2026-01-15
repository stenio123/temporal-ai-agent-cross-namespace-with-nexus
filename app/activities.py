"""
Activities: All non-deterministic operations (LLM calls, tool execution)

These are the ONLY places where I/O and non-deterministic code is allowed.
Results are persisted by Temporal - replays use stored results, not re-execution.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from temporalio import activity
from simpleeval import simple_eval

from app.llm_client import call_llm


@dataclass
class PlanResult:
    """Result from the planning activity"""
    next_step: str  # "execute_tool", "execute_remote_tool", "respond", or "done"
    tool_name: str = ""
    tool_args: Optional[Dict[str, Any]] = None
    response: str = ""
    namespace_id: str = ""  # For remote tools: "it", "finance"


@dataclass 
class ToolResult:
    """Result from tool execution"""
    tool_name: str
    result: str
    success: bool


class AgentActivities:
    """Activities for the durable agent"""
    
    @activity.defn(name="plan_next_action")
    async def plan_next_action(
        self, 
        context: str,
        conversation_history: List[Dict[str, str]],
        remote_tools: Dict[str, List[Dict[str, Any]]] = None
    ) -> PlanResult:
        """
        Use LLM to decide next action: use a local tool, remote tool, or respond to user.
        """
        activity.logger.info(f"Planning for context: {context[:100]}...")
        
        # Format remote tools for prompt
        remote_tools = remote_tools or {}
        it_tools = remote_tools.get("it", [])
        finance_tools = remote_tools.get("finance", [])
        
        system_prompt = f"""You are a helpful assistant with local and remote tools.

Available tools:

LOCAL TOOLS (immediate execution):
- calculator: Evaluate math expressions. 
  Example: {{"action": "use_tool", "tool": "calculator", "args": {{"expression": "25 * 4"}}}}
- weather: Get weather for a city. 
  Example: {{"action": "use_tool", "tool": "weather", "args": {{"city": "Paris"}}}}

REMOTE TOOLS (cross-namespace execution):

IT Namespace Tools:
{it_tools}

Finance Namespace Tools:
{finance_tools}

To use a remote tool:
{{"action": "use_remote_tool", "namespace_id": "it", "tool": "jira_metrics", "args": {{"project": "PROJ-123"}}}}

Respond with JSON:
- Local tool: {{"action": "use_tool", "tool": "calculator", "args": {{"expression": "2 + 2"}}}}
- Remote tool: {{"action": "use_remote_tool", "namespace_id": "it", "tool": "jira_metrics", "args": {{"project": "PROJ-123"}}}}
- Respond: {{"action": "respond", "message": "your response"}}
- End: {{"action": "done", "message": "goodbye"}}"""

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        
        # Call LLM with structured output
        result = call_llm(messages)
        activity.logger.info(f"LLM result: {result}")
        
        action = result.get("action", "respond")
        
        if action == "use_tool":
            return PlanResult(
                next_step="execute_tool",
                tool_name=result.get("tool", ""),
                tool_args=result.get("args", {}),
            )
        elif action == "use_remote_tool":
            return PlanResult(
                next_step="execute_remote_tool",
                namespace_id=result.get("namespace_id", ""),
                tool_name=result.get("tool", ""),
                tool_args=result.get("args", {}),
            )
        elif action == "done":
            return PlanResult(
                next_step="done",
                response=result.get("message", "Goodbye!")
            )
        else:
            return PlanResult(
                next_step="respond",
                response=result.get("message", str(result))
            )
    
    @activity.defn(name="execute_tool")
    async def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        """Execute a tool and return the result"""
        activity.logger.info(f"Executing {tool_name} with {args}")
        # Used to simulate a bug - check MANUAL_TESTS.md for details
        #raise RuntimeError("Simulated bug: crash before tool execution")
        if tool_name == "calculator":
            return self._run_calculator(args)
        elif tool_name == "weather":
            return self._run_weather(args)
        else:
            return ToolResult(tool_name, f"Unknown tool: {tool_name}", False)
    
    def _run_calculator(self, args: Dict[str, Any]) -> ToolResult:
        try:
            expr = args.get("expression", "")
            result = simple_eval(expr)
            return ToolResult("calculator", str(result), True)
        except Exception as e:
            return ToolResult("calculator", f"Error: {e}", False)
    
    def _run_weather(self, args: Dict[str, Any]) -> ToolResult:
        city = args.get("city", "Unknown")
        return ToolResult("weather", f"Weather in {city}: Sunny, 72°F", True)
    
    @activity.defn(name="list_remote_tools")
    async def list_remote_tools(self, namespace_id: str) -> List[Dict[str, Any]]:
        """
        Discover available tools from a remote namespace.
        
        STUB: Returns hardcoded list. In Stage 2, this will call Nexus.
        """
        activity.logger.info(f"[STUB] Listing tools for namespace: {namespace_id}")
        
        # STUB: Hardcoded tool lists matching expected MCP format
        if namespace_id == "it":
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
        elif namespace_id == "finance":
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
        else:
            tools = []
        
        activity.logger.info(f"[STUB] Discovered {len(tools)} tools in {namespace_id} namespace")
        for tool in tools:
            activity.logger.info(f"  - {tool['name']}: {tool['description']}")
        
        return tools
    
    @activity.defn(name="execute_remote_tool")
    async def execute_remote_tool(
        self, 
        namespace_id: str,
        tool_name: str, 
        args: Dict[str, Any]
    ) -> ToolResult:
        """
        Execute a tool in a remote namespace.
        
        STUB: Returns realistic mock data to validate LLM routing. In Stage 2, this will call Nexus.
        """
        activity.logger.info(f"[STUB] ========== REMOTE TOOL EXECUTION ==========")
        activity.logger.info(f"[STUB] Namespace: {namespace_id}")
        activity.logger.info(f"[STUB] Tool: {tool_name}")
        activity.logger.info(f"[STUB] Args: {args}")
        activity.logger.info(f"[STUB] ===============================================")
        
        # STUB: Return realistic mock data based on tool
        if tool_name == "stock_price":
            ticker = args.get("ticker", "UNKNOWN")
            mock_result = f"Stock price for {ticker}: $152.34 (as of market close)"
        elif tool_name == "jira_metrics":
            project = args.get("project", "UNKNOWN")
            mock_result = f"JIRA metrics for {project}: 23 open issues, 45 closed, 68 total"
        elif tool_name == "get_ip":
            mock_result = "Current IP address: 192.168.1.100"
        elif tool_name == "calculate_roi":
            principal = args.get("principal", 0)
            rate = args.get("rate", 0)
            years = args.get("years", 0)
            roi = principal * (1 + rate) ** years
            mock_result = f"ROI calculation: ${roi:.2f} after {years} years"
        else:
            mock_result = f"Mock result from {namespace_id}.{tool_name}"
        
        return ToolResult(
            tool_name=tool_name,
            result=mock_result,
            success=True
        )