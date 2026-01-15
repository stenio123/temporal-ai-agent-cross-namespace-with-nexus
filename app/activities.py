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

    # Note: list_remote_tools and execute_remote_tool activities are NO LONGER NEEDED!
    #
    # Why? The Python SDK documentation explicitly states:
    # "There is no support currently for calling a Nexus operation from non-workflow code."
    #
    # Solution: Nexus calls are now made directly from the workflow (see workflow.py):
    # - _discover_remote_tools() calls Nexus to get tool lists
    # - _execute_nexus_tool() calls Nexus to execute tools
    #
    # This is safe because:
    # 1. Nexus calls from workflows ARE deterministic - they're recorded in workflow history
    # 2. On replay, Temporal uses the recorded results instead of re-executing
    # 3. This follows the SDK's documented best practices