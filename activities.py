"""
Activities: All non-deterministic operations (LLM calls, tool execution)

These are the ONLY places where I/O and non-deterministic code is allowed.
Results are persisted by Temporal - replays use stored results, not re-execution.
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from temporalio import activity
from simpleeval import simple_eval

from llm_client import call_llm


@dataclass
class PlanResult:
    """Result from the planning activity"""
    next_step: str  # "execute_tool", "respond", or "done"
    tool_name: str = ""
    tool_args: Optional[Dict[str, Any]] = None
    response: str = ""


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
        conversation_history: List[Dict[str, str]]
    ) -> PlanResult:
        """
        Use LLM to decide next action: use a tool or respond to user.
        """
        activity.logger.info(f"Planning for context: {context[:100]}...")

        # Used to simulate API unavailability - check MANUAL_TESTS.md for details
        #import time
        #if not hasattr(self, '_attempt_count'):
        #    self._attempt_count = 0
        #self._attempt_count += 1
        
        #if self._attempt_count <= 3:
        #    activity.logger.error(f"API unavailable (attempt {self._attempt_count}/3)")
        #    raise Exception("ServiceUnavailable: LLM API temporarily unavailable")
        
        system_prompt = """You are a helpful assistant with tools.

Available tools:
- calculator: Evaluate math expressions. Example: {"action": "use_tool", "tool": "calculator", "args": {"expression": "25 * 4"}}
- weather: Get weather for a city. Example: {"action": "use_tool", "tool": "weather", "args": {"city": "Paris"}}

Respond with JSON:
- To use a tool: {"action": "use_tool", "tool": "calculator", "args": {"expression": "2 + 2"}}
- To respond: {"action": "respond", "message": "your response", "tool": null, "args": {}}
- To end chat: {"action": "done", "message": "goodbye", "tool": null, "args": {}}"""

        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (just user and assistant roles)
        for msg in conversation_history:
            messages.append({
                "role": msg["role"], 
                "content": msg["content"]
            })
        
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